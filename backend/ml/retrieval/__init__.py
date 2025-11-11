"""
Retrieval & Search Module
FAISS-based vector similarity search with filtering and ranking.
"""

from .index_builder import FAISSIndexBuilder
from .index_manager import FAISSIndexManager, get_index_manager
from .similarity_search import SimilaritySearch, SearchResult, SearchResults
from .filters import (
    ProductFilter,
    ProductFilters,
    FilteredSearcher,
    FilterOperator,
    create_price_filter,
    create_merchant_filter,
    create_category_filter,
    combine_filters,
)
from .filtered_search import FilteredSimilaritySearch
from .ranking import (
    RankingConfig,
    PopularityScorer,
    PriceAffinityScorer,
    BrandMatchScorer,
    HeuristicRanker,
)
from .personalized_search import PersonalizedSearch, UserContext, create_user_context

__all__ = [
    "FAISSIndexBuilder",
    "FAISSIndexManager",
    "get_index_manager",
    "SimilaritySearch",
    "SearchResult",
    "SearchResults",
    "ProductFilter",
    "ProductFilters",
    "FilteredSearcher",
    "FilterOperator",
    "FilteredSimilaritySearch",
    "create_price_filter",
    "create_merchant_filter",
    "create_category_filter",
    "combine_filters",
    "RankingConfig",
    "PopularityScorer",
    "PriceAffinityScorer",
    "BrandMatchScorer",
    "HeuristicRanker",
    "PersonalizedSearch",
    "UserContext",
    "create_user_context",
]
