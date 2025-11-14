"""
Feedback Endpoint
POST /feedback - Record user-product interactions for personalization.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...ml.caching import EmbeddingCache
from ..config import APISettings, get_settings
from ..dependencies import get_db, get_embedding_cache, get_request_id
from ..errors import APIError
from ..models.feedback import (
    INTERACTION_WEIGHTS,
    SESSION_DECAY,
    FeedbackRequest,
    FeedbackResponse,
    InteractionType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_200_OK)
async def record_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    cache: EmbeddingCache = Depends(get_embedding_cache),
    settings: APISettings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
) -> FeedbackResponse:
    """
    Record user-product interaction for personalization.

    Workflow:
    1. Validate request
    2. Store interaction in database
    3. Update session embeddings (if requested)
    4. Trigger user embedding update (background if requested)
    5. Invalidate cached recommendations
    6. Return confirmation

    Args:
        request: Feedback request with user_id, product_id, interaction_type
        background_tasks: FastAPI background tasks
        db: Database session
        cache: Embedding cache
        settings: API settings
        request_id: Request ID for tracing

    Returns:
        Feedback response with status and update flags
    """
    start_time = time.time()

    logger.info(
        f"Feedback: user={request.user_id}, product={request.product_id}, "
        f"type={request.interaction_type}",
        extra={"request_id": request_id},
    )

    # Step 1: Validate interaction type has rating if needed
    if request.interaction_type == InteractionType.RATING and request.rating is None:
        raise APIError(message="rating field required for interaction_type=rating", status_code=400)

    # Step 2: Store interaction in database
    interaction_id = _store_interaction(request, db)

    # Step 3: Update session embeddings
    session_updated = False
    if request.update_session:
        session_updated = _update_session_embeddings(
            user_id=request.user_id,
            product_id=request.product_id,
            interaction_type=request.interaction_type,
            cache=cache,
            db=db,
        )

    # Step 4: Trigger user embedding update (Celery task)
    embeddings_updated = False
    task_id = None
    if request.update_embeddings:
        # Dispatch Celery task for async processing
        from ...tasks.embeddings import update_user_embedding

        result = update_user_embedding.delay(
            user_external_id=str(request.user_id), max_interactions=50
        )
        task_id = result.id
        embeddings_updated = True  # Marked as queued

        logger.debug(f"Dispatched embedding update task {task_id} for user {request.user_id}")

    # Step 5: Invalidate cached recommendations
    cache_invalidated = False
    if settings.enable_cache:
        cache_invalidated = _invalidate_user_cache(user_id=request.user_id, cache=cache)

    # Step 6: Build response
    processing_time_ms = (time.time() - start_time) * 1000

    response = FeedbackResponse(
        success=True,
        message="Feedback recorded",
        interaction_id=interaction_id,
        user_id=request.user_id,
        product_id=request.product_id,
        interaction_type=request.interaction_type.value,
        embeddings_updated=embeddings_updated,
        session_updated=session_updated,
        cache_invalidated=cache_invalidated,
        recorded_at=datetime.utcnow(),
        processing_time_ms=processing_time_ms,
    )

    logger.info(
        f"Feedback recorded: id={interaction_id}, processing_time={processing_time_ms:.2f}ms",
        extra={"request_id": request_id},
    )

    return response


def _store_interaction(request: FeedbackRequest, db: Session) -> Optional[str]:
    """
    Store interaction in database.

    Args:
        request: Feedback request
        db: Database session

    Returns:
        Interaction ID (UUID as string) or None if storage failed
    """
    try:
        from uuid import UUID

        from sqlalchemy import select

        from ...db.models import Product, User, UserInteraction

        # Get or create user
        # Try to parse as UUID first (database ID), fallback to external_id lookup
        user_id_str = str(request.user_id)
        user = None

        try:
            # Try as UUID (database ID)
            user_uuid = UUID(user_id_str)
            user = db.execute(
                select(User).where(User.id == user_uuid)
            ).scalar_one_or_none()

            if user:
                logger.debug(f"Found user by database ID: {user_uuid}")
        except ValueError:
            # Not a UUID, try external_id lookup
            user = db.execute(
                select(User).where(User.external_id == user_id_str)
            ).scalar_one_or_none()

            if user:
                logger.debug(f"Found user by external_id: {user_id_str}")

        if user is None:
            # Create new user with external_id (for external user systems)
            # Use placeholder email and password_hash for anonymous/external users
            user = User(
                external_id=user_id_str,
                email=f"{user_id_str}@anonymous.knytt.local",  # Placeholder email
                password_hash="",  # Empty password hash (external auth)
            )
            db.add(user)
            db.flush()  # Get the user ID
            logger.info(f"Created new user: external_id={user_id_str}, id={user.id}")

        # Get product by UUID (assume product_id is a UUID string)
        try:
            product_uuid = UUID(str(request.product_id))
            product = db.execute(
                select(Product).where(Product.id == product_uuid)
            ).scalar_one_or_none()

            if product is None:
                logger.warning(f"Product not found: {request.product_id}")
                raise APIError(
                    message="Product not found",
                    details={"product_id": request.product_id},
                    status_code=404,
                )
        except ValueError:
            # Not a valid UUID, try looking up by merchant_product_id
            logger.warning(
                f"Invalid product UUID: {request.product_id}, treating as merchant_product_id"
            )
            raise APIError(
                message="Invalid product ID format (expected UUID)",
                details={"product_id": request.product_id},
                status_code=400,
            )

        # Create interaction record
        interaction = UserInteraction(
            user_id=user.id,
            product_id=product.id,
            interaction_type=request.interaction_type.value,
            rating=request.rating,
            session_id=request.session_id,
            context=request.context,
            query=request.query,
            position=request.position,
            interaction_metadata=request.metadata or {},
        )

        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        # Update user stats
        user.total_interactions += 1
        user.last_active = datetime.utcnow()
        db.commit()

        logger.info(
            f"Stored interaction: id={interaction.id}, user={user.id}, product={product.id}"
        )
        return str(interaction.id)

    except APIError:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Failed to store interaction: {e}", exc_info=True)
        db.rollback()
        raise APIError(
            message="Failed to record feedback", details={"error": str(e)}, status_code=500
        )


def _update_session_embeddings(
    user_id: int,
    product_id: int,
    interaction_type: InteractionType,
    cache: EmbeddingCache,
    db: Session,
) -> bool:
    """
    Update user's session embeddings with new interaction.

    Uses exponential moving average to blend current session with new interaction.

    Args:
        user_id: User ID
        product_id: Product ID
        interaction_type: Type of interaction
        cache: Embedding cache
        db: Database session

    Returns:
        True if updated, False otherwise
    """
    try:
        # Get current session embedding
        user_embeddings = cache.get_user_embeddings(user_id)
        current_session = user_embeddings.get("session")

        # Get product embedding
        product_embedding = _get_product_embedding(product_id, cache, db)
        if product_embedding is None:
            logger.warning(f"Product embedding not found for product {product_id}")
            return False

        # Get interaction weight
        weight = INTERACTION_WEIGHTS.get(interaction_type, 0.3)

        # Blend with current session (if exists)
        if current_session is not None:
            # Exponential moving average: new = alpha * new + (1-alpha) * old
            alpha = 0.3  # Weight for new interaction
            updated_session = alpha * (weight * product_embedding) + (1 - alpha) * current_session
        else:
            # First interaction in session
            updated_session = weight * product_embedding

        # Normalize
        import numpy as np

        norm = np.linalg.norm(updated_session)
        if norm > 0:
            updated_session = updated_session / norm

        # Update cache
        decay_minutes = SESSION_DECAY.get(interaction_type, 10)
        success = cache.set_user_session_embedding(
            user_id=str(user_id),
            embedding=updated_session,
            ttl=decay_minutes * 60,  # Convert to seconds
        )

        if success:
            logger.debug(f"Updated session embeddings for user {user_id}")

        return success

    except Exception as e:
        logger.error(f"Failed to update session embeddings: {e}")
        return False


def _invalidate_user_cache(user_id: int, cache: EmbeddingCache) -> bool:
    """
    Invalidate cached recommendations and search results for user.

    Deletes:
    - All cached recommendation results for this user
    - All cached search results for this user
    - User embedding caches (will be refreshed on next request)

    Args:
        user_id: User ID
        cache: Embedding cache

    Returns:
        True if invalidated, False otherwise
    """
    try:
        keys_deleted = 0

        # Pattern 1: Recommendations containing this user_id
        # Cache keys follow pattern: recommend:{hash} where hash contains user:{user_id}
        pattern = f"recommend:*user:{user_id}*"

        try:
            cursor = 0
            while True:
                cursor, keys = cache.redis.connection.scan(cursor, match=pattern, count=100)
                if keys:
                    cache.redis.connection.delete(*keys)
                    keys_deleted += len(keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Failed to delete recommendation cache keys: {e}")

        # Pattern 2: Search results containing this user_id
        pattern = f"search:*user:{user_id}*"

        try:
            cursor = 0
            while True:
                cursor, keys = cache.redis.connection.scan(cursor, match=pattern, count=100)
                if keys:
                    cache.redis.connection.delete(*keys)
                    keys_deleted += len(keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Failed to delete search cache keys: {e}")

        # Pattern 3: User embedding caches
        # These will be refreshed when the embedding update task completes
        # But we can delete them now to force fresh lookup
        user_id_str = str(user_id)
        embedding_keys = [
            f"user_embeddings:{user_id_str}",
            f"user_long_term:{user_id_str}",
            f"user_session:{user_id_str}",
        ]

        try:
            for key in embedding_keys:
                try:
                    cache.redis.delete(key)
                    keys_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete embedding key {key}: {e}")
        except Exception as e:
            logger.warning(f"Failed to delete user embedding keys: {e}")

        logger.debug(f"Invalidated {keys_deleted} cache keys for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}", exc_info=True)
        return False


def _get_product_embedding(product_id: int, cache: EmbeddingCache, db: Session) -> Optional[any]:
    """
    Get product embedding from cache or database.

    Args:
        product_id: Product ID
        cache: Embedding cache
        db: Database session

    Returns:
        Product embedding vector or None
    """
    try:
        # Try cache first
        cache_key = f"product_embedding:{product_id}"
        cached = cache.redis.get(cache_key)
        if cached is not None:
            return cached

        # TODO: Fetch from FAISS index or database
        # For now, return None
        logger.warning(f"Product embedding lookup not implemented for product {product_id}")
        return None

    except Exception as e:
        logger.error(f"Failed to get product embedding: {e}")
        return None
