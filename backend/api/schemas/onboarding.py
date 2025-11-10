"""
Onboarding schemas.
Handles user onboarding flow including style quiz and preference setup.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class OnboardingProductsRequest(BaseModel):
    """Request for fetching products for onboarding moodboard."""
    limit: int = Field(20, ge=12, le=50, description="Number of products to return")
    diverse: bool = Field(True, description="Whether to return diverse products across categories")


class OnboardingProduct(BaseModel):
    """Simplified product for onboarding display."""
    product_id: str
    title: str
    image_url: Optional[str]
    price: float
    brand: Optional[str]
    category: Optional[str]


class OnboardingProductsResponse(BaseModel):
    """Response containing products for moodboard selection."""
    products: List[OnboardingProduct]
    total: int


class OnboardingCompleteRequest(BaseModel):
    """Request to complete onboarding with style preferences."""
    selected_product_ids: List[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-5 product IDs selected from moodboard"
    )
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price preference")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price preference")

    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Ensure max price is greater than min price."""
        if v is not None and info.data.get('price_min') is not None:
            if v <= info.data['price_min']:
                raise ValueError("Maximum price must be greater than minimum price")
        return v


class OnboardingCompleteResponse(BaseModel):
    """Response after completing onboarding."""
    success: bool
    user_id: str
    onboarded: bool
    embedding_created: bool
    preferences_saved: bool
    selected_products_count: int
    message: str
    next_step: str = Field("/", description="Where to redirect user after onboarding")

    # Metadata about the created embedding
    embedding_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Information about the created embedding (confidence, method, etc.)"
    )


class OnboardingStatusResponse(BaseModel):
    """Response for checking onboarding status."""
    user_id: str
    onboarded: bool
    has_embedding: bool
    has_preferences: bool
    registration_date: str
    onboarding_date: Optional[str] = None