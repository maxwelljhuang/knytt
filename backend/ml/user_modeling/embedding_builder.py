"""
User Embedding Builder
Builds and updates user embeddings from interaction history stored in database.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from uuid import UUID

from ..config import get_ml_config
from .warm_user import get_warm_user_updater
from .cold_start import get_cold_start_generator

logger = logging.getLogger(__name__)


class UserEmbeddingBuilder:
    """
    Builds user embeddings from interaction history.

    This service:
    1. Fetches user interactions from database
    2. Retrieves product embeddings for those interactions
    3. Applies weighted aggregation based on interaction types
    4. Uses EWMA to blend with existing long-term embedding
    5. Saves updated embedding to database and cache
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize embedding builder.

        Args:
            db: Database session
            cache: Optional embedding cache
        """
        self.db = db
        self.cache = cache
        self.config = get_ml_config()
        self.warm_updater = get_warm_user_updater()

        # Interaction weights (matching feedback.py)
        self.interaction_weights = {
            "view": 0.1,
            "click": 0.3,
            "add_to_cart": 0.6,
            "purchase": 1.0,
            "like": 0.5,
            "share": 0.4,
            "rating": 0.7,
        }

    def get_recent_interactions(
        self, user_id: UUID, limit: int = 50, days_back: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent user interactions from database.

        Args:
            user_id: User UUID
            limit: Maximum number of interactions to fetch
            days_back: How many days back to look

        Returns:
            List of interaction dicts with product_id, interaction_type, created_at, etc.
        """
        from ...db.models import UserInteraction

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = (
            select(UserInteraction)
            .where(
                and_(UserInteraction.user_id == user_id, UserInteraction.created_at >= cutoff_date)
            )
            .order_by(desc(UserInteraction.created_at))
            .limit(limit)
        )

        results = self.db.execute(query).scalars().all()

        interactions = []
        for row in results:
            interactions.append(
                {
                    "id": row.id,
                    "product_id": row.product_id,
                    "interaction_type": row.interaction_type,
                    "rating": row.rating,
                    "created_at": row.created_at,
                    "weight": self.interaction_weights.get(row.interaction_type, 0.3),
                }
            )

        logger.info(f"Fetched {len(interactions)} recent interactions for user {user_id}")
        return interactions

    def get_product_embeddings(self, product_ids: List[UUID]) -> Dict[UUID, np.ndarray]:
        """
        Fetch product embeddings from database.

        Args:
            product_ids: List of product UUIDs

        Returns:
            Dict mapping product_id -> embedding array
        """
        from ...db.models import ProductEmbedding

        query = select(ProductEmbedding).where(
            and_(
                ProductEmbedding.product_id.in_(product_ids),
                ProductEmbedding.embedding_type == "text",
            )
        )

        results = self.db.execute(query).scalars().all()

        embeddings = {}
        for row in results:
            # Handle both old array format and new pgvector format
            embedding_data = (
                row.embedding_vector
                if hasattr(row, "embedding_vector") and row.embedding_vector is not None
                else row.embedding
            )

            if embedding_data is not None:
                if isinstance(embedding_data, (list, tuple)):
                    embeddings[row.product_id] = np.array(embedding_data, dtype=np.float32)
                elif isinstance(embedding_data, np.ndarray):
                    embeddings[row.product_id] = embedding_data.astype(np.float32)

        logger.info(f"Fetched embeddings for {len(embeddings)}/{len(product_ids)} products")
        return embeddings

    def build_user_embedding(
        self,
        user_id: UUID,
        current_embedding: Optional[np.ndarray] = None,
        max_interactions: int = 50,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Build or update user embedding from interaction history.

        Args:
            user_id: User UUID
            current_embedding: Existing user embedding (if any)
            max_interactions: Maximum number of interactions to consider

        Returns:
            Tuple of (updated_embedding, metadata)
        """
        # Fetch recent interactions
        interactions = self.get_recent_interactions(user_id, limit=max_interactions)

        if len(interactions) == 0:
            logger.warning(f"No interactions found for user {user_id}")
            # Return cold start embedding if no current embedding
            if current_embedding is None:
                cold_start_gen = get_cold_start_generator()
                current_embedding = cold_start_gen.generate_random_embedding()
                logger.info(f"Generated cold start embedding for user {user_id}")

            return current_embedding, {
                "interaction_count": 0,
                "status": "cold_start",
                "confidence": 0.0,
            }

        # Get product IDs
        product_ids = [interaction["product_id"] for interaction in interactions]

        # Fetch product embeddings
        product_embeddings = self.get_product_embeddings(product_ids)

        if len(product_embeddings) == 0:
            logger.error(f"No product embeddings found for user {user_id}'s interactions")
            if current_embedding is None:
                cold_start_gen = get_cold_start_generator()
                current_embedding = cold_start_gen.generate_random_embedding()

            return current_embedding, {
                "interaction_count": len(interactions),
                "status": "no_embeddings",
                "confidence": 0.0,
            }

        # Build embedding from interactions
        if current_embedding is None:
            # Initialize with first product embedding (weighted)
            first_interaction = interactions[0]
            first_product_id = first_interaction["product_id"]

            if first_product_id in product_embeddings:
                current_embedding = product_embeddings[first_product_id].copy()
                weight = first_interaction["weight"]
                current_embedding = current_embedding * weight

                # Normalize
                norm = np.linalg.norm(current_embedding)
                if norm > 0:
                    current_embedding = current_embedding / norm

                logger.info(f"Initialized embedding for user {user_id} from first interaction")
            else:
                # Fallback to cold start
                cold_start_gen = get_cold_start_generator()
                current_embedding = cold_start_gen.generate_random_embedding()
                logger.warning(f"Using cold start embedding for user {user_id}")

        # Update embedding with each interaction using EWMA
        processed_count = 0
        for interaction in interactions:
            product_id = interaction["product_id"]

            if product_id not in product_embeddings:
                continue

            product_embedding = product_embeddings[product_id]
            interaction_type = interaction["interaction_type"]
            weight = interaction["weight"]

            # Update using warm user logic
            try:
                result = self.warm_updater.update_from_interaction(
                    user_id=str(user_id),
                    current_embedding=current_embedding,
                    interaction={
                        "product_embedding": product_embedding,
                        "interaction_type": interaction_type,
                        "timestamp": interaction["created_at"],
                    },
                )

                if result["success"]:
                    current_embedding = result["updated_embedding"]
                    processed_count += 1

            except Exception as e:
                logger.error(f"Failed to update embedding for interaction: {e}")
                continue

        # Calculate confidence score based on interaction count
        confidence = min(processed_count / 20.0, 1.0)  # Full confidence at 20+ interactions

        metadata = {
            "interaction_count": len(interactions),
            "processed_count": processed_count,
            "status": "warm_user",
            "confidence": confidence,
            "updated_at": datetime.utcnow(),
        }

        logger.info(
            f"Built embedding for user {user_id}: "
            f"{processed_count}/{len(interactions)} interactions processed, "
            f"confidence={confidence:.2f}"
        )

        return current_embedding, metadata

    def save_user_embedding(
        self,
        user_id: UUID,
        embedding: np.ndarray,
        embedding_type: str = "long_term",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save user embedding to database.

        Args:
            user_id: User UUID
            embedding: Embedding array
            embedding_type: 'long_term' or 'session'
            metadata: Optional metadata dict

        Returns:
            True if saved successfully
        """
        from ...db.models import UserEmbedding

        try:
            # Check if embedding exists
            query = select(UserEmbedding).where(
                and_(
                    UserEmbedding.user_id == user_id, UserEmbedding.embedding_type == embedding_type
                )
            )
            existing = self.db.execute(query).scalar_one_or_none()

            if existing:
                # Update existing
                if embedding_type == "long_term":
                    existing.long_term_embedding = embedding.tolist()
                elif embedding_type == "session":
                    existing.session_embedding = embedding.tolist()

                existing.updated_at = datetime.utcnow()
                existing.last_interaction_at = datetime.utcnow()

                if metadata:
                    existing.interaction_count = metadata.get(
                        "processed_count", existing.interaction_count
                    )
                    existing.confidence_score = metadata.get(
                        "confidence", existing.confidence_score
                    )

                logger.info(f"Updated {embedding_type} embedding for user {user_id}")

            else:
                # Create new
                user_embedding = UserEmbedding(
                    user_id=user_id,
                    embedding_type=embedding_type,
                    long_term_embedding=(
                        embedding.tolist() if embedding_type == "long_term" else None
                    ),
                    session_embedding=embedding.tolist() if embedding_type == "session" else None,
                    last_interaction_at=datetime.utcnow(),
                    interaction_count=metadata.get("processed_count", 0) if metadata else 0,
                    confidence_score=metadata.get("confidence", 0.5) if metadata else 0.5,
                )

                self.db.add(user_embedding)
                logger.info(f"Created new {embedding_type} embedding for user {user_id}")

            self.db.commit()

            # Update cache if available
            if self.cache:
                try:
                    # Convert UUID to int or string for cache key
                    cache_user_id = str(user_id)

                    if embedding_type == "long_term":
                        self.cache.set_user_long_term_embedding(
                            user_id=cache_user_id, embedding=embedding
                        )
                    elif embedding_type == "session":
                        self.cache.set_user_session_embedding(
                            user_id=cache_user_id, embedding=embedding
                        )
                    logger.debug(f"Cached {embedding_type} embedding for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to cache embedding: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to save user embedding: {e}")
            self.db.rollback()
            return False

    def update_user_embedding(
        self, user_id: UUID, max_interactions: int = 50
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update user's long-term embedding from recent interactions.

        This is the main entry point for updating user embeddings.

        Args:
            user_id: User UUID
            max_interactions: Max number of interactions to consider

        Returns:
            Tuple of (success, metadata)
        """
        try:
            # Get current long-term embedding if it exists
            from ...db.models import UserEmbedding

            query = select(UserEmbedding).where(
                and_(UserEmbedding.user_id == user_id, UserEmbedding.embedding_type == "long_term")
            )
            existing = self.db.execute(query).scalar_one_or_none()

            current_embedding = None
            if existing and existing.long_term_embedding is not None:
                emb_data = existing.long_term_embedding
                if isinstance(emb_data, (list, tuple)):
                    current_embedding = np.array(emb_data, dtype=np.float32)
                elif isinstance(emb_data, np.ndarray):
                    current_embedding = emb_data.astype(np.float32)

            # Build updated embedding
            updated_embedding, metadata = self.build_user_embedding(
                user_id=user_id,
                current_embedding=current_embedding,
                max_interactions=max_interactions,
            )

            # Save to database and cache
            success = self.save_user_embedding(
                user_id=user_id,
                embedding=updated_embedding,
                embedding_type="long_term",
                metadata=metadata,
            )

            return success, metadata

        except Exception as e:
            logger.error(f"Failed to update user embedding: {e}", exc_info=True)
            return False, {"error": str(e)}


def get_embedding_builder(db: Session, cache=None) -> UserEmbeddingBuilder:
    """
    Get embedding builder instance.

    Args:
        db: Database session
        cache: Optional cache instance

    Returns:
        UserEmbeddingBuilder instance
    """
    return UserEmbeddingBuilder(db=db, cache=cache)
