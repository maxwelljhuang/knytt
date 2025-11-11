"""
Search Service
Unified search API integrating all ML components.
"""

import logging
import time
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from ..config import get_ml_config, MLConfig
from ..retrieval import (
    PersonalizedSearch,
    UserContext,
    ProductFilters,
    SearchResults,
    RankingConfig,
)
from ..caching import EmbeddingCache
from ..feedback import FeedbackHandler, InteractionType

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search modes."""

    PERSONALIZED_FEED = "personalized_feed"  # User-based recommendations
    TEXT_SEARCH = "text_search"  # Text query search
    SIMILAR_ITEMS = "similar_items"  # Similar product search
    CATEGORY_BROWSE = "category_browse"  # Category exploration
    TRENDING = "trending"  # Trending/popular items


@dataclass
class SearchRequest:
    """
    Unified search request.

    Supports multiple search modes with a single interface.
    """

    # User context
    user_id: Optional[int] = None
    user_context: Optional[UserContext] = None

    # Search mode and query
    mode: SearchMode = SearchMode.PERSONALIZED_FEED
    query: Optional[str] = None  # For text search
    product_id: Optional[int] = None  # For similar items

    # Filters
    filters: Optional[ProductFilters] = None

    # Pagination
    offset: int = 0
    limit: int = 50

    # Personalization settings
    use_ranking: bool = True
    ranking_config: Optional[RankingConfig] = None
    context: str = "feed"  # 'feed', 'search', 'similar'

    # Diversity settings
    enable_diversity: bool = True
    diversity_weight: float = 0.15

    # Performance settings
    enable_caching: bool = True

    # Metadata
    session_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class SearchResponse:
    """
    Search response with results and metadata.
    """

    results: SearchResults
    mode: SearchMode
    total_results: int
    offset: int
    limit: int

    # Performance metrics
    search_time_ms: float
    total_time_ms: float

    # Metadata
    user_id: Optional[int] = None
    query: Optional[str] = None
    filters_applied: bool = False
    ranking_applied: bool = False
    diversity_applied: bool = False
    cache_hit_rate: Optional[float] = None

    # Debugging info
    debug_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "results": self.results.to_dict(),
            "mode": self.mode.value,
            "total_results": self.total_results,
            "offset": self.offset,
            "limit": self.limit,
            "search_time_ms": self.search_time_ms,
            "total_time_ms": self.total_time_ms,
            "user_id": self.user_id,
            "query": self.query,
            "filters_applied": self.filters_applied,
            "ranking_applied": self.ranking_applied,
            "diversity_applied": self.diversity_applied,
            "cache_hit_rate": self.cache_hit_rate,
        }


class SearchService:
    """
    Unified search service.

    Orchestrates all ML components to provide a complete search experience:
    - Personalized recommendations
    - Text search
    - Similar items
    - Filtering
    - Ranking
    - Caching
    - Feedback
    """

    def __init__(self, config: Optional[MLConfig] = None, db_session_factory=None):
        """
        Initialize search service.

        Args:
            config: ML configuration
            db_session_factory: Database session factory
        """
        self.config = config or get_ml_config()
        self.db_session_factory = db_session_factory

        # Initialize components
        self.personalized_search = PersonalizedSearch(
            config=self.config, db_session_factory=db_session_factory
        )
        self.cache = EmbeddingCache(self.config)
        self.feedback_handler = FeedbackHandler(
            config=self.config, db_session_factory=db_session_factory
        )

        logger.info("Search service initialized")

    def search(self, request: SearchRequest, session=None) -> SearchResponse:
        """
        Execute search request.

        Args:
            request: Search request
            session: Database session (optional)

        Returns:
            Search response
        """
        start_time = time.time()

        logger.info(
            f"Search request: mode={request.mode.value}, "
            f"user={request.user_id}, query='{request.query}'"
        )

        # Route to appropriate search handler
        if request.mode == SearchMode.PERSONALIZED_FEED:
            results = self._search_personalized_feed(request, session)
        elif request.mode == SearchMode.TEXT_SEARCH:
            results = self._search_text(request, session)
        elif request.mode == SearchMode.SIMILAR_ITEMS:
            results = self._search_similar_items(request, session)
        elif request.mode == SearchMode.CATEGORY_BROWSE:
            results = self._search_category(request, session)
        elif request.mode == SearchMode.TRENDING:
            results = self._search_trending(request, session)
        else:
            raise ValueError(f"Unsupported search mode: {request.mode}")

        # Apply diversity if enabled
        if request.enable_diversity and len(results.results) > 0:
            results = self._apply_diversity(results, request.diversity_weight)
            diversity_applied = True
        else:
            diversity_applied = False

        # Apply pagination
        paginated_results = self._paginate_results(
            results, offset=request.offset, limit=request.limit
        )

        # Build response
        total_time_ms = (time.time() - start_time) * 1000

        response = SearchResponse(
            results=paginated_results,
            mode=request.mode,
            total_results=len(results.results),
            offset=request.offset,
            limit=request.limit,
            search_time_ms=results.search_time_ms,
            total_time_ms=total_time_ms,
            user_id=request.user_id,
            query=request.query,
            filters_applied=request.filters is not None,
            ranking_applied=request.use_ranking,
            diversity_applied=diversity_applied,
        )

        logger.info(f"Search completed: {response.total_results} results in {total_time_ms:.2f}ms")

        return response

    def _search_personalized_feed(self, request: SearchRequest, session) -> SearchResults:
        """
        Get personalized feed recommendations.

        Args:
            request: Search request
            session: Database session

        Returns:
            Search results
        """
        # Get or create user context
        user_context = request.user_context
        if user_context is None and request.user_id is not None:
            user_context = self._build_user_context(request.user_id)

        if user_context is None or user_context.is_anonymous:
            # Anonymous user - return trending/popular
            logger.info("Anonymous user, returning trending items")
            return self.personalized_search.recommend_for_anonymous(
                k=request.limit * 2,  # Get more for pagination
                filters=request.filters,
                session=session,
            )

        # Personalized recommendations
        return self.personalized_search.recommend_for_user(
            user_context=user_context,
            k=request.limit * 2,
            filters=request.filters,
            context=request.context,
            use_ranking=request.use_ranking,
            ranking_config=request.ranking_config,
            session=session,
        )

    def _search_text(self, request: SearchRequest, session) -> SearchResults:
        """
        Text search with personalization.

        Args:
            request: Search request
            session: Database session

        Returns:
            Search results
        """
        if not request.query:
            raise ValueError("Text search requires a query")

        # Get user context
        user_context = request.user_context
        if user_context is None and request.user_id is not None:
            user_context = self._build_user_context(request.user_id)

        if user_context is None:
            # Create anonymous context
            from ..retrieval import create_user_context

            user_context = create_user_context()

        # Execute search
        return self.personalized_search.search_for_user(
            query_text=request.query,
            user_context=user_context,
            k=request.limit * 2,
            filters=request.filters,
            use_ranking=request.use_ranking,
            session=session,
        )

    def _search_similar_items(self, request: SearchRequest, session) -> SearchResults:
        """
        Find similar items with personalization.

        Args:
            request: Search request
            session: Database session

        Returns:
            Search results
        """
        if request.product_id is None:
            raise ValueError("Similar items search requires product_id")

        # Get user context
        user_context = request.user_context
        if user_context is None and request.user_id is not None:
            user_context = self._build_user_context(request.user_id)

        if user_context is None:
            # Create anonymous context
            from ..retrieval import create_user_context

            user_context = create_user_context()

        # Find similar items
        return self.personalized_search.find_similar_for_user(
            product_id=request.product_id,
            user_context=user_context,
            k=request.limit * 2,
            filters=request.filters,
            blend_ratio=0.9,  # 90% product similarity, 10% user preference
            use_ranking=request.use_ranking,
            session=session,
        )

    def _search_category(self, request: SearchRequest, session) -> SearchResults:
        """
        Browse category with personalization.

        Args:
            request: Search request
            session: Database session

        Returns:
            Search results
        """
        # Category browse is like personalized feed but with category filter
        return self._search_personalized_feed(request, session)

    def _search_trending(self, request: SearchRequest, session) -> SearchResults:
        """
        Get trending/popular items.

        Args:
            request: Search request
            session: Database session

        Returns:
            Search results
        """
        # Get hot products
        hot_products = self.cache.get_hot_products(limit=request.limit * 2)

        if not hot_products:
            logger.warning("No hot products found, returning empty results")
            return SearchResults(
                results=[],
                query_vector_shape=(0,),
                k=request.limit,
                total_found=0,
                search_time_ms=0.0,
            )

        # TODO: Convert hot products to SearchResults with proper ranking
        # For now, return empty results
        logger.info(f"Found {len(hot_products)} hot products")

        return SearchResults(
            results=[], query_vector_shape=(0,), k=request.limit, total_found=0, search_time_ms=0.0
        )

    def _build_user_context(self, user_id: int) -> Optional[UserContext]:
        """
        Build user context from cache/database.

        Args:
            user_id: User ID

        Returns:
            UserContext or None if not available
        """
        # Get embeddings from cache
        embeddings = self.cache.get_user_embeddings(user_id)

        long_term = embeddings.get("long_term")
        session = embeddings.get("session")

        if long_term is None and session is None:
            # No embeddings available
            logger.debug(f"No embeddings found for user {user_id}")
            return None

        # Create user context
        from ..retrieval import create_user_context

        return create_user_context(
            user_id=user_id, long_term_embedding=long_term, session_embedding=session
        )

    def _apply_diversity(self, results: SearchResults, diversity_weight: float) -> SearchResults:
        """
        Apply diversity to search results (MMR-style).

        Maximal Marginal Relevance: balance relevance and diversity.

        Args:
            results: Search results
            diversity_weight: Weight for diversity (0-1)

        Returns:
            Diversified search results
        """
        if len(results.results) <= 1:
            return results

        # Simple diversity: ensure no duplicate products
        seen_products = set()
        unique_results = []

        for result in results.results:
            if result.product_id not in seen_products:
                seen_products.add(result.product_id)
                unique_results.append(result)

        # Update results
        results.results = unique_results
        results.total_found = len(unique_results)

        # Re-rank
        for i, result in enumerate(results.results):
            result.rank = i

        logger.debug(f"Applied diversity: {len(unique_results)} unique results")

        return results

    def _paginate_results(self, results: SearchResults, offset: int, limit: int) -> SearchResults:
        """
        Apply pagination to results.

        Args:
            results: Search results
            offset: Starting index
            limit: Number of results to return

        Returns:
            Paginated search results
        """
        if offset >= len(results.results):
            # Offset beyond results
            results.results = []
            results.total_found = 0
            return results

        # Slice results
        paginated = results.results[offset : offset + limit]

        # Update ranks
        for i, result in enumerate(paginated):
            result.rank = i

        # Create new SearchResults
        return SearchResults(
            results=paginated,
            query_vector_shape=results.query_vector_shape,
            k=limit,
            total_found=len(paginated),
            search_time_ms=results.search_time_ms,
        )

    def record_interaction(
        self,
        user_id: int,
        product_id: int,
        interaction_type: InteractionType,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record user interaction (for feedback loop).

        Args:
            user_id: User ID
            product_id: Product ID
            interaction_type: Type of interaction
            context: Context where interaction occurred

        Returns:
            Feedback processing result
        """
        from ..feedback import InteractionEvent

        event = InteractionEvent(
            user_id=user_id,
            product_id=product_id,
            interaction_type=interaction_type,
            context=context,
        )

        return self.feedback_handler.process_event(event)

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Dict with service stats
        """
        from ..retrieval import get_index_manager

        index_manager = get_index_manager()
        cache_stats = self.cache.get_cache_stats()
        index_stats = index_manager.get_stats()

        return {
            "service": "SearchService",
            "version": self.config.model_version,
            "index": index_stats,
            "cache": cache_stats,
        }
