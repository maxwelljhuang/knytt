"""
Redis Cache Client
Thread-safe Redis client with connection pooling.
"""

import logging
import pickle
from typing import Optional, Any, List, Dict
import threading

try:
    import redis
    from redis.connection import ConnectionPool

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..config import get_ml_config, MLConfig

logger = logging.getLogger(__name__)


class RedisCacheError(Exception):
    """Exception raised for Redis cache errors."""

    pass


class RedisCache:
    """
    Redis cache client with connection pooling.

    Provides thread-safe access to Redis for caching embeddings and other data.
    """

    _instance: Optional["RedisCache"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[MLConfig] = None):
        """
        Initialize Redis cache client.

        Args:
            config: ML configuration

        Raises:
            RedisCacheError: If Redis is not available
        """
        # Only initialize once
        if hasattr(self, "_initialized") and self._initialized:
            return

        if not REDIS_AVAILABLE:
            raise RedisCacheError("Redis is not installed. Install with: pip install redis")

        self.config = config or get_ml_config()

        # Create connection pool
        self.pool = ConnectionPool(
            host=self.config.storage.redis_host,
            port=self.config.storage.redis_port,
            db=self.config.storage.redis_db,
            decode_responses=False,  # We'll handle binary data (pickled embeddings)
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        self.client: Optional[redis.Redis] = None
        self._initialized = True

        logger.info(
            f"Redis cache initialized: {self.config.storage.redis_host}:"
            f"{self.config.storage.redis_port} (db={self.config.storage.redis_db})"
        )

    def _get_client(self) -> redis.Redis:
        """
        Get Redis client (lazy initialization).

        Returns:
            Redis client

        Raises:
            RedisCacheError: If connection fails
        """
        if self.client is None:
            try:
                self.client = redis.Redis(connection_pool=self.pool)
                # Test connection
                self.client.ping()
                logger.info("Redis connection established")
            except redis.ConnectionError as e:
                raise RedisCacheError(f"Failed to connect to Redis: {e}")

        return self.client

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            client = self._get_client()
            data = client.get(key)

            if data is None:
                return None

            # Unpickle the data
            return pickle.loads(data)

        except redis.RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error deserializing cached data for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be pickled)
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()

            # Pickle the value
            data = pickle.dumps(value)

            if ttl is not None:
                client.setex(key, ttl, data)
            else:
                client.set(key, data)

            return True

        except redis.RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error serializing data for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            client = self._get_client()
            result = client.delete(key)
            return result > 0

        except redis.RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = self._get_client()
            keys = client.keys(pattern)

            if len(keys) == 0:
                return 0

            return client.delete(*keys)

        except redis.RedisError as e:
            logger.error(f"Redis DELETE PATTERN error for pattern '{pattern}': {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            client = self._get_client()
            return client.exists(key) > 0

        except redis.RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict mapping keys to values (missing keys are omitted)
        """
        if not keys:
            return {}

        try:
            client = self._get_client()
            values = client.mget(keys)

            result = {}
            for key, data in zip(keys, values):
                if data is not None:
                    try:
                        result[key] = pickle.loads(data)
                    except Exception as e:
                        logger.error(f"Error deserializing cached data for key '{key}': {e}")

            return result

        except redis.RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            return {}

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in cache.

        Args:
            mapping: Dict mapping keys to values
            ttl: Time-to-live in seconds (applied to all keys)

        Returns:
            True if successful, False otherwise
        """
        if not mapping:
            return True

        try:
            client = self._get_client()

            # Pickle all values
            pickled_mapping = {}
            for key, value in mapping.items():
                try:
                    pickled_mapping[key] = pickle.dumps(value)
                except Exception as e:
                    logger.error(f"Error serializing data for key '{key}': {e}")

            if not pickled_mapping:
                return False

            # Use pipeline for atomic operation
            pipe = client.pipeline()

            if ttl is not None:
                # Set with expiration
                for key, data in pickled_mapping.items():
                    pipe.setex(key, ttl, data)
            else:
                # Set without expiration
                pipe.mset(pickled_mapping)

            pipe.execute()

            return True

        except redis.RedisError as e:
            logger.error(f"Redis MSET error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None on error
        """
        try:
            client = self._get_client()
            return client.incrby(key, amount)

        except redis.RedisError as e:
            logger.error(f"Redis INCRBY error for key '{key}': {e}")
            return None

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining time-to-live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist, None on error
        """
        try:
            client = self._get_client()
            return client.ttl(key)

        except redis.RedisError as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return None

    def ping(self) -> bool:
        """
        Test Redis connection.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            client = self._get_client()
            return client.ping()

        except redis.RedisError as e:
            logger.error(f"Redis PING error: {e}")
            return False

    def flush_db(self) -> bool:
        """
        Flush all keys in the current database.

        WARNING: This deletes all data in the database!

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            client.flushdb()
            logger.warning("Redis database flushed")
            return True

        except redis.RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """
        Get Redis server info.

        Returns:
            Dict with server information
        """
        try:
            client = self._get_client()
            return client.info()

        except redis.RedisError as e:
            logger.error(f"Redis INFO error: {e}")
            return {}


# Global instance accessor
_cache_instance: Optional[RedisCache] = None


def get_redis_cache(config: Optional[MLConfig] = None) -> RedisCache:
    """Get global Redis cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(config=config)
    return _cache_instance
