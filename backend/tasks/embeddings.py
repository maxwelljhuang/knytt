"""
Embedding Generation Tasks
Background tasks for generating and updating product embeddings
"""

import logging
from typing import Dict, Any, List, Optional

from .celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True, name="tasks.generate_product_embeddings", max_retries=2, default_retry_delay=180
)
def generate_product_embeddings(
    self,
    product_ids: Optional[List[str]] = None,
    batch_size: int = 16,
    force_regenerate: bool = False,
    embedding_type: str = "text",
) -> Dict[str, Any]:
    """
    Generate embeddings for products using CLIP.

    This task:
    1. Fetches product data from database
    2. Creates text representations for CLIP encoding
    3. Generates embeddings in batches using the model registry
    4. Stores embeddings in the database
    5. Optionally caches embeddings in Redis

    Args:
        product_ids: Optional list of specific product UUIDs to process. If None, process all.
        batch_size: Number of products to process at once (default: 16)
        force_regenerate: If True, regenerate even if embeddings exist
        embedding_type: Type of embedding to generate ('text', 'image', or 'multimodal')

    Returns:
        Dictionary with generation results
    """
    from sqlalchemy import select, and_, func
    from sqlalchemy.dialects.postgresql import insert
    from uuid import UUID

    try:
        logger.info(
            f"Starting {embedding_type} embedding generation for "
            f"{len(product_ids) if product_ids else 'all'} products"
        )

        # Import here to avoid circular dependencies and early model loading
        from ..db.session import SessionLocal
        from ..db.models import Product, ProductEmbedding
        from ..ml.model_loader import model_registry, TORCH_AVAILABLE

        if not TORCH_AVAILABLE:
            logger.error("PyTorch not available - cannot generate embeddings")
            return {
                "status": "error",
                "error": "PyTorch not available",
                "processed": 0,
            }

        # Create database session
        db = SessionLocal()

        try:
            # Build query for products to process
            if product_ids:
                # Process specific products
                uuid_list = [UUID(pid) if isinstance(pid, str) else pid for pid in product_ids]
                query = select(Product).where(
                    and_(Product.id.in_(uuid_list), Product.is_duplicate == False)
                )
            else:
                # Process all non-duplicate products
                if force_regenerate:
                    query = select(Product).where(Product.is_duplicate == False)
                else:
                    # Only process products without embeddings
                    query = select(Product).where(
                        and_(Product.is_duplicate == False, Product.text_embedding.is_(None))
                    )

            query = query.order_by(Product.id)
            products = db.execute(query).scalars().all()
            total = len(products)

            logger.info(f"Found {total} products to process")

            if total == 0:
                return {
                    "status": "success",
                    "processed": 0,
                    "skipped": 0,
                    "failed": 0,
                    "message": "No products to process",
                }

            # Load CLIP model
            logger.info("Loading CLIP model...")
            model_registry.get_clip_model()
            logger.info(f"Model loaded on {model_registry.get_device()}")

            # Process in batches
            successful = 0
            skipped = 0
            failed = 0
            error_details = []

            for i in range(0, total, batch_size):
                batch = products[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total + batch_size - 1) // batch_size

                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)")

                try:
                    # Create text representations
                    texts = []
                    batch_product_ids = []

                    for product in batch:
                        text = _create_text_representation(product)
                        texts.append(text)
                        batch_product_ids.append(product.id)

                    # Generate embeddings
                    embeddings = model_registry.encode_text_batch(texts)

                    # Store in database
                    for product, embedding in zip(batch, embeddings):
                        try:
                            # Store in ProductEmbedding table
                            stmt = (
                                insert(ProductEmbedding)
                                .values(
                                    product_id=product.id,
                                    embedding_type=embedding_type,
                                    embedding=embedding.tolist(),
                                    model_version="ViT-B-32",
                                )
                                .on_conflict_do_update(
                                    index_elements=["product_id", "embedding_type"],
                                    set_={
                                        "embedding": embedding.tolist(),
                                        "model_version": "ViT-B-32",
                                    },
                                )
                            )
                            db.execute(stmt)

                            # Also update denormalized column on Product table for fast access
                            product.text_embedding = embedding.tolist()

                            # Commit each product immediately to avoid transaction abort issues
                            db.commit()
                            successful += 1

                        except Exception as e:
                            # Rollback this specific product's transaction
                            db.rollback()
                            failed += 1
                            error_msg = f"Product {product.id}: {str(e)}"
                            error_details.append(error_msg)
                            logger.error(error_msg)
                    logger.info(f"Batch {batch_num} complete ({successful}/{total} processed)")

                except Exception as e:
                    db.rollback()
                    logger.error(f"Batch {batch_num} failed: {e}", exc_info=True)
                    failed += len(batch)
                    error_details.append(f"Batch {batch_num}: {str(e)}")

            # Summary
            logger.info("=" * 60)
            logger.info(f"Embedding generation complete: {successful}/{total} successful")
            logger.info("=" * 60)

            return {
                "status": "success" if failed == 0 else "partial",
                "processed": successful,
                "skipped": skipped,
                "failed": failed,
                "total": total,
                "embedding_type": embedding_type,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "errors": error_details[:10],  # Limit error details
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)

        # Retry on failure
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for embedding generation")
            return {
                "status": "error",
                "error": str(e),
                "processed": 0,
                "retries_exceeded": True,
            }


def _create_text_representation(product) -> str:
    """
    Create text representation for CLIP encoding.

    Args:
        product: Product model instance

    Returns:
        Text string for embedding
    """
    parts = []

    if product.product_name:
        parts.append(product.product_name)

    if product.brand_name:
        parts.append(f"by {product.brand_name}")

    if product.description:
        desc = product.description
        if len(desc) > 200:
            desc = desc[:197] + "..."
        parts.append(desc)

    if product.colour:
        parts.append(f"color: {product.colour}")

    if product.fashion_size:
        parts.append(f"size: {product.fashion_size}")

    return " ".join(parts)


@app.task(bind=True, name="tasks.rebuild_faiss_index", max_retries=1, default_retry_delay=300)
def rebuild_faiss_index(self, embedding_type: str = "text") -> Dict[str, Any]:
    """
    Rebuild the FAISS index from all product embeddings in database.

    This task:
    1. Fetches all product embeddings from PostgreSQL
    2. Builds a new FAISS index using FAISSIndexBuilder
    3. Saves the index to disk with metadata
    4. Returns statistics about the rebuild

    Args:
        embedding_type: Type of embedding to index ('text', 'image', or 'multimodal')

    Returns:
        Dictionary with rebuild results
    """
    from sqlalchemy import select
    import numpy as np

    try:
        logger.info(f"Starting FAISS index rebuild for {embedding_type} embeddings")

        # Import here to avoid circular dependencies and early loading
        from ..db.session import SessionLocal
        from ..db.models import Product, ProductEmbedding
        from ..ml.retrieval.index_builder import FAISSIndexBuilder

        # Create database session
        db = SessionLocal()

        try:
            # Fetch all product embeddings from database
            logger.info("Fetching product embeddings from database...")

            # Query products with embeddings
            if embedding_type == "text":
                # Use denormalized column on Product table for performance
                query = select(Product).where(Product.text_embedding.isnot(None))
                results = db.execute(query).scalars().all()

                embeddings_list = []
                product_ids = []

                for product in results:
                    if product.text_embedding is not None:
                        # Handle both list and array formats
                        if isinstance(product.text_embedding, (list, tuple)):
                            emb = np.array(product.text_embedding, dtype=np.float32)
                        else:
                            emb = np.array(product.text_embedding, dtype=np.float32)

                        embeddings_list.append(emb)
                        product_ids.append(str(product.id))

            else:
                # For other types, use ProductEmbedding table
                query = select(ProductEmbedding).where(
                    ProductEmbedding.embedding_type == embedding_type
                )
                results = db.execute(query).scalars().all()

                embeddings_list = []
                product_ids = []

                for prod_emb in results:
                    # Try embedding_vector first (pgvector), then embedding (legacy)
                    emb_data = (
                        prod_emb.embedding_vector
                        if hasattr(prod_emb, "embedding_vector")
                        and prod_emb.embedding_vector is not None
                        else prod_emb.embedding
                    )

                    if emb_data is not None:
                        if isinstance(emb_data, (list, tuple)):
                            emb = np.array(emb_data, dtype=np.float32)
                        else:
                            emb = np.array(emb_data, dtype=np.float32)

                        embeddings_list.append(emb)
                        product_ids.append(str(prod_emb.product_id))

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

            return {
                "status": "success",
                "embedding_type": embedding_type,
                "num_vectors": stats["num_vectors"],
                "index_type": stats["index_type"],
                "save_path": str(save_path),
                "stats": stats,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error rebuilding FAISS index: {e}", exc_info=True)

        # Retry on failure
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for FAISS index rebuild")
            return {
                "status": "error",
                "embedding_type": embedding_type,
                "error": str(e),
                "retries_exceeded": True,
            }


@app.task(bind=True, name="tasks.update_user_embedding", max_retries=3, default_retry_delay=60)
def update_user_embedding(
    self, user_external_id: str, max_interactions: int = 50
) -> Dict[str, Any]:
    """
    Update user's long-term embedding based on interaction history.

    This task:
    1. Fetches user's recent interactions from database
    2. Retrieves product embeddings for those interactions
    3. Applies EWMA to update the user's long-term embedding
    4. Saves updated embedding to database and cache

    Args:
        user_external_id: User external ID (from API)
        max_interactions: Maximum number of recent interactions to consider

    Returns:
        Dictionary with update results
    """
    from sqlalchemy import select
    from uuid import UUID

    try:
        logger.info(f"Updating long-term embedding for user {user_external_id}")

        # Import here to avoid circular dependencies and early loading
        from ..db.session import SessionLocal
        from ..db.models import User
        from ..ml.user_modeling import get_embedding_builder
        from ..ml.caching import EmbeddingCache

        # Create database session
        db = SessionLocal()
        cache = None

        try:
            # Initialize cache (optional, gracefully handles Redis unavailability)
            try:
                cache = EmbeddingCache()
            except Exception as e:
                logger.warning(f"Cache unavailable, continuing without cache: {e}")

            # Get user UUID from external_id
            user = db.execute(
                select(User).where(User.external_id == user_external_id)
            ).scalar_one_or_none()

            if user is None:
                logger.error(f"User not found: {user_external_id}")
                return {"status": "error", "user_id": user_external_id, "error": "User not found"}

            # Create embedding builder
            builder = get_embedding_builder(db=db, cache=cache)

            # Update user embedding from interaction history
            success, metadata = builder.update_user_embedding(
                user_id=user.id, max_interactions=max_interactions
            )

            if success:
                logger.info(
                    f"Updated user embedding for {user_external_id}: "
                    f"status={metadata.get('status')}, "
                    f"confidence={metadata.get('confidence', 0):.2f}, "
                    f"processed={metadata.get('processed_count', 0)}/{metadata.get('interaction_count', 0)}"
                )
                return {
                    "status": "success",
                    "user_id": user_external_id,
                    "metadata": metadata,
                }
            else:
                error_msg = metadata.get("error", "Unknown error")
                logger.error(f"Failed to update user embedding: {error_msg}")
                return {
                    "status": "error",
                    "user_id": user_external_id,
                    "error": error_msg,
                }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error updating user embedding for {user_external_id}: {e}", exc_info=True)

        # Retry on failure
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for user {user_external_id}")
            return {
                "status": "error",
                "user_id": user_external_id,
                "error": str(e),
                "retries_exceeded": True,
            }


@app.task(bind=True, name="tasks.batch_refresh_user_embeddings")
def batch_refresh_user_embeddings(
    self, hours_active: int = 24, batch_size: int = 50
) -> Dict[str, Any]:
    """
    Refresh embeddings for users who were active in the last N hours.

    This periodic task:
    1. Finds users with recent interactions
    2. Triggers embedding updates for each active user
    3. Returns stats on refreshed embeddings

    Args:
        hours_active: Only refresh users active in last N hours (default: 24)
        batch_size: Maximum number of users to process (default: 50)

    Returns:
        Dictionary with refresh results
    """
    from sqlalchemy import select, func
    from datetime import datetime, timedelta

    try:
        logger.info(f"Starting batch user embedding refresh (active in last {hours_active}h)")

        # Import here to avoid circular dependencies
        from ..db.session import SessionLocal
        from ..db.models import User, UserInteraction

        # Create database session
        db = SessionLocal()

        try:
            # Find users with recent interactions
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_active)

            # Query for active users
            query = (
                select(User.external_id, func.count(UserInteraction.id).label("interaction_count"))
                .join(UserInteraction, User.id == UserInteraction.user_id)
                .where(UserInteraction.created_at >= cutoff_time)
                .group_by(User.external_id)
                .order_by(func.count(UserInteraction.id).desc())
                .limit(batch_size)
            )

            results = db.execute(query).all()
            active_users = [(row[0], row[1]) for row in results]

            logger.info(f"Found {len(active_users)} active users")

            if len(active_users) == 0:
                return {
                    "status": "success",
                    "refreshed": 0,
                    "message": "No active users to refresh",
                }

            # Trigger embedding update for each user
            successful = 0
            failed = 0
            task_ids = []

            for user_external_id, interaction_count in active_users:
                try:
                    # Dispatch update task
                    result = update_user_embedding.delay(
                        user_external_id=user_external_id,
                        max_interactions=100,  # Use more interactions for periodic refresh
                    )
                    task_ids.append(result.id)
                    successful += 1

                    logger.debug(
                        f"Dispatched refresh for user {user_external_id} "
                        f"({interaction_count} interactions, task {result.id})"
                    )

                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to dispatch refresh for user {user_external_id}: {e}")

            logger.info(
                f"Batch user embedding refresh complete: {successful}/{len(active_users)} dispatched"
            )

            return {
                "status": "success",
                "active_users": len(active_users),
                "refreshed": successful,
                "failed": failed,
                "task_ids": task_ids[:10],  # Limit task IDs in response
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in batch user embedding refresh: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }


@app.task(bind=True, name="tasks.cleanup_old_sessions")
def cleanup_old_sessions(self, days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old session data and expired caches.

    This periodic task:
    1. Removes session embeddings older than N days
    2. Cleans up expired cache entries
    3. Optionally marks old interactions as processed

    Args:
        days_old: Delete sessions older than N days (default: 7)

    Returns:
        Dictionary with cleanup results
    """
    from sqlalchemy import select, delete
    from datetime import datetime, timedelta

    try:
        logger.info(f"Starting session cleanup (older than {days_old} days)")

        # Import here to avoid circular dependencies
        from ..db.session import SessionLocal
        from ..db.models import UserEmbedding
        from ..ml.caching import EmbeddingCache

        # Create database session
        db = SessionLocal()
        cache = None

        try:
            # Initialize cache (optional)
            try:
                cache = EmbeddingCache()
            except Exception as e:
                logger.warning(f"Cache unavailable, skipping cache cleanup: {e}")

            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Clean up old session embeddings from database
            # Only delete session-type embeddings, keep long-term
            delete_stmt = delete(UserEmbedding).where(
                UserEmbedding.embedding_type == "session", UserEmbedding.updated_at < cutoff_date
            )

            result = db.execute(delete_stmt)
            deleted_count = result.rowcount
            db.commit()

            logger.info(f"Deleted {deleted_count} old session embeddings from database")

            # Clean up cache if available
            cache_cleaned = 0
            if cache:
                try:
                    # Note: Redis handles TTL expiration automatically
                    # This is just a placeholder for any manual cleanup needed
                    logger.info("Cache cleanup handled by Redis TTL")
                except Exception as e:
                    logger.warning(f"Cache cleanup error: {e}")

            logger.info(f"Session cleanup complete: {deleted_count} sessions removed")

            return {
                "status": "success",
                "deleted_sessions": deleted_count,
                "cache_cleaned": cache_cleaned,
                "cutoff_date": cutoff_date.isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in session cleanup: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
