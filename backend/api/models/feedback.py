"""
Feedback Models
Pydantic models for feedback endpoint.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class InteractionType(str, Enum):
    """
    User interaction types.

    Different types of user-product interactions for tracking behavior.
    """

    VIEW = "view"  # User viewed product details
    CLICK = "click"  # User clicked on product in search/recommendation
    ADD_TO_CART = "add_to_cart"  # User added product to cart
    PURCHASE = "purchase"  # User purchased product
    LIKE = "like"  # User favorited/liked product
    SHARE = "share"  # User shared product
    RATING = "rating"  # User rated product


class FeedbackRequest(BaseModel):
    """
    Feedback request model.

    Records user-product interaction for personalization.
    """

    # User and product
    user_id: int = Field(..., description="User ID (external ID)")
    product_id: str = Field(..., description="Product ID (UUID)")

    # Interaction details
    interaction_type: InteractionType = Field(..., description="Type of interaction")

    # Optional interaction metadata
    rating: Optional[float] = Field(
        None, ge=0, le=5, description="Rating value (0-5) for rating interactions"
    )
    session_id: Optional[str] = Field(
        None, max_length=128, description="Session ID for grouping interactions"
    )
    context: Optional[str] = Field(
        None,
        max_length=64,
        description="Context where interaction occurred (search, feed, similar, etc.)",
    )
    query: Optional[str] = Field(
        None,
        max_length=500,
        description="Search query that led to this interaction (if applicable)",
    )
    position: Optional[int] = Field(
        None, ge=0, description="Position of product in results (for CTR analysis)"
    )

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional interaction metadata (page, referrer, etc.)"
    )

    # Update preferences
    update_embeddings: bool = Field(
        default=True, description="Whether to trigger user embedding update"
    )
    update_session: bool = Field(default=True, description="Whether to update session embeddings")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "interaction_type": "click",
                "session_id": "sess_abc123",
                "context": "search",
                "query": "summer dresses",
                "position": 2,
                "metadata": {"page": "search_results", "device": "mobile"},
            }
        }


class FeedbackResponse(BaseModel):
    """
    Feedback response model.

    Confirmation of feedback recording.
    """

    # Status
    success: bool = Field(..., description="Whether feedback was recorded successfully")
    message: str = Field(default="Feedback recorded", description="Status message")

    # Recorded interaction
    interaction_id: Optional[str] = Field(
        None, description="Database ID of recorded interaction (UUID)"
    )
    user_id: int = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID (UUID)")
    interaction_type: str = Field(..., description="Type of interaction")

    # Update status
    embeddings_updated: bool = Field(
        default=False, description="Whether user embeddings were updated"
    )
    session_updated: bool = Field(
        default=False, description="Whether session embeddings were updated"
    )
    cache_invalidated: bool = Field(
        default=False, description="Whether user's cached recommendations were invalidated"
    )

    # Timestamps
    recorded_at: datetime = Field(..., description="When the feedback was recorded")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Feedback recorded",
                "interaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 123,
                "product_id": "20970224-990e-4483-89af-d01978286247",
                "interaction_type": "click",
                "embeddings_updated": True,
                "session_updated": True,
                "cache_invalidated": True,
                "recorded_at": "2025-01-15T10:30:00Z",
                "processing_time_ms": 12.5,
            }
        }


# Interaction weights for different types (for embedding updates)
INTERACTION_WEIGHTS = {
    InteractionType.VIEW: 0.1,
    InteractionType.CLICK: 0.3,
    InteractionType.ADD_TO_CART: 0.6,
    InteractionType.PURCHASE: 1.0,
    InteractionType.LIKE: 0.5,
    InteractionType.SHARE: 0.4,
    InteractionType.RATING: 0.7,
}


# Session decay for different interaction types (in minutes)
SESSION_DECAY = {
    InteractionType.VIEW: 5,
    InteractionType.CLICK: 10,
    InteractionType.ADD_TO_CART: 30,
    InteractionType.PURCHASE: 60,
    InteractionType.LIKE: 30,
    InteractionType.SHARE: 20,
    InteractionType.RATING: 45,
}
