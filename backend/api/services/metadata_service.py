"""
Metadata Service
Fetches and enriches product metadata from database.
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...ml.caching import EmbeddingCache
from ..models.search import ProductResult

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Service for fetching product metadata from database.

    Handles batch fetching and caching of product details.
    """

    def __init__(self, cache: Optional[EmbeddingCache] = None):
        """
        Initialize metadata service.

        Args:
            cache: Embedding cache instance (for caching product metadata)
        """
        self.cache = cache or EmbeddingCache()

        logger.info("Metadata service initialized")

    def enrich_results(
        self,
        product_ids: List[int],
        scores: Dict[int, Dict[str, float]],
        db: Session
    ) -> List[ProductResult]:
        """
        Enrich search results with product metadata.

        Args:
            product_ids: List of product IDs (in rank order)
            scores: Dict mapping product_id -> score dict (similarity, rank, etc.)
            db: Database session

        Returns:
            List of enriched ProductResult objects
        """
        if not product_ids:
            return []

        # Fetch product metadata from database
        products_data = self._fetch_products_batch(product_ids, db)

        # Build enriched results
        enriched_results = []

        for rank, product_id in enumerate(product_ids):
            product_data = products_data.get(product_id)

            if not product_data:
                logger.warning(f"Product {product_id} not found in database")
                continue

            # Get scores for this product
            product_scores = scores.get(product_id, {})

            # Create ProductResult
            result = ProductResult(
                product_id=product_id,
                title=product_data.get("title", "Unknown Product"),
                description=product_data.get("description"),
                price=product_data.get("price", 0.0),
                currency=product_data.get("currency", "GBP"),
                image_url=product_data.get("image_url"),
                merchant_id=product_data.get("merchant_id"),
                merchant_name=product_data.get("merchant_name"),
                brand=product_data.get("brand"),
                brand_id=product_data.get("brand_id"),
                in_stock=product_data.get("in_stock", True),
                stock_quantity=product_data.get("stock_quantity"),
                category_id=product_data.get("category_id"),
                category_name=product_data.get("category_name"),
                product_url=product_data.get("product_url"),
                rrp_price=product_data.get("rrp_price"),
                colour=product_data.get("colour"),
                fashion_category=product_data.get("fashion_category"),
                fashion_size=product_data.get("fashion_size"),
                quality_score=product_data.get("quality_score"),
                rating=product_data.get("rating"),
                review_count=product_data.get("review_count"),
                similarity=product_scores.get("similarity", 0.0),
                rank=rank,
                final_score=product_scores.get("final_score"),
                popularity_score=product_scores.get("popularity_score"),
                price_affinity_score=product_scores.get("price_affinity_score"),
                brand_match_score=product_scores.get("brand_match_score"),
            )

            enriched_results.append(result)

        logger.debug(f"Enriched {len(enriched_results)} product results")

        return enriched_results

    def _fetch_products_batch(
        self,
        product_ids: List[int],
        db: Session
    ) -> Dict[int, Dict]:
        """
        Fetch product metadata in batch.

        Performs efficient batch query with caching support.

        Args:
            product_ids: List of product IDs
            db: Database session

        Returns:
            Dict mapping product_id -> product_data
        """
        if not product_ids:
            return {}

        logger.debug(f"Fetching metadata for {len(product_ids)} products")

        # Check cache first
        products_data = {}
        uncached_ids = []

        for product_id in product_ids:
            cached = self.get_cached_metadata(product_id)
            if cached:
                products_data[product_id] = cached
            else:
                uncached_ids.append(product_id)

        # Fetch uncached products from database
        if uncached_ids:
            logger.debug(f"Cache miss for {len(uncached_ids)} products, fetching from DB")

            # Convert integer IDs to UUID strings for query
            # Note: The database uses UUID primary keys, so we need to handle the mapping
            # For now, we'll query by product_id as integer (assuming index on products table)

            query = text("""
                SELECT
                    id,
                    product_name,
                    description,
                    search_price,
                    currency,
                    COALESCE(merchant_image_url, aw_image_url, large_image) as image_url,
                    merchant_id,
                    merchant_name,
                    brand_name,
                    brand_id,
                    in_stock,
                    stock_quantity,
                    category_id,
                    category_name,
                    aw_deep_link,
                    rrp_price,
                    colour,
                    fashion_category,
                    fashion_size,
                    quality_score
                FROM products
                WHERE id::text = ANY(:product_ids)
                    AND is_active = true
                    AND COALESCE(merchant_image_url, aw_image_url, large_image) IS NOT NULL
                    AND COALESCE(merchant_image_url, aw_image_url, large_image) != ''
                    AND COALESCE(merchant_image_url, aw_image_url, large_image) ~ '^https?://'
            """)

            try:
                result = db.execute(query, {"product_ids": uncached_ids})
                rows = result.fetchall()

                for row in rows:
                    # Convert UUID to string for consistent key format
                    product_id = str(row.id)

                    product_data = {
                        "id": product_id,
                        "title": row.product_name,
                        "description": row.description,
                        "price": float(row.search_price) if row.search_price else 0.0,
                        "currency": row.currency or "GBP",
                        "image_url": row.image_url,
                        "merchant_id": row.merchant_id,
                        "merchant_name": row.merchant_name,
                        "brand": row.brand_name,
                        "brand_id": row.brand_id,
                        "in_stock": row.in_stock if row.in_stock is not None else True,
                        "stock_quantity": row.stock_quantity,
                        "category_id": row.category_id,
                        "category_name": row.category_name,
                        "product_url": row.aw_deep_link,
                        "rrp_price": float(row.rrp_price) if row.rrp_price else None,
                        "colour": row.colour,
                        "fashion_category": row.fashion_category,
                        "fashion_size": row.fashion_size,
                        "quality_score": row.quality_score,
                        "rating": None,
                        "review_count": None,
                    }

                    products_data[product_id] = product_data

                    # Cache the product metadata (1 hour TTL)
                    self.cache_product_metadata(product_id, product_data, ttl=3600)

                logger.info(f"Fetched {len(rows)} products from database")

            except Exception as e:
                logger.error(f"Failed to fetch products from database: {e}")
                # Return empty dict on error - caller will handle missing products

        return products_data

    def cache_product_metadata(
        self,
        product_id: int,
        metadata: Dict,
        ttl: int = 3600
    ) -> bool:
        """
        Cache product metadata in Redis.

        Args:
            product_id: Product ID
            metadata: Product metadata dict
            ttl: Time-to-live in seconds (default 1 hour)

        Returns:
            True if cached successfully
        """
        cache_key = f"product_metadata:{product_id}"

        try:
            return self.cache.redis.set(cache_key, metadata, ttl=ttl)
        except Exception as e:
            logger.error(f"Failed to cache product metadata: {e}")
            return False

    def get_cached_metadata(self, product_id: int) -> Optional[Dict]:
        """
        Get cached product metadata.

        Args:
            product_id: Product ID

        Returns:
            Product metadata or None if not cached
        """
        cache_key = f"product_metadata:{product_id}"

        try:
            return self.cache.redis.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get cached metadata: {e}")
            return None


# Singleton instance
_metadata_service: Optional[MetadataService] = None


def get_metadata_service() -> MetadataService:
    """Get global metadata service instance."""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service
