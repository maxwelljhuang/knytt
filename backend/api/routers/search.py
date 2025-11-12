"""
Search Endpoint
POST /search - Text-based product search with personalization.
"""

import logging
import hashlib
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..config import get_settings, APISettings
from ..dependencies import get_db, get_search_service, get_embedding_cache, get_request_id
from ..models.search import SearchRequest, SearchResponse, ProductResult
from ..services.text_encoder import get_text_encoder_service, TextEncoderService
from ..services.metadata_service import get_metadata_service, MetadataService
from ..services.cache_service import get_cache_service, CacheService
from ..errors import SearchError
from ...ml.search import SearchService, SearchRequest as MLSearchRequest, SearchMode
from ...ml.retrieval import ProductFilters, create_user_context
from ...ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
    text_encoder: TextEncoderService = Depends(get_text_encoder_service),
    metadata_service: MetadataService = Depends(get_metadata_service),
    cache: EmbeddingCache = Depends(get_embedding_cache),
    cache_service: CacheService = Depends(get_cache_service),
    settings: APISettings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
) -> SearchResponse:
    """
    Search for products using text query.

    Workflow:
    1. Check cache for results
    2. Encode query text to embedding
    3. Perform similarity search with FAISS
    4. Apply filters and ranking
    5. Enrich results with product metadata
    6. Cache results
    7. Return response

    Args:
        request: Search request with query and filters
        db: Database session
        search_service: Search service instance
        text_encoder: Text encoder service
        metadata_service: Metadata service
        cache: Embedding cache
        settings: API settings
        request_id: Request ID for tracing

    Returns:
        Search response with results and metadata
    """
    start_time = time.time()

    logger.info(
        f"Search request: query='{request.query}', user_id={request.user_id}",
        extra={"request_id": request_id},
    )

    # Track query for cache warming
    cache_service.track_query(request.query)
    if request.user_id:
        cache_service.track_user_activity(request.user_id)

    # Generate cache key
    cache_key = _generate_cache_key(request)

    # Check cache if enabled
    cached_response = None
    if settings.enable_cache:
        cached_response = cache_service.get_search_results(cache_key)

        if cached_response:
            logger.info(f"Cache HIT for query: '{request.query}'", extra={"request_id": request_id})
            cached_response["cached"] = True
            cached_response["total_time_ms"] = (time.time() - start_time) * 1000
            return SearchResponse(**cached_response)

    logger.debug(f"Cache MISS for query: '{request.query}'")

    # Step 1: Encode query text to embedding
    try:
        query_embedding = text_encoder.encode_query(request.query)
    except Exception as e:
        logger.error(f"Failed to encode query: {e}")
        raise SearchError(
            message="Failed to encode search query",
            details={"query": request.query, "error": str(e)},
        )

    # Step 2: Build filters
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

    # Step 3: Build user context (for personalization)
    user_context = None
    if request.user_id:
        # Get user embeddings from cache
        user_embeddings = cache.get_user_embeddings(request.user_id)
        long_term = user_embeddings.get("long_term")
        session_emb = user_embeddings.get("session")

        if long_term or session_emb:
            user_context = create_user_context(
                user_id=request.user_id,
                long_term_embedding=long_term,
                session_embedding=session_emb,
            )

    # Step 4: Perform search
    # We'll use the text search mode, but for MVP we'll treat it as a vector search
    # TODO: Implement proper text search in SearchService

    # For now, use the query embedding directly
    from ...ml.retrieval import SimilaritySearch, FilteredSimilaritySearch

    # Ensure FAISS index is loaded (lazy loading on first search request)
    index_manager = search_service.personalized_search.index_manager
    try:
        index_manager.ensure_index_loaded(session=db)
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        raise SearchError(
            message="Search service temporarily unavailable",
            details={"error": str(e)},
        )

    if filters:
        filtered_search = FilteredSimilaritySearch(
            index_manager=search_service.personalized_search.index_manager,
            db_session_factory=lambda: db,
        )

        ml_results = filtered_search.search_with_filters(
            query_vector=query_embedding,
            filters=filters,
            k=request.limit * 2,  # Get more for better results after enrichment
            session=db,
        )
    else:
        similarity_search = SimilaritySearch(
            index_manager=search_service.personalized_search.index_manager
        )

        ml_results = similarity_search.search(query_vector=query_embedding, k=request.limit * 2)

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
        "query": request.query,
        "user_id": request.user_id,
        "search_time_ms": ml_results.search_time_ms,
        "total_time_ms": total_time_ms,
        "personalized": user_context is not None,
        "cached": False,
        "filters_applied": filters is not None,
        "ranking_applied": request.use_ranking,
    }

    # Step 9: Cache response
    if settings.enable_cache:
        cache_service.set_search_results(cache_key, response_data, settings.cache_ttl_search)

    logger.info(
        f"Search completed: {len(enriched_results)} results in {total_time_ms:.2f}ms",
        extra={"request_id": request_id},
    )

    return SearchResponse(**response_data)


def _generate_cache_key(request: SearchRequest) -> str:
    """
    Generate cache key for search request.

    Args:
        request: Search request

    Returns:
        Cache key string
    """
    # Create a deterministic string representation of the request
    key_parts = [
        f"query:{request.query.lower().strip()}",
        f"user:{request.user_id or 'anon'}",
        f"offset:{request.offset}",
        f"limit:{request.limit}",
    ]

    if request.filters:
        key_parts.append(f"filters:{_hash_filters(request.filters)}")

    key_string = "|".join(key_parts)

    # Hash to create shorter key
    key_hash = hashlib.md5(key_string.encode()).hexdigest()

    return f"search:{key_hash}"


def _hash_filters(filters) -> str:
    """Hash filter parameters."""
    filter_parts = []

    if filters.min_price is not None:
        filter_parts.append(f"min_price:{filters.min_price}")
    if filters.max_price is not None:
        filter_parts.append(f"max_price:{filters.max_price}")
    if filters.in_stock is not None:
        filter_parts.append(f"in_stock:{filters.in_stock}")
    if filters.merchant_ids:
        filter_parts.append(f"merchants:{','.join(map(str, sorted(filters.merchant_ids)))}")
    if filters.category_ids:
        filter_parts.append(f"categories:{','.join(map(str, sorted(filters.category_ids)))}")
    if filters.brand_ids:
        filter_parts.append(f"brands:{','.join(map(str, sorted(filters.brand_ids)))}")

    return "|".join(filter_parts)


def _get_cached_response(cache_key: str, cache: EmbeddingCache) -> Dict[str, Any]:
    """Get cached search response."""
    try:
        return cache.redis.get(cache_key)
    except Exception as e:
        logger.warning(f"Failed to get cached response: {e}")
        return None


def _cache_response(
    cache_key: str, response_data: Dict[str, Any], cache: EmbeddingCache, ttl: int
) -> bool:
    """Cache search response."""
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
