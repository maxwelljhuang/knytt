"""
FAISS Index Manager
Manages FAISS index lifecycle: loading from DB, building, rebuilding, and serving.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import text

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from ..config import get_ml_config, MLConfig
from .index_builder import FAISSIndexBuilder, FAISSIndexBuilderError

logger = logging.getLogger(__name__)


class FAISSIndexManagerError(Exception):
    """Exception raised for index manager errors."""

    pass


class FAISSIndexManager:
    """
    Manages FAISS index lifecycle with automatic rebuilding.

    This is a singleton class that:
    - Loads product embeddings from PostgreSQL
    - Builds and maintains FAISS index
    - Handles index rebuilding on a schedule
    - Provides thread-safe access to the index
    """

    _instance: Optional["FAISSIndexManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[MLConfig] = None, db_session_factory=None):
        """
        Initialize FAISS index manager.

        Args:
            config: ML configuration
            db_session_factory: Factory function to create database sessions
        """
        # Only initialize once
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.config = config or get_ml_config()
        self.builder = FAISSIndexBuilder(self.config)
        self.db_session_factory = db_session_factory

        # Index state
        self.index: Optional[faiss.Index] = None
        self.id_mapping: Dict[int, int] = {}  # FAISS position -> product_id
        self.reverse_mapping: Dict[int, int] = {}  # product_id -> FAISS position
        self.metadata: dict = {}

        # Rebuild scheduling
        self.last_rebuild: Optional[datetime] = None
        self.rebuild_interval = timedelta(hours=self.config.storage.rebuild_index_interval_hours)

        # Thread safety
        self.index_lock = threading.RLock()

        self._initialized = True
        logger.info("FAISS Index Manager initialized")

    @classmethod
    def get_instance(cls, config: Optional[MLConfig] = None, db_session_factory=None):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config=config, db_session_factory=db_session_factory)
        return cls._instance

    def load_embeddings_from_db(self, session) -> Tuple[np.ndarray, List[int]]:
        """
        Load product embeddings from PostgreSQL.

        Args:
            session: SQLAlchemy database session

        Returns:
            Tuple of (embeddings_array, product_ids)

        Raises:
            FAISSIndexManagerError: If loading fails
        """
        try:
            # Query product embeddings
            query = text(
                """
                SELECT product_id, embedding
                FROM product_embeddings
                WHERE embedding_type = 'text'
                  AND embedding IS NOT NULL
                ORDER BY product_id
            """
            )

            result = session.execute(query)
            rows = result.fetchall()

            if len(rows) == 0:
                raise FAISSIndexManagerError(
                    "No product embeddings found in database. "
                    "Run embedding generation first: python scripts/ml/generate_embeddings.py"
                )

            # Extract embeddings and IDs
            product_ids = []
            embeddings_list = []

            for row in rows:
                product_id = row[0]
                embedding = row[1]  # This is a pgvector column, should be list/array

                # Convert pgvector to numpy array
                if isinstance(embedding, str):
                    # If stored as string, parse it
                    embedding = np.fromstring(embedding.strip("[]"), sep=",")
                elif isinstance(embedding, (list, tuple)):
                    embedding = np.array(embedding)

                product_ids.append(product_id)
                embeddings_list.append(embedding)

            embeddings = np.vstack(embeddings_list).astype(np.float32)

            logger.info(f"Loaded {len(product_ids)} product embeddings from database")

            return embeddings, product_ids

        except Exception as e:
            logger.error(f"Failed to load embeddings from database: {e}")
            raise FAISSIndexManagerError(f"Database loading failed: {e}")

    def build_index_from_db(self, session) -> None:
        """
        Build FAISS index from database embeddings.

        Args:
            session: SQLAlchemy database session
        """
        logger.info("Building FAISS index from database...")

        # Load embeddings
        embeddings, product_ids = self.load_embeddings_from_db(session)

        # Build index
        with self.index_lock:
            index, id_mapping = self.builder.build_index(embeddings, product_ids)

            # Create reverse mapping
            reverse_mapping = {pid: idx for idx, pid in id_mapping.items()}

            # Update instance state
            self.index = index
            self.id_mapping = id_mapping
            self.reverse_mapping = reverse_mapping
            self.last_rebuild = datetime.utcnow()

            # Save to disk
            self.builder.save_index(index, id_mapping)

        logger.info(f"FAISS index built successfully: {self.index.ntotal} products indexed")

    def load_index_from_disk(self, path: Optional[Path] = None) -> None:
        """
        Load FAISS index from disk.

        Args:
            path: Directory to load from (default: config path)
        """
        logger.info("Loading FAISS index from disk...")

        with self.index_lock:
            index, id_mapping, metadata = self.builder.load_index(path)

            # Create reverse mapping
            reverse_mapping = {pid: idx for idx, pid in id_mapping.items()}

            # Update instance state
            self.index = index
            self.id_mapping = id_mapping
            self.reverse_mapping = reverse_mapping
            self.metadata = metadata

            # Check if metadata has created_at timestamp
            if "created_at" in metadata:
                self.last_rebuild = datetime.fromisoformat(metadata["created_at"])
            else:
                self.last_rebuild = datetime.utcnow()

        logger.info(f"FAISS index loaded from disk: {self.index.ntotal} products indexed")

    def ensure_index_loaded(self, session=None) -> None:
        """
        Ensure FAISS index is loaded and ready.

        Tries to load from disk first, then builds from DB if not found.

        Args:
            session: SQLAlchemy database session (required for DB build)
        """
        if self.index is not None:
            return  # Already loaded

        # Try loading from disk first
        try:
            self.load_index_from_disk()
            logger.info("Successfully loaded existing FAISS index from disk")
            return
        except (FAISSIndexBuilderError, FileNotFoundError) as e:
            logger.warning(f"Could not load index from disk: {e}")

        # Build from database
        if session is None:
            if self.db_session_factory is None:
                raise FAISSIndexManagerError(
                    "No index found and no database session provided to build one"
                )
            session = self.db_session_factory()

        try:
            self.build_index_from_db(session)
        finally:
            if self.db_session_factory is not None:
                session.close()

    def should_rebuild(self) -> bool:
        """
        Check if index should be rebuilt based on schedule.

        Returns:
            True if rebuild is needed
        """
        if self.last_rebuild is None:
            return True

        time_since_rebuild = datetime.utcnow() - self.last_rebuild
        return time_since_rebuild >= self.rebuild_interval

    def rebuild_if_needed(self, session) -> bool:
        """
        Rebuild index if the rebuild interval has passed.

        Args:
            session: SQLAlchemy database session

        Returns:
            True if rebuild was performed
        """
        if not self.should_rebuild():
            return False

        logger.info("Rebuild interval reached, rebuilding FAISS index...")
        self.build_index_from_db(session)
        return True

    def get_index(self) -> faiss.Index:
        """
        Get the FAISS index (thread-safe).

        Returns:
            Current FAISS index

        Raises:
            FAISSIndexManagerError: If index is not loaded
        """
        if self.index is None:
            raise FAISSIndexManagerError("Index not loaded. Call ensure_index_loaded() first.")

        with self.index_lock:
            return self.index

    def get_id_mapping(self) -> Dict[int, int]:
        """Get ID mapping (FAISS position -> product_id)."""
        with self.index_lock:
            return self.id_mapping.copy()

    def get_product_id(self, faiss_idx: int) -> Optional[int]:
        """
        Get product ID from FAISS index position.

        Args:
            faiss_idx: Position in FAISS index

        Returns:
            Product ID or None if not found
        """
        with self.index_lock:
            return self.id_mapping.get(faiss_idx)

    def get_faiss_position(self, product_id: int) -> Optional[int]:
        """
        Get FAISS position from product ID.

        Args:
            product_id: Product ID

        Returns:
            FAISS index position or None if not found
        """
        with self.index_lock:
            return self.reverse_mapping.get(product_id)

    def get_stats(self) -> dict:
        """
        Get index statistics.

        Returns:
            Dictionary with index stats
        """
        with self.index_lock:
            if self.index is None:
                return {"status": "not_loaded"}

            stats = self.builder.get_index_stats(self.index)
            stats.update(
                {
                    "status": "loaded",
                    "num_products": len(self.id_mapping),
                    "last_rebuild": self.last_rebuild.isoformat() if self.last_rebuild else None,
                    "rebuild_interval_hours": self.rebuild_interval.total_seconds() / 3600,
                    "next_rebuild": (
                        (self.last_rebuild + self.rebuild_interval).isoformat()
                        if self.last_rebuild
                        else None
                    ),
                }
            )

            return stats

    def reset(self) -> None:
        """Reset the manager (useful for testing)."""
        with self.index_lock:
            self.index = None
            self.id_mapping = {}
            self.reverse_mapping = {}
            self.metadata = {}
            self.last_rebuild = None

        logger.info("FAISS Index Manager reset")


# Global instance accessor
_manager_instance: Optional[FAISSIndexManager] = None


def get_index_manager(
    config: Optional[MLConfig] = None, db_session_factory=None
) -> FAISSIndexManager:
    """Get global FAISS index manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = FAISSIndexManager.get_instance(
            config=config, db_session_factory=db_session_factory
        )
    return _manager_instance
