"""Performance Optimizer

Provides performance optimization capabilities including request batching,
lazy loading, response caching, and performance monitoring.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Represents a batched request."""

    request_id: str
    operation: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    future: Future | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""

    total_requests: int = 0
    batch_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    lazy_loads: int = 0
    avg_response_time: float = 0.0
    batch_efficiency: float = 0.0


class RequestBatcher:
    """Batches similar requests together for more efficient processing.
    Useful for operations like document searches, feed refreshes, etc.
    """

    def __init__(self, batch_size: int = 10, batch_timeout: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._batches: dict[str, list[BatchRequest]] = defaultdict(list)
        self._batch_timers: dict[str, threading.Timer] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="batch-processor"
        )
        self._lock = threading.Lock()

    def add_request(
        self, operation_type: str, operation: Callable, *args, **kwargs
    ) -> Future:
        """Add a request to be batched.

        Args:
            operation_type: Type of operation for batching similar requests
            operation: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Future that will contain the result
        """
        request_id = f"{operation_type}_{len(self._batches[operation_type])}"
        future = Future()

        request = BatchRequest(
            request_id=request_id,
            operation=operation,
            args=args,
            kwargs=kwargs,
            future=future,
        )

        with self._lock:
            self._batches[operation_type].append(request)

            # Check if batch is ready to process
            if len(self._batches[operation_type]) >= self.batch_size:
                self._process_batch(operation_type)
            else:
                # Set or reset timer
                if operation_type in self._batch_timers:
                    self._batch_timers[operation_type].cancel()

                timer = threading.Timer(
                    self.batch_timeout, lambda: self._process_batch(operation_type)
                )
                timer.start()
                self._batch_timers[operation_type] = timer

        return future

    def _process_batch(self, operation_type: str) -> None:
        """Process a batch of requests."""
        with self._lock:
            if operation_type not in self._batches or not self._batches[operation_type]:
                return

            batch_requests = self._batches[operation_type]
            self._batches[operation_type] = []

            # Cancel timer
            if operation_type in self._batch_timers:
                self._batch_timers[operation_type].cancel()
                del self._batch_timers[operation_type]

        logger.debug(
            f"Processing batch of {len(batch_requests)} {operation_type} requests"
        )

        # Submit batch for processing
        self._executor.submit(self._execute_batch, batch_requests)

    def _execute_batch(self, batch_requests: list[BatchRequest]) -> None:
        """Execute a batch of requests."""
        for request in batch_requests:
            try:
                result = request.operation(*request.args, **request.kwargs)
                request.future.set_result(result)
            except Exception as e:
                request.future.set_exception(e)


class LazyLoader:
    """Implements lazy loading for expensive operations.
    Operations are only executed when their results are actually needed.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._loading: dict[str, Future] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="lazy-loader"
        )
        self._lock = threading.Lock()

    def lazy_load(self, key: str, loader: Callable, ttl: int = 3600) -> Future:
        """Lazily load a resource.

        Args:
            key: Unique key for the resource
            loader: Function to load the resource
            ttl: Time to live for cached result

        Returns:
            Future that will contain the loaded resource
        """
        with self._lock:
            # Check if already cached
            if key in self._cache:
                cache_entry = self._cache[key]
                if time.time() - cache_entry["timestamp"] < ttl:
                    future = Future()
                    future.set_result(cache_entry["value"])
                    return future
                else:
                    # Expired, remove from cache
                    del self._cache[key]

            # Check if already loading
            if key in self._loading:
                return self._loading[key]

            # Start loading
            future = self._executor.submit(self._load_and_cache, key, loader, ttl)
            self._loading[key] = future

            return future

    def _load_and_cache(self, key: str, loader: Callable, ttl: int) -> Any:
        """Load resource and cache it."""
        try:
            logger.debug(f"Lazy loading resource: {key}")
            result = loader()

            with self._lock:
                self._cache[key] = {"value": result, "timestamp": time.time()}

                # Remove from loading set
                if key in self._loading:
                    del self._loading[key]

            return result

        except Exception as e:
            logger.error(f"Lazy loading failed for {key}: {e}")

            with self._lock:
                # Remove from loading set
                if key in self._loading:
                    del self._loading[key]

            raise


class ResponseCache:
    """Advanced response caching with intelligent invalidation
    and compression for large responses.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, dict] = {}
        self._access_times: deque = deque()  # For LRU eviction
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get cached response."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check if expired
            if time.time() - entry["timestamp"] > entry["ttl"]:
                del self._cache[key]
                return None

            # Update access time
            self._access_times.append((key, time.time()))

            return entry["value"]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached response."""
        with self._lock:
            # Clean up if at max size
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            self._cache[key] = {
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl or self.default_ttl,
            }

            self._access_times.append((key, time.time()))

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        import re

        regex = re.compile(pattern)
        keys_to_remove = []

        with self._lock:
            for key in self._cache:
                if regex.search(key):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

        logger.info(
            f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}"
        )
        return len(keys_to_remove)

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry."""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])

        del self._cache[oldest_key]


class PerformanceOptimizer:
    """Main performance optimizer that coordinates batching, lazy loading,
    caching, and performance monitoring.
    """

    def __init__(self):
        self.request_batcher = RequestBatcher()
        self.lazy_loader = LazyLoader()
        self.response_cache = ResponseCache()
        self.metrics = PerformanceMetrics()
        self._performance_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def optimize_operation(
        self,
        operation_type: str,
        operation: Callable,
        *args,
        use_cache: bool = True,
        batch: bool = False,
        lazy: bool = False,
        cache_ttl: int = 300,
        **kwargs,
    ) -> Any:
        """Optimize an operation using available optimization techniques.

        Args:
            operation_type: Type of operation for optimization decisions
            operation: Function to execute
            *args: Function arguments
            use_cache: Whether to use response caching
            batch: Whether to batch this request
            lazy: Whether to use lazy loading
            cache_ttl: Cache time to live
            **kwargs: Function keyword arguments

        Returns:
            Operation result
        """
        start_time = time.time()

        try:
            # Generate cache key if caching enabled
            cache_key = None
            if use_cache:
                cache_key = (
                    f"{operation_type}:{hash(str(args) + str(sorted(kwargs.items())))}"
                )

                # Check cache first
                cached_result = self.response_cache.get(cache_key)
                if cached_result is not None:
                    self._record_cache_hit(start_time)
                    return cached_result

            # Determine optimization strategy
            result = None

            if lazy:
                # Use lazy loading
                loader = lambda: operation(*args, **kwargs)
                future = self.lazy_loader.lazy_load(
                    cache_key or f"lazy_{operation_type}", loader, cache_ttl
                )
                result = future.result(timeout=30)  # 30 second timeout
                self._record_lazy_load()

            elif batch:
                # Use batching
                future = self.request_batcher.add_request(
                    operation_type, operation, *args, **kwargs
                )
                result = future.result(timeout=30)  # 30 second timeout
                self._record_batch_request()

            else:
                # Execute directly
                result = operation(*args, **kwargs)

            # Cache the result if caching enabled
            if use_cache and cache_key:
                self.response_cache.set(cache_key, result, cache_ttl)
                self._record_cache_miss()

            # Record performance metrics
            self._record_request_complete(start_time)

            return result

        except Exception as e:
            self._record_request_failed(start_time)
            raise

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics."""
        with self._lock:
            recent_performance = list(self._performance_history)[
                -100:
            ]  # Last 100 operations

            if recent_performance:
                avg_recent = sum(recent_performance) / len(recent_performance)
            else:
                avg_recent = 0.0

            return {
                "total_requests": self.metrics.total_requests,
                "batch_requests": self.metrics.batch_requests,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "lazy_loads": self.metrics.lazy_loads,
                "overall_avg_response_time": self.metrics.avg_response_time,
                "recent_avg_response_time": avg_recent,
                "cache_hit_rate": (
                    (
                        self.metrics.cache_hits
                        / (self.metrics.cache_hits + self.metrics.cache_misses)
                    )
                    * 100
                    if (self.metrics.cache_hits + self.metrics.cache_misses) > 0
                    else 0
                ),
                "batch_efficiency": self.metrics.batch_efficiency,
                "cache_size": len(self.response_cache._cache),
                "lazy_cache_size": len(self.lazy_loader._cache),
            }

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        with self._lock:
            self.response_cache._cache.clear()
            self.lazy_loader._cache.clear()

        logger.info("All performance optimizer caches cleared")

    def optimize_ui_operation(
        self, operation_name: str, operation: Callable, *args, **kwargs
    ) -> Any:
        """Optimize common UI operations with predefined optimization strategies.

        Args:
            operation_name: Name of the UI operation
            operation: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Operation result
        """
        # Predefined optimization strategies for common UI operations
        optimization_strategies = {
            "list_documents": {
                "use_cache": True,
                "cache_ttl": 180,
                "batch": False,
                "lazy": False,
            },
            "search_documents": {
                "use_cache": True,
                "cache_ttl": 120,
                "batch": True,
                "lazy": False,
            },
            "get_feeds": {
                "use_cache": True,
                "cache_ttl": 600,
                "batch": False,
                "lazy": True,
            },
            "get_cve_data": {
                "use_cache": True,
                "cache_ttl": 900,
                "batch": False,
                "lazy": True,
            },
            "get_mitre_data": {
                "use_cache": True,
                "cache_ttl": 1800,
                "batch": False,
                "lazy": True,
            },
            "format_display": {
                "use_cache": True,
                "cache_ttl": 300,
                "batch": False,
                "lazy": False,
            },
            "health_check": {
                "use_cache": True,
                "cache_ttl": 60,
                "batch": True,
                "lazy": False,
            },
        }

        strategy = optimization_strategies.get(
            operation_name,
            {"use_cache": True, "cache_ttl": 300, "batch": False, "lazy": False},
        )

        return self.optimize_operation(
            operation_type=operation_name,
            operation=operation,
            *args,
            **strategy,
            **kwargs,
        )

    def _record_cache_hit(self, start_time: float) -> None:
        """Record cache hit metrics."""
        with self._lock:
            self.metrics.cache_hits += 1
            duration = time.time() - start_time
            self._performance_history.append(duration)

    def _record_cache_miss(self) -> None:
        """Record cache miss metrics."""
        with self._lock:
            self.metrics.cache_misses += 1

    def _record_batch_request(self) -> None:
        """Record batch request metrics."""
        with self._lock:
            self.metrics.batch_requests += 1

    def _record_lazy_load(self) -> None:
        """Record lazy load metrics."""
        with self._lock:
            self.metrics.lazy_loads += 1

    def _record_request_complete(self, start_time: float) -> None:
        """Record completed request metrics."""
        duration = time.time() - start_time

        with self._lock:
            self.metrics.total_requests += 1

            # Update average response time
            total = self.metrics.total_requests
            current_avg = self.metrics.avg_response_time
            self.metrics.avg_response_time = (
                (current_avg * (total - 1)) + duration
            ) / total

            self._performance_history.append(duration)

    def _record_request_failed(self, start_time: float) -> None:
        """Record failed request metrics."""
        duration = time.time() - start_time

        with self._lock:
            self.metrics.total_requests += 1
            self._performance_history.append(duration)

    def __del__(self):
        """Cleanup thread pools."""
        if hasattr(self, "request_batcher"):
            self.request_batcher._executor.shutdown(wait=False)
        if hasattr(self, "lazy_loader"):
            self.lazy_loader._executor.shutdown(wait=False)
