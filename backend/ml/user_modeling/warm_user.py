"""
Warm User Embeddings
Updates user embeddings based on interactions using EWMA.
"""

import logging
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..config import get_ml_config

logger = logging.getLogger(__name__)


class WarmUserEmbedding:
    """
    Maintains and updates long-term user taste profiles.

    Uses Exponentially Weighted Moving Average (EWMA):
    new_embedding = alpha * old_embedding + (1 - alpha) * interaction_embedding

    Where:
    - alpha (e.g., 0.95) controls drift speed
    - High alpha = slow adaptation, emphasizes history
    - Low alpha = fast adaptation, follows recent trends
    """

    def __init__(self):
        """Initialize warm user embedding updater."""
        self.config = get_ml_config()
        self.alpha = self.config.user_modeling.ewma_alpha

    def update_embedding(
        self,
        current_embedding: np.ndarray,
        interaction_embedding: np.ndarray,
        interaction_weight: float = 1.0,
    ) -> np.ndarray:
        """
        Update user embedding with new interaction using EWMA.

        Args:
            current_embedding: Current user embedding
            interaction_embedding: Embedding of interacted product
            interaction_weight: Weight for this interaction (default 1.0)
                               Can be >1 for purchases, <1 for views

        Returns:
            Updated user embedding
        """
        # Adjust alpha based on interaction weight
        # Stronger interactions (purchases) have more impact
        adjusted_alpha = self.alpha / (1.0 + interaction_weight - 1.0)
        adjusted_alpha = np.clip(adjusted_alpha, 0.0, 1.0)

        # EWMA update
        new_embedding = (
            adjusted_alpha * current_embedding + (1.0 - adjusted_alpha) * interaction_embedding
        )

        # Normalize
        if self.config.embedding.normalize_embeddings:
            new_embedding = new_embedding / np.linalg.norm(new_embedding)

        return new_embedding

    def update_from_interaction(
        self, user_id: str, current_embedding: np.ndarray, interaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user embedding from a single interaction.

        Args:
            user_id: User ID
            current_embedding: Current user embedding
            interaction: Dict with interaction details
                {
                    'product_embedding': np.ndarray,
                    'interaction_type': 'view' | 'like' | 'add_to_cart' | 'purchase',
                    'timestamp': datetime,
                }

        Returns:
            Dict with updated embedding and metadata
        """
        result = {
            "user_id": user_id,
            "updated_embedding": None,
            "success": False,
        }

        # Get product embedding
        product_emb = interaction.get("product_embedding")
        if product_emb is None:
            logger.error(f"No product embedding in interaction for user {user_id}")
            result["error"] = "no_product_embedding"
            return result

        # Determine interaction weight
        interaction_type = interaction.get("interaction_type", "view")
        weights = {
            "view": 0.5,
            "like": 1.0,
            "dislike": -0.5,  # Negative interaction
            "add_to_cart": 1.5,
            "purchase": 2.0,
        }
        weight = weights.get(interaction_type, 1.0)

        result["interaction_type"] = interaction_type
        result["interaction_weight"] = weight

        # Handle negative interactions (dislikes)
        if weight < 0:
            # Move away from disliked items
            # Invert the product embedding influence
            product_emb = -product_emb * abs(weight)
            weight = 1.0

        # Update embedding
        try:
            updated_embedding = self.update_embedding(current_embedding, product_emb, weight)

            result["updated_embedding"] = updated_embedding
            result["success"] = True

        except Exception as e:
            logger.error(f"Failed to update embedding for user {user_id}: {e}")
            result["error"] = str(e)

        return result

    def update_from_batch(
        self, current_embedding: np.ndarray, interactions: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Update user embedding from multiple interactions.

        Args:
            current_embedding: Current user embedding
            interactions: List of interaction dicts

        Returns:
            Updated user embedding
        """
        embedding = current_embedding.copy()

        for interaction in interactions:
            product_emb = interaction.get("product_embedding")
            if product_emb is None:
                continue

            interaction_type = interaction.get("interaction_type", "view")
            weights = {
                "view": 0.5,
                "like": 1.0,
                "dislike": -0.5,
                "add_to_cart": 1.5,
                "purchase": 2.0,
            }
            weight = weights.get(interaction_type, 1.0)

            # Handle negative interactions
            if weight < 0:
                product_emb = -product_emb * abs(weight)
                weight = 1.0

            # Update
            embedding = self.update_embedding(embedding, product_emb, weight)

        return embedding

    def compute_drift(self, old_embedding: np.ndarray, new_embedding: np.ndarray) -> float:
        """
        Compute how much user taste has drifted.

        Args:
            old_embedding: Previous user embedding
            new_embedding: New user embedding

        Returns:
            Drift amount (cosine distance, 0=no change, 2=complete reversal)
        """
        # Cosine similarity
        similarity = np.dot(old_embedding, new_embedding)

        # Convert to distance (0 = identical, 2 = opposite)
        distance = 1.0 - similarity

        return distance


# Global instance
_warm_user_instance = None


def get_warm_user_updater() -> WarmUserEmbedding:
    """Get global warm user updater instance."""
    global _warm_user_instance
    if _warm_user_instance is None:
        _warm_user_instance = WarmUserEmbedding()
    return _warm_user_instance


def update_user_from_interaction(
    current_embedding: np.ndarray, product_embedding: np.ndarray, interaction_type: str = "like"
) -> np.ndarray:
    """
    Convenience function to update user embedding.

    Args:
        current_embedding: Current user embedding
        product_embedding: Product they interacted with
        interaction_type: 'view', 'like', 'dislike', 'purchase'

    Returns:
        Updated user embedding
    """
    updater = get_warm_user_updater()

    result = updater.update_from_interaction(
        user_id="temp",
        current_embedding=current_embedding,
        interaction={
            "product_embedding": product_embedding,
            "interaction_type": interaction_type,
        },
    )

    if result["success"]:
        return result["updated_embedding"]
    else:
        raise ValueError(f"Update failed: {result.get('error')}")
