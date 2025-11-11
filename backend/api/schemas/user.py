"""
User-specific request/response schemas.
Pydantic models for user preferences, favorites, history, and statistics.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...db.models import Product


class UserPreferencesUpdate(BaseModel):
    """Request schema for updating user preferences."""

    preferred_categories: Optional[List[str]] = Field(
        None, description="List of preferred category names"
    )
    price_band_min: Optional[float] = Field(None, ge=0, description="Minimum price preference")
    price_band_max: Optional[float] = Field(None, ge=0, description="Maximum price preference")
    style_preferences: Optional[Dict[str, Any]] = Field(
        None, description="Style preference metadata"
    )
    brand_affinities: Optional[Dict[str, float]] = Field(None, description="Brand affinity scores")


class UserStatsResponse(BaseModel):
    """Response schema for user statistics."""

    total_interactions: int = Field(..., description="Total number of interactions")
    total_views: int = Field(..., description="Total product views")
    total_clicks: int = Field(..., description="Total product clicks")
    total_likes: int = Field(..., description="Total products liked")
    total_cart_adds: int = Field(..., description="Total add-to-cart actions")
    total_purchases: int = Field(..., description="Total purchases")
    favorite_categories: List[Dict[str, Any]] = Field(
        ..., description="Top categories by interaction"
    )
    favorite_brands: List[Dict[str, Any]] = Field(..., description="Top brands by interaction")
    avg_price_point: Optional[float] = Field(
        None, description="Average price of interacted products"
    )
    account_age_days: int = Field(..., description="Days since account creation")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")


class InteractionHistoryItem(BaseModel):
    """Single interaction history item."""

    interaction_id: int
    product_id: str
    product_title: Optional[str]
    product_image_url: Optional[str]
    product_price: Optional[float]
    interaction_type: str
    created_at: datetime
    context: Optional[str]
    query: Optional[str]

    model_config = {"from_attributes": True}


class InteractionHistoryResponse(BaseModel):
    """Response schema for interaction history."""

    interactions: List[InteractionHistoryItem]
    total: int
    offset: int
    limit: int


class FavoriteProduct(BaseModel):
    """Favorite product with interaction metadata."""

    product_id: str
    title: str
    price: float
    currency: str
    image_url: Optional[str]
    brand: Optional[str]
    in_stock: bool
    liked_at: datetime

    model_config = {"from_attributes": True}


class FavoritesResponse(BaseModel):
    """Response schema for user favorites."""

    favorites: List[FavoriteProduct]
    total: int
