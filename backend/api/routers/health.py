"""
Health Check Endpoints
Endpoints for health checks and status monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..config import get_settings, APISettings
from ..dependencies import get_db, get_embedding_cache
from ..middleware.timing import get_latency_tracker
from ..services.cache_service import get_cache_service
from ..services.performance_monitor import get_performance_monitor
from ...ml.retrieval import get_index_manager
from ...ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Basic health check.

    Returns:
        Simple health status
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/status", status_code=status.HTTP_200_OK)
async def status_check(
    settings: APISettings = Depends(get_settings),
    db: Session = Depends(get_db),
    cache: EmbeddingCache = Depends(get_embedding_cache),
) -> Dict[str, Any]:
    """
    Detailed status check.

    Checks status of:
    - Database connection
    - Redis connection
    - FAISS index
    - Performance metrics

    Returns:
        Detailed status information
    """
    status_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "components": {},
    }

    # Check database
    try:
        db.execute("SELECT 1")
        status_info["components"]["database"] = {
            "status": "healthy",
            "url": settings.database_url.split("@")[-1],  # Hide credentials
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        status_info["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        status_info["status"] = "degraded"

    # Check Redis
    try:
        redis_healthy = cache.redis.ping()
        status_info["components"]["redis"] = {"status": "healthy" if redis_healthy else "unhealthy"}
        if not redis_healthy:
            status_info["status"] = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        status_info["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        status_info["status"] = "degraded"

    # Check FAISS index
    try:
        index_manager = get_index_manager()
        index_stats = index_manager.get_stats()

        status_info["components"]["faiss_index"] = {
            "status": index_stats.get("status", "unknown"),
            "num_vectors": index_stats.get("num_vectors", 0),
            "index_type": index_stats.get("index_type", "unknown"),
        }

        if index_stats.get("status") != "loaded":
            status_info["status"] = "degraded"

    except Exception as e:
        logger.error(f"FAISS index health check failed: {e}")
        status_info["components"]["faiss_index"] = {"status": "unhealthy", "error": str(e)}
        status_info["status"] = "degraded"

    # Get performance metrics
    try:
        tracker = get_latency_tracker()
        latency_stats = tracker.get_stats()

        status_info["performance"] = {
            "request_count": latency_stats["count"],
            "latency_p50_ms": round(latency_stats["p50"], 2),
            "latency_p95_ms": round(latency_stats["p95"], 2),
            "latency_p99_ms": round(latency_stats["p99"], 2),
            "target_p95_ms": settings.target_p95_latency_ms,
            "meets_target": latency_stats["p95"] <= settings.target_p95_latency_ms,
        }

    except Exception as e:
        logger.error(f"Performance metrics check failed: {e}")
        status_info["performance"] = {"error": str(e)}

    # Get cache statistics
    try:
        cache_stats = cache.get_cache_stats()
        status_info["cache"] = {
            "cached_products": cache_stats.get("cached_products", 0),
            "cached_users": cache_stats.get("cached_user_long_term", 0)
            + cache_stats.get("cached_user_session", 0),
            "hot_products": cache_stats.get("hot_products_tracked", 0),
        }
    except Exception as e:
        logger.error(f"Cache stats check failed: {e}")

    return status_info


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics() -> Dict[str, Any]:
    """
    Get performance metrics.

    Returns:
        Latency statistics and performance metrics
    """
    tracker = get_latency_tracker()
    stats = tracker.get_stats()

    return {
        "requests": {
            "total": stats["count"],
        },
        "latency": {
            "p50_ms": round(stats["p50"], 2),
            "p95_ms": round(stats["p95"], 2),
            "p99_ms": round(stats["p99"], 2),
            "mean_ms": round(stats["mean"], 2),
            "min_ms": round(stats["min"], 2),
            "max_ms": round(stats["max"], 2),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/cache/stats", status_code=status.HTTP_200_OK)
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Cache hit rate, operations, and performance metrics
    """
    cache_service = get_cache_service()
    stats = cache_service.get_statistics()

    return {"cache": stats, "timestamp": datetime.utcnow().isoformat()}


@router.get("/performance", status_code=status.HTTP_200_OK)
async def get_performance() -> Dict[str, Any]:
    """
    Get comprehensive performance summary.

    Returns:
        Performance metrics, health, and optimization recommendations
    """
    monitor = get_performance_monitor()
    summary = monitor.get_performance_summary()
    recommendations = monitor.get_optimization_recommendations()

    return {
        "performance": summary,
        "recommendations": recommendations,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/performance/slow-queries", status_code=status.HTTP_200_OK)
async def get_slow_queries(limit: int = 100) -> Dict[str, Any]:
    """
    Get recent slow queries.

    Args:
        limit: Maximum number of queries to return

    Returns:
        List of slow query metrics
    """
    monitor = get_performance_monitor()
    slow_queries = monitor.get_slow_queries(limit)

    return {
        "slow_queries": slow_queries,
        "count": len(slow_queries),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Kubernetes readiness probe.

    Checks if the service is ready to accept traffic.

    Returns:
        Readiness status
    """
    # Check critical dependencies
    try:
        # Check database
        db.execute("SELECT 1")

        # Check FAISS index
        index_manager = get_index_manager()
        if index_manager.index is None:
            return {"status": "not_ready", "reason": "FAISS index not loaded"}

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "reason": str(e)}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe.

    Checks if the service is alive and responsive.

    Returns:
        Liveness status
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
