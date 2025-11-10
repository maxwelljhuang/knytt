"""
Embedding Cache
Caches product and user embeddings in Redis for fast access.
"""

import logging
import numpy as np
from typing import Optional, Dict, List, Set
from datetime import datetime, timedelta

from ..config import get_ml_config, MLConfig
from .redis_cache import RedisCache, get_redis_cache

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Caches embeddings in Redis with TTL and hot product tracking.

    Supports:
    - Product embedding caching (for frequently viewed products)
    - User embedding caching (long-term and session)
    - Hot product tracking
    - Automatic cache invalidation
    """

    def __init__(
        self,
        config: Optional[MLConfig] = None,
        redis_cache: Optional[RedisCache] = None
    ):
        """
        Initialize embedding cache.

        Args:
            config: ML configuration
            redis_cache: Redis cache client (uses global if not provided)
        """
        self.config = config or get_ml_config()
        self.redis = redis_cache or get_redis_cache(self.config)

        # Cache key prefixes
        self.PRODUCT_PREFIX = "embedding:product:"
        self.USER_LONG_TERM_PREFIX = "embedding:user:long_term:"
        self.USER_SESSION_PREFIX = "embedding:user:session:"
        self.HOT_PRODUCTS_KEY = "hot:products"
        self.PRODUCT_VIEW_COUNT_PREFIX = "stats:product_views:"

        # TTL settings
        self.user_ttl = self.config.storage.redis_ttl_hours * 3600
        self.hot_product_ttl = 86400  # 24 hours

        logger.info("Embedding cache initialized")

    # ========== Product Embeddings ==========

    def get_product_embedding(self, product_id: int) -> Optional[np.ndarray]:
        """
        Get cached product embedding.

        Args:
            product_id: Product ID

        Returns:
            Product embedding or None if not cached
        """
        key = f"{self.PRODUCT_PREFIX}{product_id}"
        embedding = self.redis.get(key)

        if embedding is not None:
            logger.debug(f"Cache HIT for product {product_id}")
            return embedding

        logger.debug(f"Cache MISS for product {product_id}")
        return None

    def set_product_embedding(
        self,
        product_id: int,
        embedding: np.ndarray,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache product embedding.

        Args:
            product_id: Product ID
            embedding: Product embedding
            ttl: Time-to-live in seconds (default: no expiration)

        Returns:
            True if successful
        """
        key = f"{self.PRODUCT_PREFIX}{product_id}"
        return self.redis.set(key, embedding, ttl=ttl)

    def get_product_embeddings_batch(
        self,
        product_ids: List[int]
    ) -> Dict[int, np.ndarray]:
        """
        Get multiple product embeddings from cache.

        Args:
            product_ids: List of product IDs

        Returns:
            Dict mapping product_id -> embedding (only cached ones)
        """
        if not product_ids:
            return {}

        keys = [f"{self.PRODUCT_PREFIX}{pid}" for pid in product_ids]
        cached_data = self.redis.get_many(keys)

        # Map back to product IDs
        result = {}
        for pid, key in zip(product_ids, keys):
            if key in cached_data:
                result[pid] = cached_data[key]

        logger.debug(
            f"Batch cache lookup: {len(result)}/{len(product_ids)} hits "
            f"({len(result)/len(product_ids)*100:.1f}%)"
        )

        return result

    def set_product_embeddings_batch(
        self,
        embeddings: Dict[int, np.ndarray],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache multiple product embeddings.

        Args:
            embeddings: Dict mapping product_id -> embedding
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not embeddings:
            return True

        mapping = {
            f"{self.PRODUCT_PREFIX}{pid}": emb
            for pid, emb in embeddings.items()
        }

        return self.redis.set_many(mapping, ttl=ttl)

    def delete_product_embedding(self, product_id: int) -> bool:
        """
        Invalidate cached product embedding.

        Args:
            product_id: Product ID

        Returns:
            True if deleted
        """
        key = f"{self.PRODUCT_PREFIX}{product_id}"
        return self.redis.delete(key)

    # ========== User Embeddings ==========

    def get_user_long_term_embedding(self, user_id: str) -> Optional[np.ndarray]:
        """
        Get cached user long-term embedding.

        Args:
            user_id: User ID (UUID string)

        Returns:
            User embedding or None if not cached
        """
        key = f"{self.USER_LONG_TERM_PREFIX}{user_id}"
        return self.redis.get(key)

    def set_user_long_term_embedding(
        self,
        user_id: str,
        embedding: np.ndarray
    ) -> bool:
        """
        Cache user long-term embedding.

        Args:
            user_id: User ID (UUID string)
            embedding: User embedding

        Returns:
            True if successful
        """
        key = f"{self.USER_LONG_TERM_PREFIX}{user_id}"
        return self.redis.set(key, embedding, ttl=self.user_ttl)

    def get_user_session_embedding(self, user_id: str) -> Optional[np.ndarray]:
        """
        Get cached user session embedding.

        Args:
            user_id: User ID (UUID string)

        Returns:
            Session embedding or None if not cached
        """
        key = f"{self.USER_SESSION_PREFIX}{user_id}"
        return self.redis.get(key)

    def set_user_session_embedding(
        self,
        user_id: str,
        embedding: np.ndarray,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache user session embedding.

        Args:
            user_id: User ID (UUID string)
            embedding: Session embedding
            ttl: TTL in seconds (default: 30 minutes for sessions)

        Returns:
            True if successful
        """
        key = f"{self.USER_SESSION_PREFIX}{user_id}"
        session_ttl = ttl or 1800  # 30 minutes default for sessions
        return self.redis.set(key, embedding, ttl=session_ttl)

    def get_user_embeddings(
        self,
        user_id: str
    ) -> Dict[str, Optional[np.ndarray]]:
        """
        Get both long-term and session embeddings for a user.

        Args:
            user_id: User ID (UUID string)

        Returns:
            Dict with 'long_term' and 'session' embeddings
        """
        long_term = self.get_user_long_term_embedding(user_id)
        session = self.get_user_session_embedding(user_id)

        return {
            'long_term': long_term,
            'session': session
        }

    def delete_user_embeddings(self, user_id: str) -> int:
        """
        Invalidate all cached embeddings for a user.

        Args:
            user_id: User ID (UUID string)

        Returns:
            Number of keys deleted
        """
        count = 0

        lt_key = f"{self.USER_LONG_TERM_PREFIX}{user_id}"
        if self.redis.delete(lt_key):
            count += 1

        sess_key = f"{self.USER_SESSION_PREFIX}{user_id}"
        if self.redis.delete(sess_key):
            count += 1

        return count

    # ========== Hot Products Tracking ==========

    def track_product_view(self, product_id: int) -> None:
        """
        Track a product view for hot product identification.

        Args:
            product_id: Product ID
        """
        # Increment view count
        view_key = f"{self.PRODUCT_VIEW_COUNT_PREFIX}{product_id}"
        self.redis.increment(view_key)

        # Add to sorted set of hot products (score = view count)
        # Note: This is a simplified approach. In production, use time-decayed scoring
        self.redis._get_client().zincrby(self.HOT_PRODUCTS_KEY, 1, str(product_id))

    def get_hot_products(self, limit: int = 1000) -> List[int]:
        """
        Get list of hot (frequently viewed) product IDs.

        Args:
            limit: Maximum number of hot products to return

        Returns:
            List of product IDs, sorted by view count (descending)
        """
        try:
            client = self.redis._get_client()
            # Get top products from sorted set
            results = client.zrevrange(self.HOT_PRODUCTS_KEY, 0, limit - 1)
            return [int(pid) for pid in results]

        except Exception as e:
            logger.error(f"Error getting hot products: {e}")
            return []

    def is_hot_product(
        self,
        product_id: int,
        threshold: int = 100
    ) -> bool:
        """
        Check if a product is considered "hot" (frequently viewed).

        Args:
            product_id: Product ID
            threshold: Minimum view count to be considered hot

        Returns:
            True if product is hot
        """
        view_key = f"{self.PRODUCT_VIEW_COUNT_PREFIX}{product_id}"
        view_count = self.redis.get(view_key)

        if view_count is None:
            return False

        return view_count >= threshold

    def warm_cache_for_hot_products(
        self,
        product_embeddings: Dict[int, np.ndarray],
        top_n: int = 1000
    ) -> int:
        """
        Warm cache with embeddings for hot products.

        Args:
            product_embeddings: Dict mapping product_id -> embedding
            top_n: Number of top products to cache

        Returns:
            Number of products cached
        """
        hot_products = self.get_hot_products(limit=top_n)

        # Filter to only hot products that we have embeddings for
        to_cache = {
            pid: emb
            for pid, emb in product_embeddings.items()
            if pid in hot_products
        }

        if to_cache:
            self.set_product_embeddings_batch(to_cache, ttl=self.hot_product_ttl)
            logger.info(f"Warmed cache with {len(to_cache)} hot product embeddings")

        return len(to_cache)

    # ========== Cache Management ==========

    def invalidate_all_products(self) -> int:
        """
        Invalidate all cached product embeddings.

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.PRODUCT_PREFIX}*"
        count = self.redis.delete_pattern(pattern)
        logger.info(f"Invalidated {count} product embeddings")
        return count

    def invalidate_all_users(self) -> int:
        """
        Invalidate all cached user embeddings.

        Returns:
            Number of keys deleted
        """
        count = 0
        count += self.redis.delete_pattern(f"{self.USER_LONG_TERM_PREFIX}*")
        count += self.redis.delete_pattern(f"{self.USER_SESSION_PREFIX}*")
        logger.info(f"Invalidated {count} user embeddings")
        return count

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        try:
            client = self.redis._get_client()

            # Count keys by prefix
            product_keys = len(client.keys(f"{self.PRODUCT_PREFIX}*"))
            user_lt_keys = len(client.keys(f"{self.USER_LONG_TERM_PREFIX}*"))
            user_sess_keys = len(client.keys(f"{self.USER_SESSION_PREFIX}*"))

            # Get hot products count
            hot_products_count = client.zcard(self.HOT_PRODUCTS_KEY)

            return {
                'cached_products': product_keys,
                'cached_user_long_term': user_lt_keys,
                'cached_user_session': user_sess_keys,
                'hot_products_tracked': hot_products_count,
                'redis_connected': self.redis.ping(),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'error': str(e),
                'redis_connected': False,
            }
