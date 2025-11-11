"""
User-specific routes.
Handles user favorites, history, statistics, and preferences.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..dependencies import get_db, get_current_user
from ..schemas.user import (
    UserPreferencesUpdate,
    UserStatsResponse,
    InteractionHistoryResponse,
    InteractionHistoryItem,
    FavoritesResponse,
    FavoriteProduct,
)
from ..schemas.auth import UserResponse
from ...db.models import User, UserInteraction, Product

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/favorites", response_model=FavoritesResponse)
async def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all products the user has liked/favorited.
    """
    # Query for all LIKE interactions
    liked_interactions = (
        db.query(UserInteraction)
        .filter(
            UserInteraction.user_id == current_user.id, UserInteraction.interaction_type == "like"
        )
        .order_by(desc(UserInteraction.created_at))
        .all()
    )

    # Get unique product IDs
    product_ids = list(set([i.product_id for i in liked_interactions]))

    # Fetch product details
    products = db.query(Product).filter(Product.product_id.in_(product_ids)).all()

    # Create a map of product_id to liked_at timestamp
    liked_at_map = {i.product_id: i.created_at for i in liked_interactions}

    # Build response
    favorites = []
    for product in products:
        favorites.append(
            FavoriteProduct(
                product_id=product.product_id,
                title=product.title,
                price=product.price,
                currency=product.currency or "$",
                image_url=product.image_url,
                brand=product.brand,
                in_stock=product.in_stock,
                liked_at=liked_at_map.get(product.product_id, datetime.utcnow()),
            )
        )

    # Sort by liked_at descending
    favorites.sort(key=lambda x: x.liked_at, reverse=True)

    return FavoritesResponse(favorites=favorites, total=len(favorites))


@router.delete("/me/favorites/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a product from favorites (unlike).
    """
    # Delete the LIKE interaction
    deleted_count = (
        db.query(UserInteraction)
        .filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.product_id == product_id,
            UserInteraction.interaction_type == "like",
        )
        .delete()
    )

    db.commit()

    if deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")

    return None


@router.get("/me/history", response_model=InteractionHistoryResponse)
async def get_interaction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    interaction_type: Optional[str] = Query(None, description="Filter by interaction type"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """
    Get user's interaction history with optional filtering.
    """
    # Base query
    query = (
        db.query(UserInteraction, Product)
        .join(Product, UserInteraction.product_id == Product.product_id)
        .filter(UserInteraction.user_id == current_user.id)
    )

    # Filter by interaction type if provided
    if interaction_type:
        query = query.filter(UserInteraction.interaction_type == interaction_type)

    # Get total count
    total = query.count()

    # Get paginated results
    results = query.order_by(desc(UserInteraction.created_at)).limit(limit).offset(offset).all()

    # Build response
    interactions = []
    for interaction, product in results:
        interactions.append(
            InteractionHistoryItem(
                interaction_id=interaction.id,
                product_id=interaction.product_id,
                product_title=product.title if product else None,
                product_image_url=product.image_url if product else None,
                product_price=product.price if product else None,
                interaction_type=interaction.interaction_type,
                created_at=interaction.created_at,
                context=interaction.context,
                query=interaction.query,
            )
        )

    return InteractionHistoryResponse(
        interactions=interactions, total=total, offset=offset, limit=limit
    )


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user statistics and insights.
    """
    # Get interaction counts by type
    interaction_counts = (
        db.query(UserInteraction.interaction_type, func.count(UserInteraction.id).label("count"))
        .filter(UserInteraction.user_id == current_user.id)
        .group_by(UserInteraction.interaction_type)
        .all()
    )

    counts_map = {row[0]: row[1] for row in interaction_counts}

    # Get favorite categories (top interacted categories)
    category_stats = (
        db.query(Product.category, func.count(UserInteraction.id).label("interaction_count"))
        .join(UserInteraction, Product.product_id == UserInteraction.product_id)
        .filter(UserInteraction.user_id == current_user.id)
        .filter(Product.category.isnot(None))
        .group_by(Product.category)
        .order_by(desc("interaction_count"))
        .limit(10)
        .all()
    )

    favorite_categories = [{"category": row[0], "count": row[1]} for row in category_stats]

    # Get favorite brands
    brand_stats = (
        db.query(Product.brand, func.count(UserInteraction.id).label("interaction_count"))
        .join(UserInteraction, Product.product_id == UserInteraction.product_id)
        .filter(UserInteraction.user_id == current_user.id)
        .filter(Product.brand.isnot(None))
        .group_by(Product.brand)
        .order_by(desc("interaction_count"))
        .limit(10)
        .all()
    )

    favorite_brands = [{"brand": row[0], "count": row[1]} for row in brand_stats]

    # Get average price point
    avg_price = (
        db.query(func.avg(Product.price))
        .join(UserInteraction, Product.product_id == UserInteraction.product_id)
        .filter(UserInteraction.user_id == current_user.id)
        .scalar()
    )

    # Calculate account age
    account_age = (datetime.utcnow() - current_user.created_at).days

    return UserStatsResponse(
        total_interactions=current_user.total_interactions,
        total_views=counts_map.get("view", 0),
        total_clicks=counts_map.get("click", 0),
        total_likes=counts_map.get("like", 0),
        total_cart_adds=counts_map.get("add_to_cart", 0),
        total_purchases=counts_map.get("purchase", 0),
        favorite_categories=favorite_categories,
        favorite_brands=favorite_brands,
        avg_price_point=float(avg_price) if avg_price else None,
        account_age_days=account_age,
        last_active=current_user.last_active,
    )


@router.put("/me/preferences", response_model=UserResponse)
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user preferences.
    """
    # Update fields if provided
    if preferences.preferred_categories is not None:
        current_user.preferred_categories = preferences.preferred_categories

    if preferences.price_band_min is not None:
        current_user.price_band_min = preferences.price_band_min

    if preferences.price_band_max is not None:
        current_user.price_band_max = preferences.price_band_max

    if preferences.style_preferences is not None:
        current_user.style_preferences = preferences.style_preferences

    if preferences.brand_affinities is not None:
        current_user.brand_affinities = preferences.brand_affinities

    current_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)
