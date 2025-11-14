"""
User-specific routes.
Handles user favorites, history, statistics, and preferences.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...db.models import Product, User, UserInteraction
from ..dependencies import get_current_user, get_db
from ..schemas.auth import UserResponse
from ..schemas.user import (
    FavoriteProduct,
    FavoritesResponse,
    InteractionHistoryItem,
    InteractionHistoryResponse,
    UserPreferencesUpdate,
    UserStatsResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/favorites", response_model=FavoritesResponse)
async def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all products the user has liked/favorited.
    """
    from ...db.models import UserFavorite

    # Query favorites with joined products
    favorites_query = (
        db.query(UserFavorite, Product)
        .join(Product, UserFavorite.product_id == Product.id)
        .filter(UserFavorite.user_id == current_user.id)
        .order_by(desc(UserFavorite.created_at))
        .all()
    )

    # Build response
    favorites = []
    for favorite, product in favorites_query:
        favorites.append(
            FavoriteProduct(
                product_id=str(product.id),
                title=product.product_name,
                price=float(product.search_price) if product.search_price else 0.0,
                currency=product.currency or "GBP",
                image_url=product.merchant_image_url or product.aw_image_url,
                brand=product.brand_name,
                in_stock=product.in_stock,
                liked_at=favorite.created_at,
            )
        )

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
    from ...db.models import UserFavorite

    # Convert string product_id to UUID
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID format")

    # Delete from user_favorites
    deleted_count = (
        db.query(UserFavorite)
        .filter(
            UserFavorite.user_id == current_user.id,
            UserFavorite.product_id == product_uuid,
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
        .join(Product, UserInteraction.product_id == Product.id)
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
                product_id=str(interaction.product_id),
                product_title=product.product_name if product else None,
                product_image_url=(product.merchant_image_url or product.aw_image_url) if product else None,
                product_price=float(product.search_price) if (product and product.search_price) else None,
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
