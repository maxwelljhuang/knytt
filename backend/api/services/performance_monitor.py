"""
Performance Monitoring Service
Tracks API performance metrics, slow queries, and optimization opportunities.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceThreshold(Enum):
    """Performance threshold levels."""

    EXCELLENT = 50  # < 50ms
    GOOD = 100  # < 100ms
    ACCEPTABLE = 150  # < 150ms (target p95)
    SLOW = 300  # < 300ms
    CRITICAL = 1000  # < 1000ms


@dataclass
class OperationMetric:
    """Single operation performance metric."""

    operation: str
    duration_ms: float
    timestamp: datetime
    endpoint: str
    user_id: Optional[int] = None
    query: Optional[str] = None
    result_count: Optional[int] = None
    cached: bool = False
    error: Optional[str] = None


class PerformanceMonitor:
    """
    Performance monitoring service.

    Tracks operation metrics, identifies bottlenecks, and logs slow queries.
    """

    def __init__(self, max_history: int = 10000):
        """
        Initialize performance monitor.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history

        # Metric storage (using deque for efficient FIFO)
        self.metrics: deque = deque(maxlen=max_history)

        # Per-operation stats
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)

        # Slow query tracking
        self.slow_queries: deque = deque(maxlen=1000)
        self.slow_threshold_ms = 300

        # Error tracking
        self.errors: deque = deque(maxlen=1000)

        # Endpoint stats
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time_ms": 0,
                "errors": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
        )

        logger.info("Performance monitor initialized")

    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        endpoint: str,
        user_id: Optional[int] = None,
        query: Optional[str] = None,
        result_count: Optional[int] = None,
        cached: bool = False,
        error: Optional[str] = None,
    ):
        """
        Record an operation metric.

        Args:
            operation: Operation name (e.g., "search", "recommend", "encode_query")
            duration_ms: Duration in milliseconds
            endpoint: API endpoint
            user_id: User ID (if applicable)
            query: Search query (if applicable)
            result_count: Number of results returned
            cached: Whether result was cached
            error: Error message (if failed)
        """
        metric = OperationMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            endpoint=endpoint,
            user_id=user_id,
            query=query,
            result_count=result_count,
            cached=cached,
            error=error,
        )

        # Store metric
        self.metrics.append(metric)

        # Update operation stats
        self.operation_stats[operation].append(duration_ms)

        # Update endpoint stats
        self.endpoint_stats[endpoint]["count"] += 1
        self.endpoint_stats[endpoint]["total_time_ms"] += duration_ms

        if error:
            self.endpoint_stats[endpoint]["errors"] += 1
            self.errors.append(metric)

        if cached:
            self.endpoint_stats[endpoint]["cache_hits"] += 1
        else:
            self.endpoint_stats[endpoint]["cache_misses"] += 1

        # Track slow queries
        if duration_ms > self.slow_threshold_ms and not error:
            self.slow_queries.append(metric)
            logger.warning(
                f"Slow operation: {operation} took {duration_ms:.2f}ms "
                f"(endpoint={endpoint}, query={query})"
            )

    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """
        Get statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Stats dict with p50, p95, p99, mean, min, max
        """
        durations = self.operation_stats.get(operation, [])

        if not durations:
            return {
                "count": 0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
            }

        sorted_durations = sorted(durations)
        count = len(sorted_durations)

        return {
            "count": count,
            "p50": sorted_durations[int(count * 0.5)],
            "p95": sorted_durations[int(count * 0.95)],
            "p99": sorted_durations[int(count * 0.99)],
            "mean": sum(sorted_durations) / count,
            "min": sorted_durations[0],
            "max": sorted_durations[-1],
        }

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for endpoint(s).

        Args:
            endpoint: Specific endpoint or None for all

        Returns:
            Endpoint statistics
        """
        if endpoint:
            stats = self.endpoint_stats.get(endpoint, {})
            if stats.get("count", 0) > 0:
                stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
                stats["cache_hit_rate"] = (
                    stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"]) * 100
                    if (stats["cache_hits"] + stats["cache_misses"]) > 0
                    else 0
                )
            return stats

        # Return all endpoints
        all_stats = {}
        for ep, stats in self.endpoint_stats.items():
            ep_stats = stats.copy()
            if ep_stats["count"] > 0:
                ep_stats["avg_time_ms"] = ep_stats["total_time_ms"] / ep_stats["count"]
                ep_stats["cache_hit_rate"] = (
                    ep_stats["cache_hits"]
                    / (ep_stats["cache_hits"] + ep_stats["cache_misses"])
                    * 100
                    if (ep_stats["cache_hits"] + ep_stats["cache_misses"]) > 0
                    else 0
                )
            all_stats[ep] = ep_stats

        return all_stats

    def get_slow_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent slow queries.

        Args:
            limit: Maximum number to return

        Returns:
            List of slow query metrics
        """
        slow = list(self.slow_queries)[-limit:]
        return [asdict(m) for m in slow]

    def get_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent errors.

        Args:
            limit: Maximum number to return

        Returns:
            List of error metrics
        """
        errors = list(self.errors)[-limit:]
        return [asdict(m) for m in errors]

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.

        Returns:
            Performance summary with stats and health indicators
        """
        # Calculate overall stats
        all_durations = []
        for durations in self.operation_stats.values():
            all_durations.extend(durations)

        if all_durations:
            sorted_all = sorted(all_durations)
            count = len(sorted_all)
            overall_stats = {
                "total_operations": count,
                "p50_ms": sorted_all[int(count * 0.5)],
                "p95_ms": sorted_all[int(count * 0.95)],
                "p99_ms": sorted_all[int(count * 0.99)],
                "mean_ms": sum(sorted_all) / count,
                "min_ms": sorted_all[0],
                "max_ms": sorted_all[-1],
            }
        else:
            overall_stats = {
                "total_operations": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "mean_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
            }

        # Per-operation breakdown
        operation_breakdown = {}
        for op in self.operation_stats.keys():
            operation_breakdown[op] = self.get_operation_stats(op)

        # Health assessment
        p95 = overall_stats["p95_ms"]
        if p95 < PerformanceThreshold.EXCELLENT.value:
            health = "excellent"
        elif p95 < PerformanceThreshold.GOOD.value:
            health = "good"
        elif p95 < PerformanceThreshold.ACCEPTABLE.value:
            health = "acceptable"
        elif p95 < PerformanceThreshold.SLOW.value:
            health = "slow"
        else:
            health = "critical"

        return {
            "overall": overall_stats,
            "health": health,
            "target_p95_ms": PerformanceThreshold.ACCEPTABLE.value,
            "meeting_target": p95 < PerformanceThreshold.ACCEPTABLE.value,
            "operations": operation_breakdown,
            "endpoints": self.get_endpoint_stats(),
            "slow_query_count": len(self.slow_queries),
            "error_count": len(self.errors),
            "metrics_tracked": len(self.metrics),
        }

    def get_optimization_recommendations(self) -> List[Dict[str, str]]:
        """
        Get performance optimization recommendations.

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check endpoint performance
        for endpoint, stats in self.endpoint_stats.items():
            if stats["count"] == 0:
                continue

            avg_time = stats["total_time_ms"] / stats["count"]
            cache_hit_rate = (
                stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"]) * 100
                if (stats["cache_hits"] + stats["cache_misses"]) > 0
                else 0
            )

            # Slow endpoint
            if avg_time > PerformanceThreshold.ACCEPTABLE.value:
                recommendations.append(
                    {
                        "priority": "high",
                        "endpoint": endpoint,
                        "issue": f"Slow average response time ({avg_time:.0f}ms)",
                        "recommendation": "Optimize query, add indexes, or increase cache TTL",
                    }
                )

            # Low cache hit rate
            if cache_hit_rate < 50 and stats["cache_hits"] + stats["cache_misses"] > 100:
                recommendations.append(
                    {
                        "priority": "medium",
                        "endpoint": endpoint,
                        "issue": f"Low cache hit rate ({cache_hit_rate:.1f}%)",
                        "recommendation": "Increase cache TTL or implement cache warming",
                    }
                )

            # High error rate
            error_rate = stats["errors"] / stats["count"] * 100
            if error_rate > 5:
                recommendations.append(
                    {
                        "priority": "critical",
                        "endpoint": endpoint,
                        "issue": f"High error rate ({error_rate:.1f}%)",
                        "recommendation": "Investigate and fix errors immediately",
                    }
                )

        # Check operation performance
        for operation, durations in self.operation_stats.items():
            if len(durations) < 10:
                continue

            stats = self.get_operation_stats(operation)

            if stats["p95"] > PerformanceThreshold.ACCEPTABLE.value:
                recommendations.append(
                    {
                        "priority": "high",
                        "operation": operation,
                        "issue": f"Slow p95 latency ({stats['p95']:.0f}ms)",
                        "recommendation": "Profile and optimize this operation",
                    }
                )

        return recommendations

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.operation_stats.clear()
        self.slow_queries.clear()
        self.errors.clear()
        self.endpoint_stats.clear()
        logger.info("Performance metrics reset")


# Global singleton
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
