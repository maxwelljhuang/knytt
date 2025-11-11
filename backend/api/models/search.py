"""
Search Models
Pydantic models for search endpoint.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .common import PaginationParams, FilterParams


class SearchRequest(BaseModel):
    """
    Search request model.

    Supports text-based search with optional user personalization and filters.
    """

    query: str = Field(..., min_length=1, max_length=500, description="Search query text")

    # User context (optional for personalization)
    user_id: Optional[int] = Field(None, description="User ID for personalized results")

    # Filters
    filters: Optional[FilterParams] = Field(None, description="Product filters")

    # Pagination
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results to return")

    # Search settings
    use_ranking: bool = Field(default=True, description="Apply heuristic ranking")
    enable_diversity: bool = Field(default=True, description="Apply result diversity")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "summer dresses",
                "user_id": 123,
                "filters": {"min_price": 30.0, "max_price": 100.0, "in_stock": True},
                "offset": 0,
                "limit": 20,
            }
        }


class ProductResult(BaseModel):
    """
    Single product result.

    Contains product information and relevance scores.
    """

    # Product identifiers
    product_id: str = Field(..., description="Product ID (UUID)")

    # Product information
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., description="Product price")
    currency: str = Field(default="USD", description="Price currency")
    image_url: Optional[str] = Field(None, description="Primary product image URL")

    # Merchant/brand info
    merchant_id: Optional[int] = Field(None, description="Merchant ID")
    merchant_name: Optional[str] = Field(None, description="Merchant name")
    brand: Optional[str] = Field(None, description="Product brand")
    brand_id: Optional[int] = Field(None, description="Brand ID")

    # Availability
    in_stock: bool = Field(default=True, description="Stock availability")
    stock_quantity: Optional[int] = Field(None, description="Stock quantity")

    # Category/classification
    category_id: Optional[int] = Field(None, description="Category ID")
    category_name: Optional[str] = Field(None, description="Category name")

    # Additional product details
    product_url: Optional[str] = Field(None, description="Product page URL")
    rrp_price: Optional[float] = Field(None, description="Recommended retail price")
    colour: Optional[str] = Field(None, description="Product colour")
    fashion_category: Optional[str] = Field(None, description="Fashion category")
    fashion_size: Optional[str] = Field(None, description="Fashion size")
    quality_score: Optional[float] = Field(None, description="Data quality score (0-1)")
    rating: Optional[float] = Field(None, description="Average customer rating")
    review_count: Optional[int] = Field(None, description="Number of reviews")

    # Relevance scores
    similarity: float = Field(..., ge=0, le=1, description="Similarity score (0-1)")
    rank: int = Field(..., ge=0, description="Result rank (0-indexed)")

    # Optional ranking details
    final_score: Optional[float] = Field(None, description="Final ranking score")
    popularity_score: Optional[float] = Field(None, description="Popularity component")
    price_affinity_score: Optional[float] = Field(None, description="Price affinity component")
    brand_match_score: Optional[float] = Field(None, description="Brand match component")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 456,
                "title": "Floral Summer Dress",
                "description": "Beautiful floral print dress perfect for summer",
                "price": 59.99,
                "currency": "USD",
                "image_url": "https://example.com/image.jpg",
                "merchant_name": "Fashion Store",
                "brand": "StyleCo",
                "in_stock": True,
                "category_name": "Dresses",
                "similarity": 0.92,
                "rank": 0,
                "final_score": 0.87,
            }
        }


class SearchResponse(BaseModel):
    """
    Search response model.

    Contains search results and metadata.
    """

    # Results
    results: List[ProductResult] = Field(..., description="List of product results")

    # Pagination info
    total: int = Field(..., description="Total number of results")
    offset: int = Field(..., description="Results offset")
    limit: int = Field(..., description="Results limit")
    page: int = Field(..., description="Current page (1-indexed)")

    # Query info
    query: str = Field(..., description="Original search query")
    user_id: Optional[int] = Field(None, description="User ID (if personalized)")

    # Performance metrics
    search_time_ms: float = Field(..., description="Search time in milliseconds")
    total_time_ms: float = Field(..., description="Total request time in milliseconds")

    # Metadata
    personalized: bool = Field(default=False, description="Whether results are personalized")
    cached: bool = Field(default=False, description="Whether results came from cache")
    filters_applied: bool = Field(default=False, description="Whether filters were applied")
    ranking_applied: bool = Field(default=True, description="Whether ranking was applied")

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
                    }
                ],
                "total": 150,
                "offset": 0,
                "limit": 20,
                "page": 1,
                "query": "summer dresses",
                "search_time_ms": 45.2,
                "total_time_ms": 78.5,
                "cached": False,
            }
        }
