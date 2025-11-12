"""
Discover/Browse endpoints for product discovery without ML dependencies.
Provides fallback when search service is unavailable.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...db.models import Product, UserInteraction
from ..dependencies import get_db
from ..models.search import ProductResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["discover"])


@router.get("/discover", status_code=status.HTTP_200_OK)
async def discover_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="popular", regex="^(popular|recent|price_low|price_high)$"),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    """
    Discover products without ML dependencies - simple database query.

    Sort options:
    - popular: Most interactions (default)
    - recent: Recently added
    - price_low: Lowest price first
    - price_high: Highest price first
    """
    try:
        # Base query
        query = db.query(
            Product,
            func.coalesce(func.count(UserInteraction.id), 0).label("interaction_count")
        ).outerjoin(
            UserInteraction, Product.id == UserInteraction.product_id
        ).filter(
            Product.is_active == True  # noqa: E712
        ).group_by(Product.id)

        # Price filters
        if min_price is not None:
            query = query.filter(Product.search_price >= min_price)
        if max_price is not None:
            query = query.filter(Product.search_price <= max_price)

        # Only show products with images
        query = query.filter(
            (Product.merchant_image_url != None) |  # noqa: E711
            (Product.aw_image_url != None) |  # noqa: E711
            (Product.large_image != None)  # noqa: E711
        )

        # Sorting
        if sort_by == "popular":
            query = query.order_by(desc("interaction_count"), desc(Product.ingested_at))
        elif sort_by == "recent":
            query = query.order_by(desc(Product.ingested_at))
        elif sort_by == "price_low":
            query = query.order_by(Product.search_price.asc())
        elif sort_by == "price_high":
            query = query.order_by(Product.search_price.desc())

        # Get total count
        total = query.count()

        # Pagination
        products_with_counts = query.offset(offset).limit(limit).all()

        # Build response
        results: List[ProductResult] = []
        for product, interaction_count in products_with_counts:
            image_url = product.merchant_image_url or product.aw_image_url or product.large_image

            results.append(ProductResult(
                product_id=str(product.id),
                title=product.product_name or "",
                description=product.description or "",
                price=float(product.search_price) if product.search_price else 0.0,
                currency=product.currency or "USD",
                merchant_name=product.merchant_name or "",
                merchant_id=str(product.merchant_id) if product.merchant_id else None,
                category_name=product.category_name or "",
                category_id=str(product.category_id) if product.category_id else None,
                brand_name=product.brand_name or "",
                image_url=image_url,
                product_url=product.aw_deep_link or product.merchant_deep_link or "",
                in_stock=product.in_stock if product.in_stock is not None else True,
                score=0.0,  # No ML score for simple discover
                similarity=None,
                rank=None,
            ))

        return {
            "results": results,
            "total": total,
            "offset": offset,
            "limit": limit,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "sort_by": sort_by,
        }

    except Exception as e:
        logger.error(f"Failed to fetch discover products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products",
        )
