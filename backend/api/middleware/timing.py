"""
Request Timing Middleware
Tracks request latency and performance metrics.
"""

import logging
import time
from typing import Callable, Dict, List
from collections import deque
from threading import Lock
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LatencyTracker:
    """
    Tracks request latency statistics.

    Maintains a rolling window of recent request latencies
    and calculates percentiles.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize latency tracker.

        Args:
            window_size: Number of recent requests to track
        """
        self.window_size = window_size
        self.latencies: deque = deque(maxlen=window_size)
        self.lock = Lock()

    def record(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        with self.lock:
            self.latencies.append(latency_ms)

    def get_stats(self) -> Dict[str, float]:
        """
        Get latency statistics.

        Returns:
            Dict with p50, p95, p99, mean, min, max
        """
        with self.lock:
            if not self.latencies:
                return {
                    "count": 0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                    "mean": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                }

            sorted_latencies = sorted(self.latencies)
            count = len(sorted_latencies)

            return {
                "count": count,
                "p50": self._percentile(sorted_latencies, 50),
                "p95": self._percentile(sorted_latencies, 95),
                "p99": self._percentile(sorted_latencies, 99),
                "mean": sum(sorted_latencies) / count,
                "min": sorted_latencies[0],
                "max": sorted_latencies[-1],
            }

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


# Global latency tracker
_latency_tracker = LatencyTracker()


def get_latency_tracker() -> LatencyTracker:
    """Get global latency tracker."""
    return _latency_tracker


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request timing and performance.

    Records latency for each request and provides statistics.
    """

    def __init__(self, app, tracker: LatencyTracker = None):
        """
        Initialize timing middleware.

        Args:
            app: FastAPI application
            tracker: Latency tracker (uses global if not provided)
        """
        super().__init__(app)
        self.tracker = tracker or get_latency_tracker()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track timing."""
        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Record latency
        self.tracker.record(duration_ms)

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Log slow requests (> 300ms)
        if duration_ms > 300:
            logger.warning(
                f"Slow request detected",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )

        return response
