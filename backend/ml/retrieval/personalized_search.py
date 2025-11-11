"""
Personalized Search
Integrates user embeddings with similarity search for personalized recommendations.
"""

import logging
import numpy as np
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

from ..config import get_ml_config, MLConfig
from ..user_modeling.blending import UserEmbeddingBlender
from ..user_modeling.session import SessionManager
from .similarity_search import SimilaritySearch, SearchResults
from .filtered_search import FilteredSimilaritySearch
from .filters import ProductFilters
from .ranking import HeuristicRanker, RankingConfig
from .index_manager import get_index_manager

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """
    User context for personalized search.

    Contains user embeddings and metadata needed for personalization.
    """

    user_id: Optional[int] = None
    long_term_embedding: Optional[np.ndarray] = None
    session_embedding: Optional[np.ndarray] = None
    is_anonymous: bool = True

    # User profile for ranking
    price_profile: Optional[Dict[str, float]] = None
    brand_preferences: Optional[Dict[int, float]] = None


class PersonalizedSearch:
    """
    Personalized product search using user embeddings.

    Combines:
    - User embeddings (long-term + session)
    - Filtered search (business logic)
    - Heuristic ranking (multi-signal)

    Supports multiple search contexts:
    - Feed recommendations (balance long-term + session)
    - Search results (emphasize session intent)
    - Similar items (emphasize product similarity)
    """

    def __init__(self, config: Optional[MLConfig] = None, db_session_factory=None):
        """
        Initialize personalized search.

        Args:
            config: ML configuration
            db_session_factory: Database session factory
        """
        self.config = config or get_ml_config()
        self.db_session_factory = db_session_factory

        # Initialize components
        self.index_manager = get_index_manager()
        self.similarity_search = SimilaritySearch(
            config=self.config, index_manager=self.index_manager
        )
        self.filtered_search = FilteredSimilaritySearch(
            config=self.config,
            index_manager=self.index_manager,
            db_session_factory=db_session_factory,
        )
        self.blender = UserEmbeddingBlender()
        self.session_manager = SessionManager()

        logger.info("Personalized search initialized")

    def recommend_for_user(
        self,
        user_context: UserContext,
        k: int = 50,
        filters: Optional[ProductFilters] = None,
        context: str = "feed",
        use_ranking: bool = True,
        ranking_config: Optional[RankingConfig] = None,
        session=None,
    ) -> SearchResults:
        """
        Generate personalized recommendations for a user.

        Args:
            user_context: User context with embeddings
            k: Number of recommendations to return
            filters: Optional product filters
            context: Search context ('feed', 'search', 'similar')
            use_ranking: Whether to apply heuristic ranking
            ranking_config: Optional custom ranking configuration
            session: Database session

        Returns:
            SearchResults with personalized recommendations
        """
        # Get query vector based on user embeddings
        query_vector = self._get_user_query_vector(user_context, context)

        if query_vector is None:
            # No user embeddings available, return empty results
            logger.warning(f"No query vector available for user {user_context.user_id}")
            return SearchResults(
                results=[], query_vector_shape=(0,), k=k, total_found=0, search_time_ms=0.0
            )

        # Perform search (with or without filters)
        if filters is not None:
            results = self.filtered_search.search_with_filters(
                query_vector=query_vector,
                filters=filters,
                k=k * 2 if use_ranking else k,  # Get more for ranking
                session=session,
            )
        else:
            results = self.similarity_search.search(
                query_vector=query_vector, k=k * 2 if use_ranking else k
            )

        # Apply heuristic ranking if enabled
        if use_ranking and len(results.results) > 0:
            results = self._apply_ranking(
                results=results,
                user_context=user_context,
                ranking_config=ranking_config,
                session=session,
            )

            # Trim to requested k
            results.results = results.results[:k]
            results.total_found = len(results.results)

        logger.info(
            f"Generated {results.total_found} recommendations for "
            f"{'user ' + str(user_context.user_id) if not user_context.is_anonymous else 'anonymous user'} "
            f"in context '{context}'"
        )

        return results

    def search_for_user(
        self,
        query_text: str,
        user_context: UserContext,
        k: int = 50,
        filters: Optional[ProductFilters] = None,
        use_ranking: bool = True,
        session=None,
    ) -> SearchResults:
        """
        Text search with user personalization.

        Args:
            query_text: Search query text
            user_context: User context
            k: Number of results
            filters: Optional filters
            use_ranking: Whether to apply ranking
            session: Database session

        Returns:
            SearchResults
        """
        # TODO: Encode query text to embedding
        # For now, use user embedding as fallback
        logger.warning("Text search not yet implemented, falling back to user recommendations")

        return self.recommend_for_user(
            user_context=user_context,
            k=k,
            filters=filters,
            context="search",
            use_ranking=use_ranking,
            session=session,
        )

    def find_similar_for_user(
        self,
        product_id: int,
        user_context: UserContext,
        k: int = 50,
        filters: Optional[ProductFilters] = None,
        blend_ratio: float = 0.9,
        use_ranking: bool = True,
        session=None,
    ) -> SearchResults:
        """
        Find similar items with user personalization.

        Args:
            product_id: Product to find similar items for
            user_context: User context
            k: Number of results
            filters: Optional filters
            blend_ratio: How much to emphasize product (vs user). 0.9 = 90% product, 10% user
            use_ranking: Whether to apply ranking
            session: Database session

        Returns:
            SearchResults
        """
        # Get product embedding
        product_vector = self.similarity_search.get_product_vector(product_id)

        if product_vector is None:
            raise ValueError(f"Product {product_id} not found in index")

        # Get user query vector
        user_vector = self._get_user_query_vector(user_context, context="similar")

        # Blend product and user vectors
        if user_vector is not None and not user_context.is_anonymous:
            query_vector = blend_ratio * product_vector + (1 - blend_ratio) * user_vector
            # Normalize
            query_vector = query_vector / np.linalg.norm(query_vector)
        else:
            # No user vector, just use product
            query_vector = product_vector

        # Search
        if filters is not None:
            results = self.filtered_search.search_with_filters(
                query_vector=query_vector,
                filters=filters,
                k=k * 2 if use_ranking else k,
                session=session,
            )
        else:
            results = self.similarity_search.search(
                query_vector=query_vector, k=k * 2 if use_ranking else k
            )

        # Remove the query product from results
        results.results = [r for r in results.results if r.product_id != product_id]

        # Apply ranking
        if use_ranking and len(results.results) > 0:
            results = self._apply_ranking(
                results=results, user_context=user_context, session=session
            )

        # Trim to k and re-rank
        results.results = results.results[:k]
        results.total_found = len(results.results)
        for i, result in enumerate(results.results):
            result.rank = i

        return results

    def recommend_for_anonymous(
        self,
        k: int = 50,
        filters: Optional[ProductFilters] = None,
        strategy: str = "popular",
        session=None,
    ) -> SearchResults:
        """
        Generate recommendations for anonymous users.

        Args:
            k: Number of recommendations
            filters: Optional filters
            strategy: Recommendation strategy ('popular', 'random', 'trending')
            session: Database session

        Returns:
            SearchResults
        """
        logger.info(f"Generating {k} recommendations for anonymous user (strategy: {strategy})")

        # For now, return empty results
        # In production, would implement cold-start strategies:
        # - Popular items
        # - Trending items
        # - Random exploration

        # TODO: Implement anonymous user strategies

        return SearchResults(
            results=[], query_vector_shape=(0,), k=k, total_found=0, search_time_ms=0.0
        )

    def _get_user_query_vector(
        self, user_context: UserContext, context: str
    ) -> Optional[np.ndarray]:
        """
        Get query vector for user based on context.

        Args:
            user_context: User context with embeddings
            context: Search context ('feed', 'search', 'similar')

        Returns:
            Query vector or None if not available
        """
        if user_context.is_anonymous:
            return None

        long_term = user_context.long_term_embedding
        session_emb = user_context.session_embedding

        if long_term is None and session_emb is None:
            return None

        # Blend based on context
        blend_result = self.blender.blend(
            long_term_embedding=long_term, session_embedding=session_emb, context=context
        )

        return blend_result["blended_embedding"]

    def _apply_ranking(
        self,
        results: SearchResults,
        user_context: UserContext,
        ranking_config: Optional[RankingConfig] = None,
        session=None,
    ) -> SearchResults:
        """
        Apply heuristic ranking to search results.

        Args:
            results: Search results to rank
            user_context: User context for personalization
            ranking_config: Optional custom ranking config
            session: Database session

        Returns:
            Re-ranked SearchResults
        """
        ranker = HeuristicRanker(config=ranking_config)

        # Get product IDs
        product_ids = results.get_product_ids()

        # Fetch product data for ranking signals
        # TODO: Implement actual database queries
        # For now, use mock data
        popularity_scores = self._get_popularity_scores(product_ids, session)
        price_affinity_scores = self._get_price_affinity_scores(product_ids, user_context, session)
        brand_match_scores = self._get_brand_match_scores(product_ids, user_context, session)

        # Apply ranking
        ranked_results = ranker.rank_results(
            search_results=results,
            popularity_scores=popularity_scores,
            price_affinity_scores=price_affinity_scores,
            brand_match_scores=brand_match_scores,
        )

        return ranked_results

    def _get_popularity_scores(self, product_ids: List[int], session) -> Dict[int, float]:
        """
        Get popularity scores for products.

        Args:
            product_ids: List of product IDs
            session: Database session

        Returns:
            Dict mapping product_id -> popularity score
        """
        # TODO: Query database for actual engagement metrics
        # For now, return neutral scores
        return {pid: 0.5 for pid in product_ids}

    def _get_price_affinity_scores(
        self, product_ids: List[int], user_context: UserContext, session
    ) -> Dict[int, float]:
        """
        Get price affinity scores for products.

        Args:
            product_ids: List of product IDs
            user_context: User context with price profile
            session: Database session

        Returns:
            Dict mapping product_id -> price affinity score
        """
        # TODO: Query database for product prices and user price profile
        # For now, return neutral scores
        return {pid: 0.5 for pid in product_ids}

    def _get_brand_match_scores(
        self, product_ids: List[int], user_context: UserContext, session
    ) -> Dict[int, float]:
        """
        Get brand match scores for products.

        Args:
            product_ids: List of product IDs
            user_context: User context with brand preferences
            session: Database session

        Returns:
            Dict mapping product_id -> brand match score
        """
        # TODO: Query database for product brands and user brand preferences
        # For now, return neutral scores
        return {pid: 0.5 for pid in product_ids}


def create_user_context(
    user_id: Optional[int] = None,
    long_term_embedding: Optional[np.ndarray] = None,
    session_embedding: Optional[np.ndarray] = None,
    price_profile: Optional[Dict[str, float]] = None,
    brand_preferences: Optional[Dict[int, float]] = None,
) -> UserContext:
    """
    Convenience function to create UserContext.

    Args:
        user_id: User ID (None for anonymous)
        long_term_embedding: User's long-term embedding
        session_embedding: User's session embedding
        price_profile: User's price profile
        brand_preferences: User's brand preferences

    Returns:
        UserContext object
    """
    is_anonymous = user_id is None

    return UserContext(
        user_id=user_id,
        long_term_embedding=long_term_embedding,
        session_embedding=session_embedding,
        is_anonymous=is_anonymous,
        price_profile=price_profile,
        brand_preferences=brand_preferences,
    )
