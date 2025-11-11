"""
Cold-Start User Embeddings
Generates initial user embeddings from style quiz selections.
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any

from ..config import get_ml_config

logger = logging.getLogger(__name__)


class ColdStartEmbedding:
    """
    Creates initial user embeddings for new users.

    Strategies:
    1. Style quiz: Average embeddings of selected moodboard/products
    2. Demographic defaults: Based on age/gender/location
    3. Random exploration: Start with diverse recommendations
    """

    def __init__(self):
        """Initialize cold-start embedding generator."""
        self.config = get_ml_config()

    def from_product_selections(self, product_embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Create user embedding from selected products (style quiz).

        Args:
            product_embeddings: List of product embeddings user selected

        Returns:
            User embedding (average of selections)
        """
        if not product_embeddings:
            raise ValueError("Need at least one product selection")

        # Simple average
        user_embedding = np.mean(product_embeddings, axis=0)

        # Normalize
        if self.config.embedding.normalize_embeddings:
            user_embedding = user_embedding / np.linalg.norm(user_embedding)

        return user_embedding

    def from_style_quiz(
        self, selected_product_ids: List[str], product_embeddings_dict: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Create user embedding from style quiz results.

        Args:
            selected_product_ids: IDs of products/moodboards user selected
            product_embeddings_dict: Mapping of product_id -> embedding

        Returns:
            Dict with user embedding and metadata
        """
        result = {
            "user_embedding": None,
            "num_selections": len(selected_product_ids),
            "success": False,
            "method": "style_quiz",
        }

        # Get embeddings for selected products
        selected_embeddings = []
        missing_ids = []

        for product_id in selected_product_ids:
            if product_id in product_embeddings_dict:
                selected_embeddings.append(product_embeddings_dict[product_id])
            else:
                missing_ids.append(product_id)
                logger.warning(f"No embedding found for product {product_id}")

        result["missing_ids"] = missing_ids
        result["valid_selections"] = len(selected_embeddings)

        if not selected_embeddings:
            logger.error("No valid product embeddings found")
            result["error"] = "no_valid_selections"
            return result

        # Check minimum selections
        min_selections = self.config.user_modeling.min_quiz_selections
        if len(selected_embeddings) < min_selections:
            logger.warning(
                f"Only {len(selected_embeddings)} selections, " f"minimum is {min_selections}"
            )

        # Create user embedding
        try:
            user_embedding = self.from_product_selections(selected_embeddings)
            result["user_embedding"] = user_embedding
            result["success"] = True
        except Exception as e:
            logger.error(f"Failed to create user embedding: {e}")
            result["error"] = str(e)

        return result

    def from_category_preferences(
        self,
        category_embeddings: Dict[str, np.ndarray],
        preferred_categories: List[str],
        weights: Optional[List[float]] = None,
    ) -> np.ndarray:
        """
        Create user embedding from category preferences.

        Args:
            category_embeddings: Category name -> embedding mapping
            preferred_categories: List of preferred category names
            weights: Optional weights for each category

        Returns:
            User embedding
        """
        if not preferred_categories:
            raise ValueError("Need at least one preferred category")

        # Get category embeddings
        embeddings = [
            category_embeddings[cat] for cat in preferred_categories if cat in category_embeddings
        ]

        if not embeddings:
            raise ValueError("No valid category embeddings found")

        # Weighted average
        if weights:
            weights = np.array(weights[: len(embeddings)])
            weights = weights / weights.sum()  # Normalize weights
            user_embedding = np.average(embeddings, axis=0, weights=weights)
        else:
            user_embedding = np.mean(embeddings, axis=0)

        # Normalize
        if self.config.embedding.normalize_embeddings:
            user_embedding = user_embedding / np.linalg.norm(user_embedding)

        return user_embedding

    def get_exploration_embedding(
        self, base_embedding: Optional[np.ndarray] = None, exploration_factor: float = 0.1
    ) -> np.ndarray:
        """
        Add exploration noise to embedding for diversity.

        Args:
            base_embedding: Base user embedding (None = random)
            exploration_factor: Amount of noise to add (0.0-1.0)

        Returns:
            Embedding with exploration noise
        """
        embedding_dim = self.config.user_modeling.user_embedding_dim

        if base_embedding is None:
            # Fully random embedding
            embedding = np.random.randn(embedding_dim)
        else:
            # Add noise to existing embedding
            noise = np.random.randn(embedding_dim) * exploration_factor
            embedding = base_embedding + noise

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def create_default_embedding(self) -> np.ndarray:
        """
        Create a neutral default embedding for users with no data.

        Returns:
            Random normalized embedding
        """
        logger.info("Creating default random embedding")
        return self.get_exploration_embedding(base_embedding=None)


# Global instance
_cold_start_instance = None


def get_cold_start_generator() -> ColdStartEmbedding:
    """Get global cold-start generator instance."""
    global _cold_start_instance
    if _cold_start_instance is None:
        _cold_start_instance = ColdStartEmbedding()
    return _cold_start_instance


def create_user_from_quiz(
    selected_product_ids: List[str], product_embeddings: Dict[str, np.ndarray]
) -> np.ndarray:
    """
    Convenience function to create user embedding from quiz.

    Args:
        selected_product_ids: IDs of selected products
        product_embeddings: Product ID -> embedding mapping

    Returns:
        User embedding
    """
    generator = get_cold_start_generator()
    result = generator.from_style_quiz(selected_product_ids, product_embeddings)

    if result["success"]:
        return result["user_embedding"]
    else:
        raise ValueError(f"Failed to create user embedding: {result.get('error')}")
