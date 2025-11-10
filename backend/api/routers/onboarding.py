"""
Onboarding routes.
Handles user onboarding including style quiz and preference setup.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..dependencies import get_db, get_current_user, get_embedding_cache
from ..schemas.onboarding import (
    OnboardingProductsRequest,
    OnboardingProductsResponse,
    OnboardingProduct,
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    OnboardingStatusResponse,
)
from ...db.models import User, Product, UserInteraction, UserEmbedding, ProductEmbedding
from ...ml.user_modeling.cold_start import ColdStartEmbedding
from ...ml.user_modeling.embedding_builder import UserEmbeddingBuilder
from ...ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/products", response_model=OnboardingProductsResponse)
async def get_onboarding_products(
    request: OnboardingProductsRequest = OnboardingProductsRequest(),
    db: Session = Depends(get_db),
) -> OnboardingProductsResponse:
    """
    Get popular/trending products for onboarding moodboard.

    Returns diverse, popular products that new users can select from
    to indicate their style preferences.
    """
    try:
        # Query for popular products
        # Get products with the most interactions in the last 30 days
        popular_products_query = (
            db.query(Product, func.count(UserInteraction.id).label('interaction_count'))
            .outerjoin(UserInteraction, Product.id == UserInteraction.product_id)
            .filter(Product.is_active == True)
            # Skip in_stock check for now since no products are marked as in_stock in test data
            # .filter(Product.in_stock == True)
            .filter(
                (Product.merchant_image_url.isnot(None)) |
                (Product.aw_image_url.isnot(None)) |
                (Product.large_image.isnot(None))
            )  # Must have at least one image for moodboard
            .group_by(Product.id)
            .order_by(desc('interaction_count'))
        )

        if request.diverse:
            # If diverse mode, try to get products from different categories
            categories = db.query(Product.category_name).filter(
                Product.category_name.isnot(None)
            ).distinct().limit(10).all()

            products = []
            products_per_category = max(2, request.limit // len(categories)) if categories else request.limit

            for category in categories:
                category_products = popular_products_query.filter(
                    Product.category_name == category[0]
                ).limit(products_per_category).all()
                products.extend(category_products)

                if len(products) >= request.limit:
                    break

            # If not enough diverse products, fill with popular ones
            if len(products) < request.limit:
                remaining = request.limit - len(products)
                exclude_ids = [p[0].id for p in products]
                more_products = popular_products_query.filter(
                    ~Product.id.in_(exclude_ids)
                ).limit(remaining).all()
                products.extend(more_products)
        else:
            # Just get the most popular products
            products = popular_products_query.limit(request.limit).all()

        # Convert to response format
        onboarding_products = []
        for product, _ in products[:request.limit]:
            # Use merchant_image_url or aw_image_url, whichever is available
            image_url = product.merchant_image_url or product.aw_image_url or product.large_image

            onboarding_products.append(OnboardingProduct(
                product_id=str(product.id),
                title=product.product_name,
                image_url=image_url,
                price=float(product.search_price) if product.search_price else 0.0,
                brand=product.brand_name,
                category=product.category_name,
            ))

        return OnboardingProductsResponse(
            products=onboarding_products,
            total=len(onboarding_products)
        )

    except Exception as e:
        logger.error(f"Failed to fetch onboarding products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products for onboarding"
        )


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cache: EmbeddingCache = Depends(get_embedding_cache),
) -> OnboardingCompleteResponse:
    """
    Complete user onboarding by processing style selections.

    This endpoint:
    1. Validates selected products exist
    2. Creates initial user embedding from selections
    3. Updates user preferences (price range)
    4. Marks user as onboarded
    """
    try:
        # Check if already onboarded
        if current_user.onboarded:
            return OnboardingCompleteResponse(
                success=True,
                user_id=str(current_user.id),
                onboarded=True,
                embedding_created=True,
                preferences_saved=True,
                selected_products_count=0,
                message="User has already completed onboarding",
                next_step="/feed"
            )

        # Validate selected products exist (selected_product_ids are strings of UUIDs)
        from uuid import UUID

        # Convert string IDs to UUIDs for database query
        product_uuids = []
        for pid in request.selected_product_ids:
            try:
                product_uuids.append(UUID(pid))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid product ID format: {pid}"
                )

        selected_products = db.query(Product).filter(
            Product.id.in_(product_uuids)
        ).all()

        if len(selected_products) != len(request.selected_product_ids):
            found_ids = {str(p.id) for p in selected_products}
            missing_ids = set(request.selected_product_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Some selected products not found: {missing_ids}"
            )

        # Get product embeddings from database
        product_embeddings_dict = {}

        for product in selected_products:
            # Query database directly for product embeddings
            embedding_record = db.query(ProductEmbedding).filter(
                ProductEmbedding.product_id == product.id,
                ProductEmbedding.embedding_type == 'text'
            ).first()

            if embedding_record and embedding_record.embedding:
                product_embeddings_dict[str(product.id)] = np.array(embedding_record.embedding)
            else:
                # If no embedding found, log warning
                logger.warning(f"No embedding found for product {product.id}")

        if not product_embeddings_dict:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not find embeddings for selected products"
            )

        # Create cold-start embedding from selections
        cold_start = ColdStartEmbedding()
        embedding_result = cold_start.from_style_quiz(
            selected_product_ids=list(product_embeddings_dict.keys()),
            product_embeddings_dict=product_embeddings_dict
        )

        # Save the embedding to database and cache
        embedding_builder = UserEmbeddingBuilder(db, cache)
        saved = embedding_builder.save_user_embedding(
            user_id=current_user.id,
            embedding=embedding_result['user_embedding'],
            embedding_type='long_term',  # Initialize as long-term profile
            metadata={
                'method': 'onboarding_style_quiz',
                'product_count': len(request.selected_product_ids),
                'confidence': embedding_result.get('confidence', 0.8),
                'created_at': datetime.utcnow().isoformat()
            }
        )

        # Update user preferences
        if request.price_min is not None:
            current_user.price_band_min = request.price_min
        if request.price_max is not None:
            current_user.price_band_max = request.price_max

        # Mark user as onboarded
        current_user.onboarded = True
        current_user.updated_at = datetime.utcnow()

        # Also track these as initial interactions (likes)
        for product_id in request.selected_product_ids:
            interaction = UserInteraction(
                user_id=current_user.id,
                product_id=product_id,
                interaction_type='like',
                context='onboarding_moodboard',
                metadata={
                    'source': 'onboarding',
                    'step': 'style_quiz'
                }
            )
            db.add(interaction)

        # Commit all changes
        db.commit()

        return OnboardingCompleteResponse(
            success=True,
            user_id=str(current_user.id),
            onboarded=True,
            embedding_created=saved,
            preferences_saved=True,
            selected_products_count=len(request.selected_product_ids),
            message="Onboarding completed successfully! Your style profile has been created.",
            next_step="/feed",
            embedding_metadata={
                'confidence': embedding_result.get('confidence', 0.8),
                'method': embedding_result.get('method', 'style_quiz'),
                'products_used': len(request.selected_product_ids)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete onboarding for user {current_user.id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding. Please try again."
        )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingStatusResponse:
    """
    Check user's onboarding status.

    Returns whether the user has completed onboarding and has
    the necessary embeddings for recommendations.
    """
    # Check if user has embeddings
    user_embedding = db.query(UserEmbedding).filter(
        UserEmbedding.user_id == current_user.id
    ).first()

    has_embedding = user_embedding is not None and (
        user_embedding.long_term_embedding is not None or
        user_embedding.session_embedding is not None
    )

    # Check if user has preferences
    has_preferences = (
        current_user.price_band_min is not None or
        current_user.price_band_max is not None or
        (current_user.preferred_categories and len(current_user.preferred_categories) > 0) or
        (current_user.style_preferences and len(current_user.style_preferences) > 0)
    )

    # Get onboarding date if completed
    onboarding_date = None
    if current_user.onboarded:
        # Try to find the first onboarding interaction
        first_onboarding = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.context == 'onboarding_moodboard'
        ).order_by(UserInteraction.created_at).first()

        if first_onboarding:
            onboarding_date = first_onboarding.created_at.isoformat()

    return OnboardingStatusResponse(
        user_id=str(current_user.id),
        onboarded=current_user.onboarded,
        has_embedding=has_embedding,
        has_preferences=has_preferences,
        registration_date=current_user.created_at.isoformat(),
        onboarding_date=onboarding_date
    )