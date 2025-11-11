"""
Filtered Similarity Search
Two-stage search: PostgreSQL filtering → FAISS similarity search
"""

import logging
import numpy as np
from typing import List, Optional, Set, Dict
import time

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from ..config import get_ml_config, MLConfig
from .similarity_search import SimilaritySearch, SearchResults, SearchResult
from .index_manager import FAISSIndexManager, get_index_manager
from .filters import ProductFilters, FilteredSearcher

logger = logging.getLogger(__name__)


class FilteredSimilaritySearchError(Exception):
    """Exception raised for filtered search errors."""

    pass


class FilteredSimilaritySearch:
    """
    Performs similarity search with pre-filtering.

    Two search strategies:
    1. Subset index: Build temporary FAISS index from filtered embeddings
       - Best when filters are very restrictive (small result set)
       - Requires DB query to get embeddings

    2. Post-filter: Search full FAISS index, then filter results
       - Best when filters are not very restrictive (large result set)
       - More efficient for light filtering
    """

    def __init__(
        self,
        config: Optional[MLConfig] = None,
        index_manager: Optional[FAISSIndexManager] = None,
        db_session_factory=None,
    ):
        """
        Initialize filtered similarity search.

        Args:
            config: ML configuration
            index_manager: FAISS index manager
            db_session_factory: Factory function to create DB sessions
        """
        self.config = config or get_ml_config()
        self.index_manager = index_manager or get_index_manager()
        self.similarity_search = SimilaritySearch(
            config=self.config, index_manager=self.index_manager
        )
        self.filtered_searcher = FilteredSearcher(db_session_factory)
        self.db_session_factory = db_session_factory

        # Strategy selection threshold
        # If filtered products < this %, use subset index strategy
        self.subset_threshold_ratio = 0.1  # 10%

        logger.info("Filtered similarity search initialized")

    def search_with_filters(
        self,
        query_vector: np.ndarray,
        filters: ProductFilters,
        k: int = 50,
        min_similarity: Optional[float] = None,
        strategy: Optional[str] = None,
        session=None,
    ) -> SearchResults:
        """
        Search with filters applied.

        Args:
            query_vector: Query embedding vector
            filters: ProductFilters object
            k: Number of results to return
            min_similarity: Optional minimum similarity threshold
            strategy: Force strategy ('subset' or 'postfilter', or None for auto)
            session: Database session (created if not provided)

        Returns:
            SearchResults object with filtered results

        Raises:
            FilteredSimilaritySearchError: If search fails
        """
        start_time = time.time()

        # Get or create session
        session_created = False
        if session is None:
            if self.db_session_factory is None:
                raise FilteredSimilaritySearchError(
                    "No database session provided and no session factory configured"
                )
            session = self.db_session_factory()
            session_created = True

        try:
            # Get total number of products in index
            total_products = self.index_manager.get_index().ntotal

            # Get filtered product IDs from database
            filtered_product_ids = self.filtered_searcher.get_filtered_product_ids(
                session=session, filters=filters
            )

            if len(filtered_product_ids) == 0:
                logger.warning("No products match the specified filters")
                return SearchResults(
                    results=[],
                    query_vector_shape=query_vector.shape,
                    k=k,
                    total_found=0,
                    search_time_ms=(time.time() - start_time) * 1000,
                )

            # Decide on strategy
            filter_ratio = len(filtered_product_ids) / total_products
            use_subset = filter_ratio < self.subset_threshold_ratio

            if strategy == "subset":
                use_subset = True
            elif strategy == "postfilter":
                use_subset = False

            logger.info(
                f"Filtered to {len(filtered_product_ids)} products "
                f"({filter_ratio*100:.1f}% of total), "
                f"using {'subset' if use_subset else 'postfilter'} strategy"
            )

            # Execute search with chosen strategy
            if use_subset:
                results = self._search_subset_strategy(
                    query_vector=query_vector,
                    filtered_product_ids=filtered_product_ids,
                    filters=filters,
                    k=k,
                    min_similarity=min_similarity,
                    session=session,
                )
            else:
                results = self._search_postfilter_strategy(
                    query_vector=query_vector,
                    filtered_product_ids=set(filtered_product_ids),
                    k=k,
                    min_similarity=min_similarity,
                )

            # Update search time
            results.search_time_ms = (time.time() - start_time) * 1000

            return results

        finally:
            if session_created:
                session.close()

    def _search_subset_strategy(
        self,
        query_vector: np.ndarray,
        filtered_product_ids: List[int],
        filters: ProductFilters,
        k: int,
        min_similarity: Optional[float],
        session,
    ) -> SearchResults:
        """
        Search using subset index strategy.

        Build temporary FAISS index from filtered embeddings.
        """
        logger.debug("Using subset index strategy")

        # Get embeddings for filtered products
        embeddings, product_ids = self.filtered_searcher.get_filtered_embeddings(
            session=session, filters=filters
        )

        if len(embeddings) == 0:
            return SearchResults(
                results=[],
                query_vector_shape=query_vector.shape,
                k=k,
                total_found=0,
                search_time_ms=0.0,
            )

        # Build temporary index
        subset_index, id_mapping = self.filtered_searcher.build_subset_index(
            embeddings=embeddings, product_ids=product_ids
        )

        # Prepare query vector
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = query_vector.astype(np.float32)

        # Normalize if configured
        if self.config.embedding.normalize_embeddings:
            norm = np.linalg.norm(query_vector)
            if norm > 1e-8:
                query_vector = query_vector / norm

        # Search subset index
        search_k = min(k, subset_index.ntotal)
        distances, indices = subset_index.search(query_vector, search_k)

        # Format results
        results = []
        for rank, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue

            product_id = id_mapping.get(int(idx))
            if product_id is None:
                continue

            # Convert distance to similarity
            similarity = self.similarity_search._distance_to_similarity(float(distance))

            if min_similarity is not None and similarity < min_similarity:
                continue

            results.append(
                SearchResult(
                    product_id=product_id,
                    distance=float(distance),
                    similarity=similarity,
                    rank=rank,
                )
            )

        return SearchResults(
            results=results,
            query_vector_shape=query_vector.shape,
            k=k,
            total_found=len(results),
            search_time_ms=0.0,  # Will be updated by caller
        )

    def _search_postfilter_strategy(
        self,
        query_vector: np.ndarray,
        filtered_product_ids: Set[int],
        k: int,
        min_similarity: Optional[float],
    ) -> SearchResults:
        """
        Search using post-filter strategy.

        Search full index, then filter results.
        """
        logger.debug("Using post-filter strategy")

        # Search with larger k to account for filtering
        # Heuristic: request 5x more results than needed
        search_k = min(k * 5, self.index_manager.get_index().ntotal)

        # Perform search on full index
        results = self.similarity_search.search(
            query_vector=query_vector, k=search_k, min_similarity=min_similarity
        )

        # Filter results to only allowed product IDs
        filtered_results = [r for r in results.results if r.product_id in filtered_product_ids][
            :k
        ]  # Take top k after filtering

        # Re-rank results
        for i, result in enumerate(filtered_results):
            result.rank = i

        return SearchResults(
            results=filtered_results,
            query_vector_shape=query_vector.shape,
            k=k,
            total_found=len(filtered_results),
            search_time_ms=0.0,  # Will be updated by caller
        )

    def search_similar_with_filters(
        self,
        product_id: int,
        filters: ProductFilters,
        k: int = 50,
        exclude_self: bool = True,
        min_similarity: Optional[float] = None,
        session=None,
    ) -> SearchResults:
        """
        Find similar products with filters applied.

        Args:
            product_id: Product ID to find similar items for
            filters: ProductFilters object
            k: Number of results to return
            exclude_self: Whether to exclude the query product
            min_similarity: Optional minimum similarity threshold
            session: Database session

        Returns:
            SearchResults object
        """
        # Get vector for this product
        vector = self.similarity_search.get_product_vector(product_id)

        if vector is None:
            raise FilteredSimilaritySearchError(f"Product ID {product_id} not found in index")

        # Search with filters
        results = self.search_with_filters(
            query_vector=vector,
            filters=filters,
            k=k + 1 if exclude_self else k,
            min_similarity=min_similarity,
            session=session,
        )

        # Filter out self if needed
        if exclude_self:
            results.results = [r for r in results.results if r.product_id != product_id][:k]
            results.total_found = len(results.results)

            # Re-rank
            for i, result in enumerate(results.results):
                result.rank = i

        return results

    def set_strategy_threshold(self, ratio: float):
        """
        Set threshold for subset vs postfilter strategy selection.

        Args:
            ratio: Ratio of filtered/total products below which to use subset strategy
                   (e.g., 0.1 = use subset if <10% of products remain after filtering)
        """
        if not 0 < ratio < 1:
            raise ValueError("Strategy threshold must be between 0 and 1")

        self.subset_threshold_ratio = ratio
        logger.info(f"Strategy threshold set to {ratio*100:.0f}%")
