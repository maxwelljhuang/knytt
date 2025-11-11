"""
Feedback Handler
Processes user interaction events and updates embeddings in real-time.
"""

import logging
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import get_ml_config, MLConfig
from ..user_modeling.warm_user import WarmUserEmbedding
from ..user_modeling.session import SessionManager
from ..caching import EmbeddingCache

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of user interactions with products."""

    VIEW = "view"
    LIKE = "like"
    DISLIKE = "dislike"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    PURCHASE = "purchase"
    CLICK = "click"
    DISMISS = "dismiss"


@dataclass
class InteractionEvent:
    """
    User interaction event.

    Represents a single user interaction with a product.
    """

    user_id: int
    product_id: int
    interaction_type: InteractionType
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Optional context
    session_id: Optional[str] = None
    search_query: Optional[str] = None
    context: Optional[str] = None  # 'feed', 'search', 'similar', etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "user_id": self.user_id,
            "product_id": self.product_id,
            "interaction_type": self.interaction_type.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "search_query": self.search_query,
            "context": self.context,
            "metadata": self.metadata,
        }


class FeedbackHandler:
    """
    Handles user feedback events and updates embeddings.

    Maps interaction types to embedding update weights:
    - Positive: like, thumbs_up, purchase, add_to_cart
    - Negative: dislike, thumbs_down, dismiss
    - Neutral: view, click
    """

    def __init__(self, config: Optional[MLConfig] = None, db_session_factory=None):
        """
        Initialize feedback handler.

        Args:
            config: ML configuration
            db_session_factory: Database session factory for persistence
        """
        self.config = config or get_ml_config()
        self.db_session_factory = db_session_factory

        # Initialize components
        self.warm_updater = WarmUserEmbedding()
        self.session_manager = SessionManager()
        self.cache = EmbeddingCache(self.config)

        # Interaction weights for embedding updates
        self.interaction_weights = {
            InteractionType.PURCHASE: 2.0,
            InteractionType.THUMBS_UP: 1.5,
            InteractionType.LIKE: 1.0,
            InteractionType.ADD_TO_CART: 0.8,
            InteractionType.CLICK: 0.3,
            InteractionType.VIEW: 0.1,
            InteractionType.DISMISS: -0.3,
            InteractionType.REMOVE_FROM_CART: -0.5,
            InteractionType.THUMBS_DOWN: -1.0,
            InteractionType.DISLIKE: -1.5,
        }

        logger.info("Feedback handler initialized")

    def process_event(
        self,
        event: InteractionEvent,
        product_embedding: Optional[np.ndarray] = None,
        update_long_term: bool = True,
        update_session: bool = True,
        persist_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a single interaction event.

        Args:
            event: Interaction event to process
            product_embedding: Product embedding (fetched if not provided)
            update_long_term: Whether to update long-term embedding
            update_session: Whether to update session embedding
            persist_to_db: Whether to save to database

        Returns:
            Dict with update results
        """
        logger.info(
            f"Processing {event.interaction_type.value} event: "
            f"user={event.user_id}, product={event.product_id}"
        )

        result = {
            "event": event.to_dict(),
            "long_term_updated": False,
            "session_updated": False,
            "cache_updated": False,
            "db_persisted": False,
        }

        # Get product embedding if not provided
        if product_embedding is None:
            product_embedding = self._get_product_embedding(event.product_id)

        if product_embedding is None:
            logger.warning(f"No embedding found for product {event.product_id}")
            result["error"] = "product_embedding_not_found"
            return result

        # Get interaction weight
        weight = self.interaction_weights.get(event.interaction_type, 0.0)

        # Update long-term embedding
        if update_long_term and weight != 0:
            new_long_term = self._update_long_term_embedding(
                user_id=event.user_id, product_embedding=product_embedding, weight=weight
            )

            if new_long_term is not None:
                result["long_term_updated"] = True
                result["new_long_term_embedding"] = new_long_term

        # Update session embedding
        if update_session:
            new_session = self._update_session_embedding(
                user_id=event.user_id,
                product_embedding=product_embedding,
                interaction_type=event.interaction_type,
            )

            if new_session is not None:
                result["session_updated"] = True
                result["new_session_embedding"] = new_session

        # Track hot products
        if event.interaction_type in [InteractionType.VIEW, InteractionType.CLICK]:
            self.cache.track_product_view(event.product_id)

        # Persist to database
        if persist_to_db and self.db_session_factory:
            persisted = self._persist_event(event)
            result["db_persisted"] = persisted

        # Log event for analytics
        self._log_event(event)

        return result

    def process_thumbs_up(
        self, user_id: int, product_id: int, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process thumbs up feedback.

        Args:
            user_id: User ID
            product_id: Product ID
            context: Context where feedback was given

        Returns:
            Processing result
        """
        event = InteractionEvent(
            user_id=user_id,
            product_id=product_id,
            interaction_type=InteractionType.THUMBS_UP,
            context=context,
        )

        return self.process_event(event)

    def process_thumbs_down(
        self, user_id: int, product_id: int, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process thumbs down feedback.

        Args:
            user_id: User ID
            product_id: Product ID
            context: Context where feedback was given

        Returns:
            Processing result
        """
        event = InteractionEvent(
            user_id=user_id,
            product_id=product_id,
            interaction_type=InteractionType.THUMBS_DOWN,
            context=context,
        )

        return self.process_event(event)

    def process_like(self, user_id: int, product_id: int) -> Dict[str, Any]:
        """Process like event."""
        event = InteractionEvent(
            user_id=user_id, product_id=product_id, interaction_type=InteractionType.LIKE
        )

        return self.process_event(event)

    def process_purchase(
        self, user_id: int, product_id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process purchase event.

        Args:
            user_id: User ID
            product_id: Product ID
            metadata: Optional purchase metadata (price, quantity, etc.)

        Returns:
            Processing result
        """
        event = InteractionEvent(
            user_id=user_id,
            product_id=product_id,
            interaction_type=InteractionType.PURCHASE,
            metadata=metadata or {},
        )

        return self.process_event(event)

    def _update_long_term_embedding(
        self, user_id: int, product_embedding: np.ndarray, weight: float
    ) -> Optional[np.ndarray]:
        """
        Update user's long-term embedding.

        Args:
            user_id: User ID
            product_embedding: Product embedding to incorporate
            weight: Interaction weight

        Returns:
            New long-term embedding or None
        """
        # Get current long-term embedding
        current_embedding = self._get_user_long_term_embedding(user_id)

        if current_embedding is None:
            # Initialize with product embedding for cold-start users
            logger.info(f"Initializing long-term embedding for user {user_id}")
            new_embedding = product_embedding.copy()
        else:
            # Update with EWMA
            new_embedding = self.warm_updater.update_embedding(
                current_embedding=current_embedding,
                interaction_embedding=product_embedding,
                interaction_weight=abs(weight),  # Use absolute value for strength
            )

            # If negative interaction, move away from the embedding
            if weight < 0:
                # Move in opposite direction
                new_embedding = current_embedding - 0.1 * (product_embedding - current_embedding)
                new_embedding = new_embedding / np.linalg.norm(new_embedding)

        # Cache the new embedding
        self.cache.set_user_long_term_embedding(user_id, new_embedding)

        logger.debug(f"Updated long-term embedding for user {user_id}")

        return new_embedding

    def _update_session_embedding(
        self, user_id: int, product_embedding: np.ndarray, interaction_type: InteractionType
    ) -> Optional[np.ndarray]:
        """
        Update user's session embedding.

        Args:
            user_id: User ID
            product_embedding: Product embedding
            interaction_type: Type of interaction

        Returns:
            New session embedding or None
        """
        # Only update session for positive interactions
        if interaction_type in [
            InteractionType.VIEW,
            InteractionType.CLICK,
            InteractionType.LIKE,
            InteractionType.THUMBS_UP,
            InteractionType.ADD_TO_CART,
            InteractionType.PURCHASE,
        ]:
            new_session = self.session_manager.add_interaction(
                user_id=user_id, product_embedding=product_embedding
            )

            # Cache the session embedding
            if new_session is not None:
                self.cache.set_user_session_embedding(user_id, new_session)

            logger.debug(f"Updated session embedding for user {user_id}")

            return new_session

        return None

    def _get_product_embedding(self, product_id: int) -> Optional[np.ndarray]:
        """
        Get product embedding (from cache or database).

        Args:
            product_id: Product ID

        Returns:
            Product embedding or None
        """
        # Try cache first
        embedding = self.cache.get_product_embedding(product_id)

        if embedding is not None:
            return embedding

        # TODO: Fetch from database if not in cache
        # For now, return None
        logger.warning(f"Product {product_id} embedding not in cache")

        return None

    def _get_user_long_term_embedding(self, user_id: int) -> Optional[np.ndarray]:
        """
        Get user's long-term embedding (from cache or database).

        Args:
            user_id: User ID

        Returns:
            Long-term embedding or None
        """
        # Try cache first
        embedding = self.cache.get_user_long_term_embedding(user_id)

        if embedding is not None:
            return embedding

        # TODO: Fetch from database if not in cache
        # For now, return None
        logger.debug(f"User {user_id} long-term embedding not in cache")

        return None

    def _persist_event(self, event: InteractionEvent) -> bool:
        """
        Persist event to database.

        Args:
            event: Interaction event

        Returns:
            True if persisted successfully
        """
        # TODO: Implement database persistence
        # This would insert into an interactions/events table for analytics
        logger.debug(f"Event persistence not yet implemented: {event.to_dict()}")
        return False

    def _log_event(self, event: InteractionEvent) -> None:
        """
        Log event for analytics.

        Args:
            event: Interaction event
        """
        # Log to application logs (can be shipped to analytics platform)
        logger.info(f"FEEDBACK_EVENT: {event.to_dict()}")


class FeedbackProcessor:
    """
    Batch processor for feedback events.

    Useful for processing events asynchronously or in batches.
    """

    def __init__(
        self, handler: Optional[FeedbackHandler] = None, config: Optional[MLConfig] = None
    ):
        """
        Initialize feedback processor.

        Args:
            handler: Feedback handler (creates new one if not provided)
            config: ML configuration
        """
        self.config = config or get_ml_config()
        self.handler = handler or FeedbackHandler(config=self.config)

        logger.info("Feedback processor initialized")

    def process_batch(self, events: List[InteractionEvent]) -> Dict[str, Any]:
        """
        Process a batch of interaction events.

        Args:
            events: List of interaction events

        Returns:
            Dict with batch processing results
        """
        if not events:
            return {"total": 0, "processed": 0, "errors": 0}

        logger.info(f"Processing batch of {len(events)} events")

        results = []
        errors = []

        for event in events:
            try:
                result = self.handler.process_event(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing event {event.to_dict()}: {e}")
                errors.append({"event": event.to_dict(), "error": str(e)})

        return {
            "total": len(events),
            "processed": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors,
        }

    def process_user_session(self, user_id: int, interactions: List[tuple]) -> Dict[str, Any]:
        """
        Process all interactions from a user session.

        Args:
            user_id: User ID
            interactions: List of (product_id, interaction_type) tuples

        Returns:
            Processing results
        """
        events = [
            InteractionEvent(
                user_id=user_id, product_id=product_id, interaction_type=interaction_type
            )
            for product_id, interaction_type in interactions
        ]

        return self.process_batch(events)
