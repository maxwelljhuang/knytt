"""
Admin Endpoints
POST /admin/rebuild-index - Manually trigger FAISS index rebuild
POST /admin/generate-embeddings - Manually trigger product embedding generation
POST /admin/clear-cache - Clear Redis cache
POST /admin/refresh-user-embeddings - Refresh user embeddings
GET /admin/task-status/{task_id} - Check Celery task status
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...ml.caching import EmbeddingCache
from ..config import APISettings, get_settings
from ..dependencies import get_db, get_embedding_cache

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
            from sqlalchemy import select

            from ...db.models import User
            from ...tasks.embeddings import update_user_embedding

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


@router.post("/generate-embeddings-sync", status_code=status.HTTP_200_OK)
async def generate_product_embeddings_sync(
    db: Session = Depends(get_db),
    batch_size: int = 16,
    max_products: int = 1000,
) -> dict:
    """
    Synchronously generate product embeddings (no Celery required).
    
    This endpoint runs the embedding generation directly and returns when complete.
    Suitable for Cloud Scheduler or manual triggers.
    
    Args:
        db: Database session
        batch_size: Number of products to process per batch
        max_products: Maximum number of products to process
        
    Returns:
        Result summary with counts
    """
    try:
        from sqlalchemy import text as sql_text
        from ...ml.model_loader import model_registry
        
        logger.info("Starting synchronous embedding generation")
        
        # Get products without embeddings
        result = db.execute(sql_text("""
            SELECT DISTINCT
                p.id,
                p.product_name,
                p.brand_name,
                p.description,
                p.colour,
                p.fashion_size
            FROM products p
            LEFT JOIN product_embeddings pe ON p.id = pe.product_id AND pe.embedding_type = 'text'
            WHERE p.is_duplicate = false AND pe.id IS NULL
            ORDER BY p.id
            LIMIT :max_products
        """), {"max_products": max_products})
        
        products = [dict(row._mapping) for row in result]
        total = len(products)
        
        logger.info(f"Found {total} products without embeddings")
        
        if total == 0:
            return {
                "status": "success",
                "processed": 0,
                "failed": 0,
                "message": "All products already have embeddings"
            }
        
        # Load CLIP model
        logger.info("Loading CLIP model...")
        model_registry.get_clip_model()
        logger.info(f"Model loaded on {model_registry.get_device()}")
        
        # Process in batches
        successful = 0
        failed = 0
        
        for i in range(0, total, batch_size):
            batch = products[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)")
            
            try:
                # Create text representations
                texts = []
                for p in batch:
                    parts = []
                    if p.get('product_name'):
                        parts.append(p['product_name'])
                    if p.get('brand_name'):
                        parts.append(f"by {p['brand_name']}")
                    if p.get('description'):
                        desc = p['description']
                        if len(desc) > 200:
                            desc = desc[:197] + "..."
                        parts.append(desc)
                    texts.append(" ".join(parts))
                
                # Generate embeddings
                embeddings = model_registry.encode_text_batch(texts)
                
                # Store in database
                for product, embedding in zip(batch, embeddings):
                    try:
                        db.execute(sql_text("""
                            INSERT INTO product_embeddings (
                                product_id,
                                embedding_type,
                                embedding,
                                model_version
                            ) VALUES (
                                :product_id,
                                'text',
                                :embedding,
                                'ViT-B-32'
                            )
                            ON CONFLICT (product_id, embedding_type)
                            DO UPDATE SET
                                embedding = EXCLUDED.embedding,
                                model_version = EXCLUDED.model_version,
                                updated_at = now()
                        """), {
                            'product_id': product['id'],
                            'embedding': embedding.tolist()
                        })
                        successful += 1
                    except Exception as e:
                        failed += 1
                        logger.error(f"Failed for product {product['id']}: {e}")
                
                # Commit batch
                db.commit()
                logger.info(f"Batch {batch_num} complete ({successful}/{total} total)")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Batch {batch_num} failed: {e}", exc_info=True)
                failed += len(batch)
        
        logger.info(f"Completed: {successful} successful, {failed} failed")
        return {
            "status": "success",
            "processed": successful,
            "failed": failed,
            "total": total,
            "message": f"Generated embeddings for {successful} products"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}"
        )


@router.post("/rebuild-index-sync", status_code=status.HTTP_200_OK)
async def rebuild_faiss_index_sync(
    embedding_type: str = "text",
    db: Session = Depends(get_db),
) -> dict:
    """
    Synchronously rebuild FAISS index from database embeddings (no Celery required).

    This endpoint:
    1. Fetches all product embeddings from database
    2. Builds a new FAISS index
    3. Saves index to disk and uploads to GCS
    4. Returns when complete

    Suitable for Cloud Scheduler or manual triggers.
    """
    try:
        import numpy as np
        from sqlalchemy import text as sql_text

        logger.info(f"Starting synchronous FAISS index rebuild for {embedding_type} embeddings")

        # Import FAISS builder
        from ...ml.retrieval.index_builder import FAISSIndexBuilder

        # Fetch all product embeddings from database
        logger.info("Fetching product embeddings from database...")

        if embedding_type == "text":
            # First try denormalized column on Product table for performance
            result = db.execute(sql_text("""
                SELECT id, text_embedding
                FROM products
                WHERE text_embedding IS NOT NULL
                ORDER BY id
            """))

            embeddings_list = []
            product_ids = []

            for row in result:
                product_id = str(row.id)
                text_embedding = row.text_embedding

                if text_embedding is not None:
                    # Handle both list and array formats
                    if isinstance(text_embedding, (list, tuple)):
                        emb = np.array(text_embedding, dtype=np.float32)
                    else:
                        emb = np.array(text_embedding, dtype=np.float32)

                    embeddings_list.append(emb)
                    product_ids.append(product_id)

            # If no embeddings found in denormalized column, fallback to product_embeddings table
            if len(embeddings_list) == 0:
                logger.info("No embeddings in denormalized column, falling back to product_embeddings table")
                result = db.execute(sql_text("""
                    SELECT product_id, embedding
                    FROM product_embeddings
                    WHERE embedding_type = 'text'
                    ORDER BY product_id
                """))

                for row in result:
                    product_id = str(row.product_id)
                    embedding_data = row.embedding

                    if embedding_data is not None:
                        if isinstance(embedding_data, (list, tuple)):
                            emb = np.array(embedding_data, dtype=np.float32)
                        else:
                            emb = np.array(embedding_data, dtype=np.float32)

                        embeddings_list.append(emb)
                        product_ids.append(product_id)
        else:
            # For other types, use ProductEmbedding table
            result = db.execute(sql_text("""
                SELECT product_id, embedding
                FROM product_embeddings
                WHERE embedding_type = :embedding_type
                ORDER BY product_id
            """), {"embedding_type": embedding_type})

            embeddings_list = []
            product_ids = []

            for row in result:
                product_id = str(row.product_id)
                embedding_data = row.embedding

                if embedding_data is not None:
                    if isinstance(embedding_data, (list, tuple)):
                        emb = np.array(embedding_data, dtype=np.float32)
                    else:
                        emb = np.array(embedding_data, dtype=np.float32)

                    embeddings_list.append(emb)
                    product_ids.append(product_id)

        if len(embeddings_list) == 0:
            logger.error(f"No {embedding_type} embeddings found in database")
            return {
                "status": "error",
                "error": f"No {embedding_type} embeddings found",
                "embedding_type": embedding_type,
            }

        # Convert to numpy array
        embeddings = np.vstack(embeddings_list)
        logger.info(f"Fetched {len(embeddings)} embeddings from database")

        # Build FAISS index
        logger.info("Building FAISS index...")
        builder = FAISSIndexBuilder()
        index, id_mapping = builder.build_index(embeddings=embeddings, product_ids=product_ids)

        # Save index to disk
        logger.info("Saving FAISS index to disk...")
        save_path = builder.save_index(index, id_mapping)

        # Get index stats
        stats = builder.get_index_stats(index)

        logger.info(
            f"FAISS index rebuilt successfully: "
            f"{stats['num_vectors']} vectors, "
            f"type={stats['index_type']}, "
            f"saved to {save_path}"
        )

        # Upload to GCS if configured
        gcs_uploaded = False
        gcs_bucket = os.getenv('GCS_FAISS_INDEX_BUCKET')
        gcs_path = os.getenv('GCS_FAISS_INDEX_PATH')

        if gcs_bucket and gcs_path:
            try:
                from ...ml.utils.gcs_utils import delete_faiss_index_from_gcs, upload_faiss_index_to_gcs

                # Delete old index from GCS first
                logger.info(f"Deleting old FAISS index from GCS: gs://{gcs_bucket}/{gcs_path}/")
                delete_faiss_index_from_gcs(
                    bucket_name=gcs_bucket,
                    gcs_path=gcs_path
                )

                # Upload new index to GCS
                logger.info(f"Uploading new FAISS index to GCS: gs://{gcs_bucket}/{gcs_path}/")
                gcs_uploaded = upload_faiss_index_to_gcs(
                    local_path=save_path,
                    bucket_name=gcs_bucket,
                    gcs_path=gcs_path
                )

                if gcs_uploaded:
                    logger.info(f"Successfully uploaded FAISS index to GCS")
                else:
                    logger.warning(f"Failed to upload FAISS index to GCS")
            except Exception as e:
                logger.error(f"Error managing GCS index: {e}", exc_info=True)
        else:
            logger.info("GCS upload skipped (GCS_FAISS_INDEX_BUCKET or GCS_FAISS_INDEX_PATH not configured)")

        return {
            "status": "success",
            "embedding_type": embedding_type,
            "num_vectors": stats["num_vectors"],
            "index_type": stats["index_type"],
            "save_path": str(save_path),
            "gcs_uploaded": gcs_uploaded,
            "gcs_bucket": gcs_bucket if gcs_bucket else None,
            "stats": stats,
            "message": f"FAISS index rebuilt with {stats['num_vectors']} vectors" + (f" and uploaded to GCS" if gcs_uploaded else "")
        }

    except Exception as e:
        logger.error(f"Failed to rebuild FAISS index: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild FAISS index: {str(e)}"
        )
