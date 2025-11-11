"""
Admin Endpoints
POST /admin/rebuild-index - Manually trigger FAISS index rebuild
POST /admin/generate-embeddings - Manually trigger product embedding generation
POST /admin/clear-cache - Clear Redis cache
POST /admin/refresh-user-embeddings - Refresh user embeddings
GET /admin/task-status/{task_id} - Check Celery task status
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings, APISettings
from ..dependencies import get_db, get_embedding_cache
from ...ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Request/Response Models
class RebuildIndexRequest(BaseModel):
    embedding_type: str = Field(default="text", description="Type of embedding to index")


class RebuildIndexResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(..., description="Success message")


class GenerateEmbeddingsRequest(BaseModel):
    product_ids: Optional[List[str]] = Field(None, description="Specific product UUIDs to process")
    batch_size: int = Field(default=16, ge=1, le=100, description="Batch size")
    force_regenerate: bool = Field(default=False, description="Regenerate existing embeddings")
    embedding_type: str = Field(default="text", description="Type of embedding")


class GenerateEmbeddingsResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(..., description="Success message")
    product_count: Optional[int] = Field(None, description="Number of products queued")


class RefreshUserEmbeddingsRequest(BaseModel):
    user_ids: Optional[List[int]] = Field(None, description="Specific user IDs to refresh")
    hours_active: int = Field(default=24, ge=1, description="Refresh users active in last N hours")
    batch_size: int = Field(default=50, ge=1, le=1000, description="Max users to process")


class RefreshUserEmbeddingsResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(..., description="Success message")
    user_count: Optional[int] = Field(None, description="Number of users queued")


class ClearCacheRequest(BaseModel):
    cache_type: str = Field(
        default="all",
        description="Type of cache to clear: 'all', 'embeddings', 'search', 'recommendations'",
    )
    user_id: Optional[int] = Field(None, description="Clear cache for specific user")


class ClearCacheResponse(BaseModel):
    status: str = Field(..., description="Status")
    message: str = Field(..., description="Result message")
    keys_cleared: Optional[int] = Field(None, description="Number of keys cleared")


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status (PENDING, STARTED, SUCCESS, FAILURE)")
    result: Optional[dict] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# Endpoints
@router.post(
    "/rebuild-index", response_model=RebuildIndexResponse, status_code=status.HTTP_202_ACCEPTED
)
async def rebuild_faiss_index(
    request: RebuildIndexRequest, settings: APISettings = Depends(get_settings)
) -> RebuildIndexResponse:
    """
    Manually trigger FAISS index rebuild.

    This is a long-running operation that:
    1. Fetches all product embeddings from database
    2. Builds a new FAISS index
    3. Saves index to disk

    Returns immediately with task ID.
    """
    try:
        from ...tasks.embeddings import rebuild_faiss_index

        # Dispatch Celery task
        result = rebuild_faiss_index.delay(embedding_type=request.embedding_type)

        logger.info(
            f"FAISS index rebuild triggered: task_id={result.id}, type={request.embedding_type}"
        )

        return RebuildIndexResponse(
            task_id=result.id,
            status="queued",
            message=f"FAISS index rebuild queued for {request.embedding_type} embeddings",
        )

    except Exception as e:
        logger.error(f"Failed to trigger FAISS index rebuild: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger index rebuild: {str(e)}",
        )


@router.post(
    "/generate-embeddings",
    response_model=GenerateEmbeddingsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_product_embeddings(
    request: GenerateEmbeddingsRequest, settings: APISettings = Depends(get_settings)
) -> GenerateEmbeddingsResponse:
    """
    Manually trigger product embedding generation.

    This operation:
    1. Fetches products from database (all or specific IDs)
    2. Generates CLIP embeddings in batches
    3. Stores embeddings in database

    Returns immediately with task ID.
    """
    try:
        from ...tasks.embeddings import generate_product_embeddings

        # Dispatch Celery task
        result = generate_product_embeddings.delay(
            product_ids=request.product_ids,
            batch_size=request.batch_size,
            force_regenerate=request.force_regenerate,
            embedding_type=request.embedding_type,
        )

        product_count = len(request.product_ids) if request.product_ids else None
        scope = f"{product_count} products" if product_count else "all products"

        logger.info(f"Embedding generation triggered: task_id={result.id}, scope={scope}")

        return GenerateEmbeddingsResponse(
            task_id=result.id,
            status="queued",
            message=f"Embedding generation queued for {scope}",
            product_count=product_count,
        )

    except Exception as e:
        logger.error(f"Failed to trigger embedding generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger embedding generation: {str(e)}",
        )


@router.post(
    "/refresh-user-embeddings",
    response_model=RefreshUserEmbeddingsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_user_embeddings(
    request: RefreshUserEmbeddingsRequest,
    db: Session = Depends(get_db),
    settings: APISettings = Depends(get_settings),
) -> RefreshUserEmbeddingsResponse:
    """
    Manually trigger user embedding refresh.

    Options:
    - Refresh specific users by ID
    - Refresh all users active in last N hours

    Returns immediately with task ID.
    """
    try:
        if request.user_ids:
            # Refresh specific users
            from ...tasks.embeddings import update_user_embedding
            from ...db.models import User
            from sqlalchemy import select

            # Get external IDs for the user IDs
            user_ids_int = request.user_ids
            query = select(User.external_id).where(User.id.in_(user_ids_int))
            results = db.execute(query).scalars().all()
            external_ids = [str(ext_id) for ext_id in results]

            if not external_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No users found with specified IDs",
                )

            # Dispatch individual tasks
            task_ids = []
            for ext_id in external_ids:
                result = update_user_embedding.delay(user_external_id=ext_id)
                task_ids.append(result.id)

            logger.info(f"User embedding refresh triggered for {len(external_ids)} users")

            return RefreshUserEmbeddingsResponse(
                task_id=task_ids[0] if task_ids else "none",
                status="queued",
                message=f"Refresh queued for {len(external_ids)} users",
                user_count=len(external_ids),
            )

        else:
            # Refresh active users
            from ...tasks.embeddings import batch_refresh_user_embeddings

            result = batch_refresh_user_embeddings.delay(
                hours_active=request.hours_active, batch_size=request.batch_size
            )

            logger.info(f"Batch user embedding refresh triggered: task_id={result.id}")

            return RefreshUserEmbeddingsResponse(
                task_id=result.id,
                status="queued",
                message=f"Batch refresh queued for users active in last {request.hours_active}h",
                user_count=None,  # Will be determined by the task
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger user embedding refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger user embedding refresh: {str(e)}",
        )


@router.post("/clear-cache", response_model=ClearCacheResponse, status_code=status.HTTP_200_OK)
async def clear_cache(
    request: ClearCacheRequest,
    cache: EmbeddingCache = Depends(get_embedding_cache),
    settings: APISettings = Depends(get_settings),
) -> ClearCacheResponse:
    """
    Clear Redis cache.

    Options:
    - Clear all caches
    - Clear specific cache type (embeddings, search, recommendations)
    - Clear cache for specific user
    """
    try:
        if not settings.enable_cache:
            return ClearCacheResponse(
                status="skipped", message="Cache is disabled in settings", keys_cleared=0
            )

        keys_cleared = 0

        if request.user_id:
            # Clear user-specific cache
            user_id_str = str(request.user_id)

            # Clear user embeddings
            if request.cache_type in ["all", "embeddings"]:
                try:
                    cache.redis.delete(f"user_embeddings:{user_id_str}")
                    cache.redis.delete(f"user_long_term:{user_id_str}")
                    cache.redis.delete(f"user_session:{user_id_str}")
                    keys_cleared += 3
                except Exception as e:
                    logger.warning(f"Failed to clear user embeddings: {e}")

            # Clear user recommendations
            if request.cache_type in ["all", "recommendations"]:
                try:
                    # Delete all keys matching pattern
                    pattern = f"recommend:*user:{user_id_str}*"
                    cursor = 0
                    while True:
                        cursor, keys = cache.redis.connection.scan(cursor, match=pattern, count=100)
                        if keys:
                            cache.redis.connection.delete(*keys)
                            keys_cleared += len(keys)
                        if cursor == 0:
                            break
                except Exception as e:
                    logger.warning(f"Failed to clear user recommendations: {e}")

            message = f"Cleared cache for user {request.user_id}"

        else:
            # Clear all caches or specific type
            try:
                if request.cache_type == "all":
                    # Flush entire Redis database
                    cache.redis.connection.flushdb()
                    keys_cleared = -1  # Unknown count
                    message = "Cleared all cache"

                elif request.cache_type == "embeddings":
                    # Clear embedding caches
                    patterns = [
                        "user_embeddings:*",
                        "user_long_term:*",
                        "user_session:*",
                        "product_embedding:*",
                    ]
                    for pattern in patterns:
                        cursor = 0
                        while True:
                            cursor, keys = cache.redis.connection.scan(
                                cursor, match=pattern, count=100
                            )
                            if keys:
                                cache.redis.connection.delete(*keys)
                                keys_cleared += len(keys)
                            if cursor == 0:
                                break
                    message = f"Cleared {keys_cleared} embedding cache keys"

                elif request.cache_type == "search":
                    # Clear search result caches
                    pattern = "search:*"
                    cursor = 0
                    while True:
                        cursor, keys = cache.redis.connection.scan(cursor, match=pattern, count=100)
                        if keys:
                            cache.redis.connection.delete(*keys)
                            keys_cleared += len(keys)
                        if cursor == 0:
                            break
                    message = f"Cleared {keys_cleared} search cache keys"

                elif request.cache_type == "recommendations":
                    # Clear recommendation caches
                    pattern = "recommend:*"
                    cursor = 0
                    while True:
                        cursor, keys = cache.redis.connection.scan(cursor, match=pattern, count=100)
                        if keys:
                            cache.redis.connection.delete(*keys)
                            keys_cleared += len(keys)
                        if cursor == 0:
                            break
                    message = f"Cleared {keys_cleared} recommendation cache keys"

                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid cache_type: {request.cache_type}",
                    )

            except Exception as e:
                logger.error(f"Failed to clear cache: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to clear cache: {str(e)}",
                )

        logger.info(f"Cache cleared: type={request.cache_type}, keys={keys_cleared}")

        return ClearCacheResponse(
            status="success",
            message=message,
            keys_cleared=keys_cleared if keys_cleared >= 0 else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


@router.get(
    "/task-status/{task_id}", response_model=TaskStatusResponse, status_code=status.HTTP_200_OK
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Check the status of a Celery task.

    Returns task state and result (if completed).
    """
    try:
        from celery.result import AsyncResult
        from ...tasks.celery_app import app as celery_app

        # Get task result
        task_result = AsyncResult(task_id, app=celery_app)

        status_str = task_result.status  # PENDING, STARTED, SUCCESS, FAILURE, RETRY

        response = TaskStatusResponse(task_id=task_id, status=status_str, result=None, error=None)

        if status_str == "SUCCESS":
            response.result = task_result.result
        elif status_str == "FAILURE":
            response.error = str(task_result.info)

        return response

    except Exception as e:
        logger.error(f"Failed to get task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )
