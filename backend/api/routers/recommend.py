"""
Recommend Endpoint
POST /recommend - Personalized product recommendations.
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...ml.caching import EmbeddingCache
from ...ml.retrieval import ProductFilters, create_user_context
from ...ml.search import SearchService
from ..config import APISettings, get_settings
from ..dependencies import get_db, get_embedding_cache, get_request_id, get_search_service
from ..errors import SearchError
from ..models.recommend import RecommendationContext, RecommendRequest, RecommendResponse
from ..models.search import ProductResult
from ..services.cache_service import CacheService, get_cache_service
from ..services.metadata_service import MetadataService, get_metadata_service
from ..services.text_encoder import TextEncoderService, get_text_encoder_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse, status_code=status.HTTP_200_OK)
async def recommend(
    request: RecommendRequest,
    db: Session = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
    text_encoder: TextEncoderService = Depends(get_text_encoder_service),
    metadata_service: MetadataService = Depends(get_metadata_service),
    cache: EmbeddingCache = Depends(get_embedding_cache),
    cache_service: CacheService = Depends(get_cache_service),
    settings: APISettings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
) -> RecommendResponse:
    """
    Generate personalized product recommendations for a user.

    Workflow:
    1. Check cache for results
    2. Load user embeddings (long-term + session)
    3. Build query vector based on context
    4. Apply filters
    5. Perform personalized search with FAISS
    6. Enrich results with product metadata
    7. Apply pagination
    8. Cache results
    9. Return response

    Args:
        request: Recommendation request with user_id and context
        db: Database session
        search_service: Search service instance
        text_encoder: Text encoder service
        metadata_service: Metadata service
        cache: Embedding cache
        settings: API settings
        request_id: Request ID for tracing

    Returns:
        Recommendation response with results and metadata
    """
    start_time = time.time()

    logger.info(
        f"Recommend request: user_id={request.user_id}, context={request.context}",
        extra={"request_id": request_id},
    )

    # Track user activity for cache warming
    cache_service.track_user_activity(request.user_id)
    if request.search_query:
        cache_service.track_query(request.search_query)

    # Generate cache key
    cache_key = _generate_cache_key(request)

    # Check cache if enabled
    cached_response = None
    if settings.enable_cache:
        cached_response = cache_service.get_recommend_results(cache_key)

        if cached_response:
            logger.info(
                f"Cache HIT for user {request.user_id}, context={request.context}",
                extra={"request_id": request_id},
            )
            cached_response["cached"] = True
            cached_response["total_time_ms"] = (time.time() - start_time) * 1000
            return RecommendResponse(**cached_response)

    logger.debug(f"Cache MISS for user {request.user_id}, context={request.context}")

    # Step 1: Load user embeddings from cache
    user_embeddings = cache.get_user_embeddings(request.user_id)
    long_term_embedding = user_embeddings.get("long_term")
    session_embedding = user_embeddings.get("session") if request.use_session_context else None

    # Fallback to database if not in cache
    if long_term_embedding is None or (request.use_session_context and session_embedding is None):
        logger.info(f"Cache miss for user {request.user_id}, querying database")
        from uuid import UUID

        import numpy as np

        from ...db.models import UserEmbedding

        try:
            # Convert user_id string to UUID for database query
            user_uuid = UUID(request.user_id)

            # Query database for user embeddings
            user_embedding_record = (
                db.query(UserEmbedding).filter(UserEmbedding.user_id == user_uuid).first()
            )

            if user_embedding_record:
                # Extract long-term embedding from database
                if long_term_embedding is None and user_embedding_record.long_term_embedding:
                    emb_data = user_embedding_record.long_term_embedding
                    if isinstance(emb_data, (list, tuple)):
                        long_term_embedding = np.array(emb_data, dtype=np.float32)
                    elif isinstance(emb_data, np.ndarray):
                        long_term_embedding = emb_data.astype(np.float32)

                    # Cache for future requests
                    cache.set_user_long_term_embedding(request.user_id, long_term_embedding)
                    logger.info(
                        f"Loaded long-term embedding from database for user {request.user_id}"
                    )

                # Extract session embedding from database if needed
                if (
                    request.use_session_context
                    and session_embedding is None
                    and user_embedding_record.session_embedding
                ):
                    sess_data = user_embedding_record.session_embedding
                    if isinstance(sess_data, (list, tuple)):
                        session_embedding = np.array(sess_data, dtype=np.float32)
                    elif isinstance(sess_data, np.ndarray):
                        session_embedding = sess_data.astype(np.float32)

                    # Cache for future requests
                    cache.set_user_session_embedding(request.user_id, session_embedding)
                    logger.info(
                        f"Loaded session embedding from database for user {request.user_id}"
                    )
            else:
                logger.warning(
                    f"No user embedding record found in database for user {request.user_id}"
                )
        except ValueError as e:
            logger.error(f"Invalid user UUID format: {request.user_id}, error: {e}")
        except Exception as e:
            logger.error(f"Error loading embeddings from database: {e}", exc_info=True)

    has_long_term_profile = long_term_embedding is not None
    has_session_context = session_embedding is not None

    # Validate user has embeddings
    if not has_long_term_profile and not has_session_context:
        logger.warning(f"No embeddings found for user {request.user_id} in cache or database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no preference profile. Please complete onboarding first.",
        )

    # Step 2: Build query vector based on context
    query_vector = None
    blend_weights = {}

    if request.context == RecommendationContext.FEED:
        # General feed: blend long-term and session
        if has_long_term_profile and has_session_context:
            # Blend both
            query_vector = 0.6 * long_term_embedding + 0.4 * session_embedding
            blend_weights = {"long_term": 0.6, "session": 0.4}
        elif has_long_term_profile:
            query_vector = long_term_embedding
            blend_weights = {"long_term": 1.0}
        else:
            query_vector = session_embedding
            blend_weights = {"session": 1.0}

    elif request.context == RecommendationContext.SEARCH:
        # Search-based: blend query + user embeddings
        if not request.search_query:
            raise SearchError(message="search_query required for context=search", status_code=400)

        try:
            query_embedding = text_encoder.encode_query(request.search_query)
        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise SearchError(
                message="Failed to encode search query",
                details={"query": request.search_query, "error": str(e)},
            )

        # Blend query with user profile
        if has_long_term_profile:
            query_vector = 0.7 * query_embedding + 0.3 * long_term_embedding
            blend_weights = {"query": 0.7, "long_term": 0.3}
        else:
            query_vector = query_embedding
            blend_weights = {"query": 1.0}

    elif request.context == RecommendationContext.SIMILAR:
        # Similar products: get product embedding + blend with user
        if not request.product_id:
            raise SearchError(message="product_id required for context=similar", status_code=400)

        # Get product embedding from cache or database
        product_embedding = _get_product_embedding(request.product_id, search_service, cache, db)

        if product_embedding is None:
            raise SearchError(
                message="Product not found",
                details={"product_id": request.product_id},
                status_code=404,
            )

        # Blend product with user profile
        if has_long_term_profile:
            query_vector = 0.8 * product_embedding + 0.2 * long_term_embedding
            blend_weights = {"product": 0.8, "long_term": 0.2}
        else:
            query_vector = product_embedding
            blend_weights = {"product": 1.0}

    elif request.context == RecommendationContext.CATEGORY:
        # Category-based: use long-term profile with category filter
        if not request.category_id:
            raise SearchError(message="category_id required for context=category", status_code=400)

        query_vector = long_term_embedding if has_long_term_profile else session_embedding
        blend_weights = {"long_term": 1.0} if has_long_term_profile else {"session": 1.0}

        # Add category filter
        if not request.filters:
            from ..models.common import FilterParams

            request.filters = FilterParams()
        if not request.filters.category_ids:
            request.filters.category_ids = []
        request.filters.category_ids.append(request.category_id)

    # Step 3: Build filters
    filters = None
    if request.filters:
        filters = ProductFilters(
            min_price=request.filters.min_price,
            max_price=request.filters.max_price,
            in_stock_only=request.filters.in_stock,
            merchant_ids=request.filters.merchant_ids,
            category_ids=request.filters.category_ids,
            brand_ids=request.filters.brand_ids,
        )

    # Step 4: Perform personalized search
    from ...ml.retrieval import FilteredSimilaritySearch, SimilaritySearch

    recommend_start = time.time()

    if filters:
        filtered_search = FilteredSimilaritySearch(
            index_manager=search_service.personalized_search.index_manager,
            db_session_factory=lambda: db,
        )

        ml_results = filtered_search.search_with_filters(
            query_vector=query_vector,
            filters=filters,
            k=request.limit * 2,  # Get more for better results after enrichment
            session=db,
        )
    else:
        similarity_search = SimilaritySearch(
            index_manager=search_service.personalized_search.index_manager
        )

        ml_results = similarity_search.search(query_vector=query_vector, k=request.limit * 2)

    recommendation_time_ms = (time.time() - recommend_start) * 1000

    # Step 5: Extract product IDs and scores
    product_ids = [r.product_id for r in ml_results.results]
    scores = {}

    for result in ml_results.results:
        scores[result.product_id] = {
            "similarity": result.similarity,
            "rank": result.rank,
            "final_score": result.metadata.get("final_score", result.similarity),
            "popularity_score": result.metadata.get("popularity_score"),
            "price_affinity_score": result.metadata.get("price_affinity_score"),
            "brand_match_score": result.metadata.get("brand_match_score"),
        }

    # Step 6: Enrich with metadata
    enriched_results = metadata_service.enrich_results(
        product_ids=product_ids, scores=scores, db=db
    )

    # Step 7: Apply pagination
    paginated_results = enriched_results[request.offset : request.offset + request.limit]

    # Step 8: Build response
    total_time_ms = (time.time() - start_time) * 1000

    response_data = {
        "results": paginated_results,
        "total": len(enriched_results),
        "offset": request.offset,
        "limit": request.limit,
        "page": (request.offset // request.limit) + 1 if request.limit > 0 else 1,
        "user_id": request.user_id,
        "context": request.context.value,
        "recommendation_time_ms": recommendation_time_ms,
        "total_time_ms": total_time_ms,
        "personalized": True,
        "cached": False,
        "filters_applied": filters is not None,
        "diversity_applied": request.enable_diversity,
        "has_long_term_profile": has_long_term_profile,
        "has_session_context": has_session_context,
        "blend_weights": blend_weights,
    }

    # Step 9: Cache response
    if settings.enable_cache:
        cache_service.set_recommend_results(cache_key, response_data, settings.cache_ttl_recommend)

    logger.info(
        f"Recommendation completed: {len(enriched_results)} results in {total_time_ms:.2f}ms",
        extra={"request_id": request_id},
    )

    return RecommendResponse(**response_data)


def _generate_cache_key(request: RecommendRequest) -> str:
    """
    Generate cache key for recommendation request.

    Args:
        request: Recommendation request

    Returns:
        Cache key string
    """
    # Create a deterministic string representation of the request
    key_parts = [
        f"user:{request.user_id}",
        f"context:{request.context.value}",
        f"offset:{request.offset}",
        f"limit:{request.limit}",
        f"session:{request.use_session_context}",
    ]

    # Add context-specific parameters
    if request.product_id:
        key_parts.append(f"product:{request.product_id}")
    if request.category_id:
        key_parts.append(f"category:{request.category_id}")
    if request.search_query:
        key_parts.append(f"query:{request.search_query.lower().strip()}")

    if request.filters:
        from ..routers.search import _hash_filters

        key_parts.append(f"filters:{_hash_filters(request.filters)}")

    key_string = "|".join(key_parts)

    # Hash to create shorter key
    key_hash = hashlib.md5(key_string.encode()).hexdigest()

    return f"recommend:{key_hash}"


def _get_cached_response(cache_key: str, cache: EmbeddingCache) -> Optional[Dict[str, Any]]:
    """Get cached recommendation response."""
    try:
        return cache.redis.get(cache_key)
    except Exception as e:
        logger.warning(f"Failed to get cached response: {e}")
        return None


def _cache_response(
    cache_key: str, response_data: Dict[str, Any], cache: EmbeddingCache, ttl: int
) -> bool:
    """Cache recommendation response."""
    try:
        # Convert Pydantic models to dicts for caching
        cacheable_data = response_data.copy()
        if "results" in cacheable_data:
            cacheable_data["results"] = [
                r.dict() if hasattr(r, "dict") else r for r in cacheable_data["results"]
            ]

        return cache.redis.set(cache_key, cacheable_data, ttl=ttl)
    except Exception as e:
        logger.warning(f"Failed to cache response: {e}")
        return False


def _get_product_embedding(
    product_id: str, search_service: SearchService, cache: EmbeddingCache, db: Session = None
) -> Optional[Any]:
    """
    Get product embedding from cache or database.

    Args:
        product_id: Product ID (UUID string)
        search_service: Search service
        cache: Embedding cache
        db: Database session (optional)

    Returns:
        Product embedding vector or None
    """
    from uuid import UUID

    import numpy as np

    # Try cache first
    cache_key = f"product_embedding:{product_id}"
    try:
        cached = cache.redis.get(cache_key)
        if cached is not None:
            logger.debug(f"Retrieved product embedding from cache: {product_id}")
            return cached
    except Exception as e:
        logger.warning(f"Failed to get cached product embedding: {e}")

    # Get from database if db session provided
    if db is not None:
        try:
            from sqlalchemy import select

            from ...db.models import Product

            # Convert product_id to UUID
            try:
                product_uuid = UUID(product_id)
            except ValueError:
                logger.error(f"Invalid product UUID: {product_id}")
                return None

            # Query product
            product = db.execute(
                select(Product).where(Product.id == product_uuid)
            ).scalar_one_or_none()

            if product is None:
                logger.warning(f"Product not found: {product_id}")
                return None

            # Get text embedding (default for similarity)
            if product.text_embedding is not None:
                if isinstance(product.text_embedding, (list, tuple)):
                    embedding = np.array(product.text_embedding, dtype=np.float32)
                else:
                    embedding = np.array(product.text_embedding, dtype=np.float32)

                # Cache for future use
                try:
                    cache.redis.set(cache_key, embedding, ttl=3600)  # Cache for 1 hour
                except Exception as e:
                    logger.warning(f"Failed to cache product embedding: {e}")

                logger.debug(f"Retrieved product embedding from database: {product_id}")
                return embedding

            logger.warning(f"Product has no text embedding: {product_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get product embedding from database: {e}")
            return None

    logger.warning(f"Cannot retrieve product embedding without database session: {product_id}")
    return None
