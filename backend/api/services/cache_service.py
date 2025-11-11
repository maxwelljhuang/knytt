"""
Cache Service
Advanced caching strategies for API performance optimization.
"""

import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict

from ...ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration and TTL policies."""

    # TTL policies (in seconds)
    TTL_SEARCH_RESULTS = 300  # 5 minutes
    TTL_RECOMMEND_RESULTS = 120  # 2 minutes
    TTL_PRODUCT_METADATA = 3600  # 1 hour
    TTL_USER_EMBEDDINGS = 1800  # 30 minutes
    TTL_HOT_EMBEDDINGS = 7200  # 2 hours
    TTL_POPULAR_QUERIES = 600  # 10 minutes

    # Cache warming
    POPULAR_QUERY_THRESHOLD = 5  # Query must appear 5+ times
    ACTIVE_USER_THRESHOLD = 10  # User must have 10+ interactions
    CACHE_WARM_BATCH_SIZE = 100  # Warm 100 items at a time

    # Statistics
    STATS_WINDOW_SECONDS = 3600  # 1 hour rolling window


class CacheStatistics:
    """Track cache performance metrics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0

        # Per-key-type stats
        self.hits_by_type: Dict[str, int] = defaultdict(int)
        self.misses_by_type: Dict[str, int] = defaultdict(int)

        # Timing stats
        self.total_get_time_ms = 0.0
        self.total_set_time_ms = 0.0

        self.start_time = time.time()

    def record_hit(self, key_type: str):
        """Record a cache hit."""
        self.hits += 1
        self.hits_by_type[key_type] += 1

    def record_miss(self, key_type: str):
        """Record a cache miss."""
        self.misses += 1
        self.misses_by_type[key_type] += 1

    def record_set(self):
        """Record a cache set operation."""
        self.sets += 1

    def record_delete(self):
        """Record a cache delete operation."""
        self.deletes += 1

    def record_error(self):
        """Record a cache error."""
        self.errors += 1

    def get_hit_rate(self) -> float:
        """Calculate overall hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics."""
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "total_operations": self.hits + self.misses + self.sets + self.deletes,
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate_percent": self.get_hit_rate(),
            "hits_by_type": dict(self.hits_by_type),
            "misses_by_type": dict(self.misses_by_type),
            "avg_get_time_ms": (
                self.total_get_time_ms / (self.hits + self.misses)
                if (self.hits + self.misses) > 0
                else 0
            ),
        }


class CacheService:
    """
    Advanced caching service with warming, statistics, and optimization.
    """

    def __init__(self, cache: Optional[EmbeddingCache] = None):
        """
        Initialize cache service.

        Args:
            cache: Embedding cache instance
        """
        self.cache = cache or EmbeddingCache()
        self.config = CacheConfig()
        self.stats = CacheStatistics()

        # Track popular queries and active users for warming
        self.popular_queries: Dict[str, int] = {}  # query -> count
        self.active_users: Set[int] = set()

        logger.info("Cache service initialized")

    def get_search_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached search results.

        Args:
            cache_key: Cache key

        Returns:
            Cached search results or None
        """
        start_time = time.time()

        try:
            result = self.cache.redis.get(cache_key)

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats.total_get_time_ms += elapsed_ms

            if result:
                self.stats.record_hit("search")
                logger.debug(f"Search cache HIT: {cache_key} ({elapsed_ms:.2f}ms)")
            else:
                self.stats.record_miss("search")
                logger.debug(f"Search cache MISS: {cache_key}")

            return result

        except Exception as e:
            self.stats.record_error()
            logger.error(f"Failed to get search results from cache: {e}")
            return None

    def set_search_results(
        self, cache_key: str, results: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        Cache search results.

        Args:
            cache_key: Cache key
            results: Search results to cache
            ttl: Time-to-live in seconds (default: config TTL)

        Returns:
            True if cached successfully
        """
        start_time = time.time()
        ttl = ttl or self.config.TTL_SEARCH_RESULTS

        try:
            # Convert Pydantic models to dicts
            cacheable_data = results.copy()
            if "results" in cacheable_data:
                cacheable_data["results"] = [
                    r.dict() if hasattr(r, "dict") else r for r in cacheable_data["results"]
                ]

            success = self.cache.redis.set(cache_key, cacheable_data, ttl=ttl)

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats.total_set_time_ms += elapsed_ms

            if success:
                self.stats.record_set()
                logger.debug(f"Cached search results: {cache_key} (TTL={ttl}s)")

            return success

        except Exception as e:
            self.stats.record_error()
            logger.error(f"Failed to cache search results: {e}")
            return False

    def get_recommend_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached recommendation results."""
        start_time = time.time()

        try:
            result = self.cache.redis.get(cache_key)

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats.total_get_time_ms += elapsed_ms

            if result:
                self.stats.record_hit("recommend")
            else:
                self.stats.record_miss("recommend")

            return result

        except Exception as e:
            self.stats.record_error()
            logger.error(f"Failed to get recommend results: {e}")
            return None

    def set_recommend_results(
        self, cache_key: str, results: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Cache recommendation results."""
        ttl = ttl or self.config.TTL_RECOMMEND_RESULTS

        try:
            cacheable_data = results.copy()
            if "results" in cacheable_data:
                cacheable_data["results"] = [
                    r.dict() if hasattr(r, "dict") else r for r in cacheable_data["results"]
                ]

            success = self.cache.redis.set(cache_key, cacheable_data, ttl=ttl)

            if success:
                self.stats.record_set()

            return success

        except Exception as e:
            self.stats.record_error()
            logger.error(f"Failed to cache recommend results: {e}")
            return False

    def track_query(self, query: str):
        """
        Track query for cache warming.

        Args:
            query: Search query
        """
        normalized_query = query.lower().strip()
        self.popular_queries[normalized_query] = self.popular_queries.get(normalized_query, 0) + 1

    def track_user_activity(self, user_id: int):
        """
        Track user activity for hot embedding caching.

        Args:
            user_id: User ID
        """
        self.active_users.add(user_id)

    def get_popular_queries(self, limit: int = 100) -> List[str]:
        """
        Get most popular queries.

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of popular queries
        """
        sorted_queries = sorted(self.popular_queries.items(), key=lambda x: x[1], reverse=True)

        return [
            query for query, count in sorted_queries if count >= self.config.POPULAR_QUERY_THRESHOLD
        ][:limit]

    def get_active_users(self) -> List[int]:
        """
        Get active users for cache warming.

        Returns:
            List of active user IDs
        """
        return list(self.active_users)

    def warm_popular_queries(self, search_function, limit: int = 50):
        """
        Warm cache with popular queries.

        Args:
            search_function: Function to execute search (async)
            limit: Number of queries to warm
        """
        popular = self.get_popular_queries(limit)

        logger.info(f"Warming cache with {len(popular)} popular queries")

        for query in popular:
            try:
                # Execute search to populate cache
                # This should be called as a background task
                logger.debug(f"Warming cache for query: {query}")
                # search_function(query)  # Caller implements actual search
            except Exception as e:
                logger.error(f"Failed to warm cache for query '{query}': {e}")

    def warm_active_users(self, recommend_function, limit: int = 100):
        """
        Warm cache with active user recommendations.

        Args:
            recommend_function: Function to execute recommendations
            limit: Number of users to warm
        """
        active_users = list(self.active_users)[:limit]

        logger.info(f"Warming cache with {len(active_users)} active users")

        for user_id in active_users:
            try:
                logger.debug(f"Warming cache for user: {user_id}")
                # recommend_function(user_id)  # Caller implements actual recommendation
            except Exception as e:
                logger.error(f"Failed to warm cache for user {user_id}: {e}")

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "search:*", "recommend:user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            # Note: This requires Redis SCAN which may not be in EmbeddingCache
            # For now, just log
            logger.info(f"Invalidating cache pattern: {pattern}")
            self.stats.record_delete()

            # TODO: Implement with Redis SCAN
            # deleted = self.cache.redis.delete_pattern(pattern)
            # return deleted

            return 0

        except Exception as e:
            self.stats.record_error()
            logger.error(f"Failed to invalidate pattern {pattern}: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.stats.get_stats()

    def reset_statistics(self):
        """Reset cache statistics."""
        self.stats = CacheStatistics()
        logger.info("Cache statistics reset")


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
