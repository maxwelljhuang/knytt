"""
FAISS Index Builder
Builds and configures FAISS indices from product embeddings stored in PostgreSQL.
"""

from __future__ import annotations

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Any
from datetime import datetime

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Import faiss for type hints only
if TYPE_CHECKING:
    import faiss

from ..config import get_ml_config, MLConfig

logger = logging.getLogger(__name__)


class FAISSIndexBuilderError(Exception):
    """Exception raised for FAISS index building errors."""

    pass


class FAISSIndexBuilder:
    """
    Builds FAISS indices from product embeddings.

    Supports multiple index types:
    - Flat: Exact nearest neighbor search (brute force, best quality)
    - IVF: Inverted file index (faster, slight quality tradeoff)
    - HNSW: Hierarchical navigable small world (fast approximate search)
    """

    def __init__(self, config: Optional[MLConfig] = None):
        """
        Initialize FAISS index builder.

        Args:
            config: ML configuration object

        Raises:
            FAISSIndexBuilderError: If FAISS is not available
        """
        if not FAISS_AVAILABLE:
            raise FAISSIndexBuilderError(
                "FAISS is not installed. Install with: pip install faiss-cpu (or faiss-gpu)"
            )

        self.config = config or get_ml_config()
        self.dimension = self.config.embedding.product_embedding_dim
        self.index_type = self.config.storage.faiss_index_type

        logger.info(
            f"Initialized FAISS index builder: type={self.index_type}, dim={self.dimension}"
        )

    def create_index(self, index_type: Optional[str] = None) -> "faiss.Index":
        """
        Create a new FAISS index based on configuration.

        Args:
            index_type: Override default index type ('Flat', 'IVF', 'HNSW')

        Returns:
            Initialized FAISS index
        """
        index_type = index_type or self.index_type

        if index_type == "Flat":
            return self._create_flat_index()
        elif index_type == "IVF":
            return self._create_ivf_index()
        elif index_type == "HNSW":
            return self._create_hnsw_index()
        else:
            raise FAISSIndexBuilderError(f"Unsupported index type: {index_type}")

    def _create_flat_index(self) -> "faiss.Index":
        """
        Create a Flat (brute force) index.
        Best for: Small datasets (<100k), exact search required
        """
        logger.info(f"Creating IndexFlatL2 with dimension {self.dimension}")
        return faiss.IndexFlatL2(self.dimension)

    def _create_ivf_index(self, nlist: Optional[int] = None) -> "faiss.Index":
        """
        Create an IVF (Inverted File) index.
        Best for: Medium datasets (100k-1M), good speed/quality tradeoff

        Args:
            nlist: Number of clusters (default: sqrt(N) where N is dataset size)
        """
        # For IVF, we need a quantizer (typically Flat index)
        quantizer = faiss.IndexFlatL2(self.dimension)

        # Number of Voronoi cells (clusters)
        # Rule of thumb: nlist = sqrt(N), where N is number of vectors
        # We'll use a reasonable default for MVP
        nlist = nlist or 100  # Good for ~10k-100k products

        logger.info(f"Creating IndexIVFFlat with dimension {self.dimension}, nlist={nlist}")
        index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)

        # Set search parameters
        index.nprobe = self.config.storage.faiss_nprobe

        return index

    def _create_hnsw_index(self, M: int = 32) -> "faiss.Index":
        """
        Create an HNSW (Hierarchical Navigable Small World) index.
        Best for: Large datasets (>1M), very fast approximate search

        Args:
            M: Number of connections per layer (higher = better quality, more memory)
        """
        logger.info(f"Creating IndexHNSWFlat with dimension {self.dimension}, M={M}")
        index = faiss.IndexHNSWFlat(self.dimension, M)

        # Set search parameters
        index.hnsw.efSearch = self.config.storage.faiss_ef_search

        return index

    def build_index(
        self, embeddings: np.ndarray, product_ids: List[int], train_ratio: float = 1.0
    ) -> Tuple[faiss.Index, Dict[int, int]]:
        """
        Build and train FAISS index from product embeddings.

        Args:
            embeddings: Array of shape (N, dimension) with product embeddings
            product_ids: List of product IDs corresponding to embeddings
            train_ratio: Fraction of data to use for training (IVF/HNSW only)

        Returns:
            Tuple of (trained_index, id_mapping)
            - trained_index: Trained FAISS index ready for search
            - id_mapping: Dict mapping FAISS index position -> product_id

        Raises:
            FAISSIndexBuilderError: If building fails
        """
        if len(embeddings) == 0:
            raise FAISSIndexBuilderError("Cannot build index with empty embeddings")

        if embeddings.shape[1] != self.dimension:
            raise FAISSIndexBuilderError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}"
            )

        if len(embeddings) != len(product_ids):
            raise FAISSIndexBuilderError(
                f"Mismatch between embeddings ({len(embeddings)}) and product_ids ({len(product_ids)})"
            )

        logger.info(f"Building FAISS index with {len(embeddings)} embeddings")

        # Ensure embeddings are float32 (FAISS requirement)
        embeddings = embeddings.astype(np.float32)

        # Create index
        index = self.create_index()

        # Train index if needed (IVF and HNSW require training)
        if isinstance(index, faiss.IndexIVFFlat):
            logger.info(f"Training IVF index on {int(len(embeddings) * train_ratio)} samples...")
            train_size = int(len(embeddings) * train_ratio)
            train_embeddings = embeddings[:train_size]
            index.train(train_embeddings)
            logger.info("IVF index training complete")

        # Add all embeddings to index
        logger.info("Adding embeddings to index...")
        index.add(embeddings)
        logger.info(f"Index built successfully: {index.ntotal} vectors indexed")

        # Create ID mapping (FAISS position -> product_id)
        id_mapping = {i: pid for i, pid in enumerate(product_ids)}

        return index, id_mapping

    def save_index(
        self, index: faiss.Index, id_mapping: Dict[int, int], path: Optional[Path] = None
    ) -> Path:
        """
        Save FAISS index and ID mapping to disk.

        Args:
            index: FAISS index to save
            id_mapping: ID mapping dict
            path: Directory to save to (default: config.storage.faiss_index_path)

        Returns:
            Path where index was saved
        """
        save_path = path or self.config.storage.faiss_index_path
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_file = save_path / "index.faiss"
        faiss.write_index(index, str(index_file))
        logger.info(f"Saved FAISS index to {index_file}")

        # Save ID mapping as numpy array for efficiency
        mapping_file = save_path / "id_mapping.npz"
        # Convert dict to two arrays: positions and product_ids
        positions = np.array(list(id_mapping.keys()), dtype=np.int32)
        # Product IDs are UUIDs (strings), save as object array
        product_ids = np.array([str(pid) for pid in id_mapping.values()], dtype=object)
        np.savez(mapping_file, positions=positions, product_ids=product_ids)
        logger.info(f"Saved ID mapping to {mapping_file}")

        # Save metadata
        metadata_file = save_path / "metadata.npy"
        metadata = {
            "index_type": self.index_type,
            "dimension": self.dimension,
            "num_vectors": index.ntotal,
            "created_at": datetime.utcnow().isoformat(),
            "model_version": self.config.model_version,
        }
        np.save(metadata_file, metadata, allow_pickle=True)
        logger.info(f"Saved metadata to {metadata_file}")

        return save_path

    def load_index(self, path: Optional[Path] = None) -> Tuple["faiss.Index", Dict[int, int], dict]:
        """
        Load FAISS index and ID mapping from disk.

        Args:
            path: Directory to load from (default: config.storage.faiss_index_path)

        Returns:
            Tuple of (index, id_mapping, metadata)

        Raises:
            FAISSIndexBuilderError: If loading fails
        """
        load_path = path or self.config.storage.faiss_index_path
        load_path = Path(load_path)

        if not load_path.exists():
            raise FAISSIndexBuilderError(f"Index path does not exist: {load_path}")

        # Load FAISS index
        index_file = load_path / "index.faiss"
        if not index_file.exists():
            raise FAISSIndexBuilderError(f"Index file not found: {index_file}")

        logger.info(f"Loading FAISS index from {index_file}")
        index = faiss.read_index(str(index_file))

        # Load ID mapping
        mapping_file = load_path / "id_mapping.npz"
        if not mapping_file.exists():
            raise FAISSIndexBuilderError(f"ID mapping file not found: {mapping_file}")

        logger.info(f"Loading ID mapping from {mapping_file}")
        mapping_data = np.load(mapping_file, allow_pickle=True)
        positions = mapping_data["positions"]
        product_ids = mapping_data["product_ids"]
        # Product IDs are UUIDs (strings), keep as strings
        id_mapping = {int(pos): str(pid) for pos, pid in zip(positions, product_ids)}

        # Load metadata
        metadata_file = load_path / "metadata.npy"
        metadata = {}
        if metadata_file.exists():
            metadata = np.load(metadata_file, allow_pickle=True).item()
            logger.info(f"Loaded index metadata: {metadata}")

        logger.info(f"Successfully loaded FAISS index: {index.ntotal} vectors")

        return index, id_mapping, metadata

    def get_index_stats(self, index: "faiss.Index") -> dict:
        """
        Get statistics about the FAISS index.

        Args:
            index: FAISS index to analyze

        Returns:
            Dictionary with index statistics
        """
        stats = {
            "num_vectors": index.ntotal,
            "dimension": self.dimension,
            "is_trained": index.is_trained,
        }

        # Add index-specific stats
        if isinstance(index, faiss.IndexIVFFlat):
            stats["index_type"] = "IVF"
            stats["nlist"] = index.nlist
            stats["nprobe"] = index.nprobe
        elif isinstance(index, faiss.IndexHNSWFlat):
            stats["index_type"] = "HNSW"
            stats["M"] = index.hnsw.M
            stats["efSearch"] = index.hnsw.efSearch
        elif isinstance(index, faiss.IndexFlatL2):
            stats["index_type"] = "Flat"
        else:
            stats["index_type"] = type(index).__name__

        return stats
