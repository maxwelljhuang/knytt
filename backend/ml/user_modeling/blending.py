"""
User Embedding Blending
Combines long-term and session embeddings for personalized recommendations.
"""

import logging
import numpy as np
from typing import Optional, Dict, Any

from ..config import get_ml_config

logger = logging.getLogger(__name__)


class UserEmbeddingBlender:
    """
    Blends long-term user taste with current session intent.

    Formula:
    user_vec = alpha * long_term_vec + (1-alpha) * session_vec

    Where:
    - alpha (e.g., 0.7) controls blend
    - High alpha = favor long-term taste
    - Low alpha = favor current session intent
    """

    def __init__(self):
        """Initialize blending module."""
        self.config = get_ml_config()

    def blend(
        self,
        long_term_embedding: Optional[np.ndarray],
        session_embedding: Optional[np.ndarray],
        alpha: Optional[float] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Blend long-term and session embeddings.

        Args:
            long_term_embedding: User's long-term taste profile
            session_embedding: Current session intent
            alpha: Blend weight for long-term (default: from config)
            context: Context for blend (e.g., 'feed', 'search')

        Returns:
            Dict with blended embedding and metadata
        """
        result = {
            "blended_embedding": None,
            "has_long_term": long_term_embedding is not None,
            "has_session": session_embedding is not None,
            "alpha": None,
            "context": context,
            "success": False,
        }

        # Get blend weight
        if alpha is None:
            alpha = self._get_alpha_for_context(context)

        result["alpha"] = alpha

        # Both available - blend them
        if long_term_embedding is not None and session_embedding is not None:
            try:
                blended = alpha * long_term_embedding + (1.0 - alpha) * session_embedding

                # Normalize
                if self.config.embedding.normalize_embeddings:
                    blended = blended / np.linalg.norm(blended)

                result["blended_embedding"] = blended
                result["blend_type"] = "full"
                result["success"] = True

            except Exception as e:
                logger.error(f"Blending failed: {e}")
                result["error"] = str(e)

        # Only long-term available
        elif long_term_embedding is not None:
            logger.debug("Using long-term embedding only (no session)")
            result["blended_embedding"] = long_term_embedding
            result["blend_type"] = "long_term_only"
            result["success"] = True

        # Only session available
        elif session_embedding is not None:
            logger.debug("Using session embedding only (no long-term)")
            result["blended_embedding"] = session_embedding
            result["blend_type"] = "session_only"
            result["success"] = True

        # Neither available
        else:
            logger.warning("No embeddings available for blending")
            result["blend_type"] = "none"
            result["error"] = "no_embeddings"

        return result

    def _get_alpha_for_context(self, context: Optional[str]) -> float:
        """
        Get blend weight based on context.

        Args:
            context: Request context ('feed', 'search', 'similar', etc.)

        Returns:
            Alpha value (0.0-1.0)
        """
        # Context-specific alphas
        alphas = {
            "feed": 0.7,  # Balanced: show established taste + current interest
            "search": 0.3,  # Session-focused: user searching for specific item
            "similar": 0.9,  # Long-term: show items matching their style
            "explore": 0.5,  # Balanced: mix of familiar and new
            "onboard": 1.0,  # Pure long-term: just style quiz results
        }

        return alphas.get(context, self.config.user_modeling.long_term_alpha)

    def add_exploration(
        self, embedding: np.ndarray, exploration_factor: Optional[float] = None
    ) -> np.ndarray:
        """
        Add exploration noise to embedding for diversity.

        Args:
            embedding: Base embedding
            exploration_factor: Amount of noise (default: from config)

        Returns:
            Embedding with exploration noise
        """
        if exploration_factor is None:
            exploration_factor = self.config.user_modeling.exploration_epsilon

        # Add random noise
        noise = np.random.randn(*embedding.shape) * exploration_factor
        noisy_embedding = embedding + noise

        # Normalize
        noisy_embedding = noisy_embedding / np.linalg.norm(noisy_embedding)

        return noisy_embedding

    def get_recommendation_embedding(
        self,
        long_term_embedding: Optional[np.ndarray],
        session_embedding: Optional[np.ndarray],
        context: str = "feed",
        add_exploration: bool = False,
    ) -> Optional[np.ndarray]:
        """
        Get final embedding for recommendations.

        Args:
            long_term_embedding: Long-term user taste
            session_embedding: Session intent
            context: Request context
            add_exploration: Whether to add exploration noise

        Returns:
            Final recommendation embedding
        """
        # Blend embeddings
        result = self.blend(long_term_embedding, session_embedding, context=context)

        if not result["success"]:
            return None

        embedding = result["blended_embedding"]

        # Add exploration if requested
        if add_exploration:
            embedding = self.add_exploration(embedding)

        return embedding


# Global blender instance
_blender_instance = None


def get_user_blender() -> UserEmbeddingBlender:
    """Get global blender instance."""
    global _blender_instance
    if _blender_instance is None:
        _blender_instance = UserEmbeddingBlender()
    return _blender_instance


def blend_user_embeddings(
    long_term: Optional[np.ndarray], session: Optional[np.ndarray], context: str = "feed"
) -> Optional[np.ndarray]:
    """
    Convenience function to blend user embeddings.

    Args:
        long_term: Long-term embedding
        session: Session embedding
        context: Context ('feed', 'search', etc.)

    Returns:
        Blended embedding
    """
    blender = get_user_blender()
    result = blender.blend(long_term, session, context=context)

    if result["success"]:
        return result["blended_embedding"]
    else:
        return None
