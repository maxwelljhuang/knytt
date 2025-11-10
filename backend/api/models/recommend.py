"""
Recommendation Models
Pydantic models for recommendation endpoint.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from .common import FilterParams
from .search import ProductResult


class RecommendationContext(str, Enum):
    """
    Recommendation context types.

    Determines how recommendations are generated and blended.
    """
    FEED = "feed"           # General personalized feed
    SEARCH = "search"       # Search-based recommendations
    SIMILAR = "similar"     # Similar to a specific product
    CATEGORY = "category"   # Category-based recommendations


class RecommendRequest(BaseModel):
    """
    Recommendation request model.

    Generates personalized product recommendations for a user.
    """

    # User context (required for personalization)
    user_id: str = Field(..., description="User ID (UUID) for personalized recommendations")

    # Recommendation context
    context: RecommendationContext = Field(
        default=RecommendationContext.FEED,
        description="Recommendation context (feed, search, similar, category)"
    )

    # Context-specific parameters
    product_id: Optional[int] = Field(
        None,
        description="Product ID for similar item recommendations (context=similar)"
    )
    category_id: Optional[int] = Field(
        None,
        description="Category ID for category recommendations (context=category)"
    )
    search_query: Optional[str] = Field(
        None,
        max_length=500,
        description="Search query for search-based recommendations (context=search)"
    )

    # Filters
    filters: Optional[FilterParams] = Field(None, description="Product filters")

    # Pagination
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results to return")

    # Recommendation settings
    use_session_context: bool = Field(
        default=True,
        description="Use recent session activity for recommendations"
    )
    enable_diversity: bool = Field(
        default=True,
        description="Apply result diversity"
    )
    diversity_lambda: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Diversity weight (0=relevance only, 1=diversity only)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "context": "feed",
                "filters": {
                    "min_price": 30.0,
                    "max_price": 100.0,
                    "in_stock": True
                },
                "offset": 0,
                "limit": 20,
                "use_session_context": True,
                "enable_diversity": True
            }
        }


class RecommendResponse(BaseModel):
    """
    Recommendation response model.

    Contains personalized recommendations and metadata.
    """

    # Results
    results: List[ProductResult] = Field(..., description="List of recommended products")

    # Pagination info
    total: int = Field(..., description="Total number of results")
    offset: int = Field(..., description="Results offset")
    limit: int = Field(..., description="Results limit")
    page: int = Field(..., description="Current page (1-indexed)")

    # Request info
    user_id: str = Field(..., description="User ID (UUID)")
    context: str = Field(..., description="Recommendation context")

    # Performance metrics
    recommendation_time_ms: float = Field(..., description="Recommendation time in milliseconds")
    total_time_ms: float = Field(..., description="Total request time in milliseconds")

    # Metadata
    personalized: bool = Field(default=True, description="Whether results are personalized")
    cached: bool = Field(default=False, description="Whether results came from cache")
    filters_applied: bool = Field(default=False, description="Whether filters were applied")
    diversity_applied: bool = Field(default=False, description="Whether diversity was applied")

    # User context info
    has_long_term_profile: bool = Field(
        default=False,
        description="Whether user has long-term preference profile"
    )
    has_session_context: bool = Field(
        default=False,
        description="Whether user has recent session activity"
    )

    # Blending info (for transparency)
    blend_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Blending weights used (long_term, session, query)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "product_id": 456,
                        "title": "Floral Summer Dress",
                        "price": 59.99,
                        "image_url": "https://example.com/image.jpg",
                        "similarity": 0.92,
                        "rank": 0,
                        "final_score": 0.87
                    }
                ],
                "total": 150,
                "offset": 0,
                "limit": 20,
                "page": 1,
                "user_id": 123,
                "context": "feed",
                "recommendation_time_ms": 45.2,
                "total_time_ms": 78.5,
                "cached": False,
                "has_long_term_profile": True,
                "has_session_context": True,
                "blend_weights": {
                    "long_term": 0.6,
                    "session": 0.4
                }
            }
        }
