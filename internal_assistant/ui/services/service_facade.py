"""
Base Service Facade

Provides the base abstraction layer for all UI service interactions.
Implements error handling, retry logic, circuit breaker patterns, and caching.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from functools import wraps
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceHealth(Enum):
    """Service health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""

    failure_count: int = 0
    last_failure_time: float = 0
    failure_threshold: int = 5
    recovery_timeout: int = 60
    is_open: bool = False


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    value: Any
    timestamp: float
    ttl: int

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class ServiceFacade(ABC, Generic[T]):
    """
    Base facade for all UI service interactions.

    Provides:
    - Error handling with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Response caching with TTL
    - Health monitoring and metrics
    - Request batching capabilities
    """

    def __init__(self, service: T, service_name: str):
        self.service = service
        self.service_name = service_name
        self._health = ServiceHealth.UNKNOWN
        self._circuit_breaker = CircuitBreakerState()
        self._cache: Dict[str, CacheEntry] = {}
        self._metrics: Dict[str, Any] = {
            "total_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0,
            "last_health_check": 0,
        }
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix=f"{service_name}-pool"
        )
        self._lock = threading.Lock()

    @staticmethod
    def with_retry(max_retries: int = 3, base_delay: float = 1.0):
        """Decorator for retrying service calls with exponential backoff."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        # Check circuit breaker
                        if self._is_circuit_breaker_open():
                            raise Exception(
                                f"Circuit breaker open for {self.service_name}"
                            )

                        # Execute the function
                        start_time = time.time()
                        result = func(self, *args, **kwargs)
                        duration = time.time() - start_time

                        # Update metrics on success
                        self._update_success_metrics(duration)
                        self._reset_circuit_breaker()

                        return result

                    except Exception as e:
                        last_exception = e
                        self._update_failure_metrics()

                        if attempt < max_retries:
                            delay = base_delay * (2**attempt)
                            logger.warning(
                                f"Service call failed, retrying in {delay}s: {e}"
                            )
                            time.sleep(delay)
                        else:
                            logger.error(
                                f"Service call failed after {max_retries} retries: {e}"
                            )
                            self._trigger_circuit_breaker()

                raise last_exception

            return wrapper

        return decorator

    @staticmethod
    def with_cache(ttl: int = 300, key_func: Optional[Callable] = None):
        """Decorator for caching service call results."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(self, *args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

                # Check cache
                with self._lock:
                    if cache_key in self._cache:
                        entry = self._cache[cache_key]
                        if not entry.is_expired():
                            self._metrics["cache_hits"] += 1
                            logger.debug(f"Cache hit for {cache_key}")
                            return entry.value
                        else:
                            # Remove expired entry
                            del self._cache[cache_key]

                # Cache miss - execute function
                self._metrics["cache_misses"] += 1
                result = func(self, *args, **kwargs)

                # Store in cache
                with self._lock:
                    self._cache[cache_key] = CacheEntry(
                        value=result, timestamp=time.time(), ttl=ttl
                    )

                return result

            return wrapper

        return decorator

    def health_check(self) -> ServiceHealth:
        """Perform health check on the underlying service."""
        try:
            if hasattr(self.service, "health_check"):
                is_healthy = self.service.health_check()
            else:
                # Basic availability check
                is_healthy = self._basic_health_check()

            if is_healthy:
                self._health = ServiceHealth.HEALTHY
            else:
                self._health = ServiceHealth.DEGRADED

            self._metrics["last_health_check"] = time.time()
            return self._health

        except Exception as e:
            logger.error(f"Health check failed for {self.service_name}: {e}")
            self._health = ServiceHealth.UNHEALTHY
            return self._health

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        with self._lock:
            return self._metrics.copy()

    def clear_cache(self) -> None:
        """Clear the service cache."""
        with self._lock:
            self._cache.clear()
        logger.info(f"Cache cleared for {self.service_name}")

    def batch_execute(
        self, operations: list[Callable], max_workers: int = 4
    ) -> list[Any]:
        """Execute multiple operations concurrently."""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_op = {executor.submit(op): op for op in operations}

            for future in as_completed(future_to_op):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch operation failed: {e}")
                    results.append(None)

        return results

    @abstractmethod
    def _basic_health_check(self) -> bool:
        """Implement basic health check logic."""
        pass

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._circuit_breaker.is_open:
            return False

        # Check if recovery timeout has passed
        if (
            time.time() - self._circuit_breaker.last_failure_time
            > self._circuit_breaker.recovery_timeout
        ):
            self._circuit_breaker.is_open = False
            self._circuit_breaker.failure_count = 0
            logger.info(f"Circuit breaker closed for {self.service_name}")
            return False

        return True

    def _trigger_circuit_breaker(self) -> None:
        """Trigger circuit breaker."""
        self._circuit_breaker.failure_count += 1
        self._circuit_breaker.last_failure_time = time.time()

        if (
            self._circuit_breaker.failure_count
            >= self._circuit_breaker.failure_threshold
        ):
            self._circuit_breaker.is_open = True
            logger.warning(f"Circuit breaker opened for {self.service_name}")

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful call."""
        if self._circuit_breaker.failure_count > 0:
            self._circuit_breaker.failure_count = 0
            self._circuit_breaker.is_open = False

    def _update_success_metrics(self, duration: float) -> None:
        """Update metrics on successful service call."""
        with self._lock:
            self._metrics["total_requests"] += 1

            # Update average response time
            total = self._metrics["total_requests"]
            current_avg = self._metrics["avg_response_time"]
            self._metrics["avg_response_time"] = (
                (current_avg * (total - 1)) + duration
            ) / total

    def _update_failure_metrics(self) -> None:
        """Update metrics on failed service call."""
        with self._lock:
            self._metrics["total_requests"] += 1
            self._metrics["failed_requests"] += 1

    def __del__(self):
        """Cleanup thread pool executor."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
