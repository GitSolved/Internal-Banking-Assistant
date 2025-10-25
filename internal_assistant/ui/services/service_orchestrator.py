"""Service Orchestrator

Manages service lifecycle, health monitoring, initialization order,
and provides centralized service access for the UI layer.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .chat_service_facade import ChatServiceFacade
from .document_service_facade import DocumentServiceFacade
from .feeds_service_facade import FeedsServiceFacade
from .service_facade import ServiceFacade, ServiceHealth

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service orchestrator status."""

    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class ServiceConfig:
    """Configuration for service initialization."""

    name: str
    facade_class: type
    dependencies: list[str]
    critical: bool = True
    health_check_interval: int = 60
    max_init_retries: int = 3


class ServiceOrchestrator:
    """Orchestrates all UI services with health monitoring, dependency management,
    and graceful degradation capabilities.
    """

    def __init__(self):
        self._services: dict[str, ServiceFacade] = {}
        self._service_configs: dict[str, ServiceConfig] = {}
        self._service_health: dict[str, ServiceHealth] = {}
        self._status = ServiceStatus.INITIALIZING
        self._health_monitor_thread: threading.Thread | None = None
        self._health_monitor_running = False
        self._initialization_callbacks: list[Callable] = []
        self._metrics_collector_thread: threading.Thread | None = None
        self._metrics_running = False
        self._health_check_in_progress = threading.Event()
        self._last_health_check_time = 0.0
        self._health_check_queue_limit = 2  # Prevent pile-up
        self._health_monitor_failure_count = 0
        self._service_recovery_tracker: dict[str, dict[str, Any]] = (
            {}
        )  # Track service recovery
        self._global_metrics: dict[str, Any] = {
            "start_time": time.time(),
            "total_requests": 0,
            "failed_requests": 0,
            "service_availability": {},
            "performance_metrics": {},
        }
        self._lock = threading.Lock()

        # Register default service configurations
        self._register_default_service_configs()

    def register_service(
        self,
        name: str,
        service: Any,
        facade_class: type,
        dependencies: list[str] | None = None,
        critical: bool = True,
    ) -> None:
        """Register a service with the orchestrator.

        Args:
            name: Service name
            service: Service instance
            facade_class: Facade class for the service
            dependencies: List of service dependencies
            critical: Whether service is critical for operation
        """
        config = ServiceConfig(
            name=name,
            facade_class=facade_class,
            dependencies=dependencies or [],
            critical=critical,
        )

        self._service_configs[name] = config

        try:
            # Create service facade
            facade = facade_class(service)
            self._services[name] = facade
            self._service_health[name] = ServiceHealth.UNKNOWN

            logger.info(f"Registered service: {name}")

        except Exception as e:
            logger.error(f"Failed to register service {name}: {e}")
            if critical:
                raise

    def initialize_services(self) -> bool:
        """Initialize all services in dependency order.

        Returns:
            True if initialization successful
        """
        logger.info("Starting service initialization")
        self._status = ServiceStatus.INITIALIZING

        try:
            # Calculate initialization order
            init_order = self._calculate_initialization_order()
            logger.info(f"Service initialization order: {init_order}")

            # Initialize services in order
            failed_services = []

            for service_name in init_order:
                if service_name in self._services:
                    success = self._initialize_service(service_name)
                    if not success:
                        config = self._service_configs[service_name]
                        if config.critical:
                            failed_services.append(service_name)
                        else:
                            logger.warning(
                                f"Non-critical service {service_name} failed to initialize"
                            )

            # Check initialization results
            if failed_services:
                logger.error(
                    f"Critical services failed to initialize: {failed_services}"
                )
                self._status = ServiceStatus.FAILED
                return False

            # Start health monitoring
            self._start_health_monitoring()

            # Start metrics collection
            self._start_metrics_collection()

            # Run initialization callbacks
            for callback in self._initialization_callbacks:
                try:
                    callback(self)
                except Exception as e:
                    logger.warning(f"Initialization callback failed: {e}")

            self._status = ServiceStatus.READY
            logger.info("Service orchestrator initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            self._status = ServiceStatus.FAILED
            return False

    def get_service(self, name: str) -> ServiceFacade | None:
        """Get a service facade by name.

        Args:
            name: Service name

        Returns:
            Service facade instance or None
        """
        return self._services.get(name)

    def get_service_health(self, name: str | None = None) -> dict[str, ServiceHealth]:
        """Get health status for services.

        Args:
            name: Specific service name, or None for all services

        Returns:
            Dictionary of service health statuses
        """
        if name:
            return {name: self._service_health.get(name, ServiceHealth.UNKNOWN)}

        return self._service_health.copy()

    def get_orchestrator_status(self) -> ServiceStatus:
        """Get the overall orchestrator status."""
        return self._status

    def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics for all services with health dashboard."""
        current_time = time.time()

        metrics = {
            "orchestrator": {
                "status": self._status.value,
                "uptime": current_time - self._global_metrics["start_time"],
                "registered_services": len(self._services),
                "healthy_services": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.HEALTHY
                    ]
                ),
                "degraded_services": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.DEGRADED
                    ]
                ),
                "unhealthy_services": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.UNHEALTHY
                    ]
                ),
                "health_monitor_failures": self._health_monitor_failure_count,
                **self._global_metrics,
            },
            "services": {},
            "health_dashboard": self.get_health_status_dashboard(),
        }

        # Collect individual service metrics
        for name, facade in self._services.items():
            try:
                service_metrics = facade.get_service_info()
                metrics["services"][name] = service_metrics
            except Exception as e:
                logger.warning(f"Failed to get metrics for {name}: {e}")
                metrics["services"][name] = {"error": str(e)}

        return metrics

    def get_health_status_dashboard(self) -> dict[str, Any]:
        """Get comprehensive health status dashboard for debugging."""
        current_time = time.time()

        dashboard = {
            "timestamp": current_time,
            "overall_status": self._status.value,
            "health_check_status": {
                "last_check_time": self._last_health_check_time,
                "check_in_progress": self._health_check_in_progress.is_set(),
                "monitor_failure_count": self._health_monitor_failure_count,
                "time_since_last_check": (
                    current_time - self._last_health_check_time
                    if self._last_health_check_time > 0
                    else None
                ),
            },
            "service_summary": {
                "total": len(self._services),
                "healthy": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.HEALTHY
                    ]
                ),
                "degraded": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.DEGRADED
                    ]
                ),
                "unhealthy": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.UNHEALTHY
                    ]
                ),
                "unknown": len(
                    [
                        h
                        for h in self._service_health.values()
                        if h == ServiceHealth.UNKNOWN
                    ]
                ),
            },
            "service_details": {},
            "recovery_tracking": self.get_service_recovery_info(),
        }

        # Add detailed service information
        for service_name, health in self._service_health.items():
            config = self._service_configs.get(service_name, {})
            facade = self._services.get(service_name)

            service_detail = {
                "health": health.value,
                "critical": getattr(config, "critical", False),
                "dependencies": getattr(config, "dependencies", []),
            }

            # Add circuit breaker status if available
            if facade and hasattr(facade, "_circuit_breaker"):
                cb = facade._circuit_breaker
                service_detail["circuit_breaker"] = {
                    "is_open": cb.is_open,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time,
                }

            dashboard["service_details"][service_name] = service_detail

        return dashboard

    def perform_health_checks(self) -> dict[str, ServiceHealth]:
        """Perform health checks on all services with queuing prevention and graceful degradation.

        Returns:
            Dictionary of service health results
        """
        current_time = time.time()

        # Prevent health check pile-up
        if self._health_check_in_progress.is_set():
            logger.debug("Health check already in progress, skipping")
            return self._service_health.copy()

        # Rate limiting - prevent too frequent health checks
        if (
            current_time - self._last_health_check_time < 30
        ):  # Min 30 seconds between checks
            logger.debug("Health check rate limited, using cached results")
            return self._service_health.copy()

        self._health_check_in_progress.set()
        self._last_health_check_time = current_time

        try:
            logger.debug("Performing health checks on all services")
            health_results = {}

            # Prioritize critical services first
            critical_services = [
                name
                for name, config in self._service_configs.items()
                if config.critical
            ]
            non_critical_services = [
                name
                for name, config in self._service_configs.items()
                if not config.critical
            ]

            # Check critical services with higher timeout
            for service_name in critical_services:
                if service_name in self._services:
                    health_results[service_name] = self._check_single_service(
                        service_name, timeout=15
                    )

            # Check non-critical services with lower timeout and graceful degradation
            with ThreadPoolExecutor(
                max_workers=2, thread_name_prefix="health-check-noncritical"
            ) as executor:
                futures = {
                    executor.submit(self._check_single_service, name, 8): name
                    for name in non_critical_services
                    if name in self._services
                }

                for future in as_completed(futures, timeout=20):
                    service_name = futures[future]
                    try:
                        health_results[service_name] = future.result()
                    except Exception as e:
                        logger.warning(
                            f"Non-critical service health check failed: {service_name}: {e}"
                        )
                        health_results[service_name] = (
                            ServiceHealth.DEGRADED
                        )  # Graceful degradation
                        self._service_health[service_name] = ServiceHealth.DEGRADED

            # Update stored health status
            for service_name, health in health_results.items():
                self._service_health[service_name] = health

            # Update overall status with graceful degradation logic
            self._update_overall_status()

            return health_results

        finally:
            self._health_check_in_progress.clear()

    def _check_single_service(
        self, service_name: str, timeout: int = 10
    ) -> ServiceHealth:
        """Check health of a single service with timeout."""
        facade = self._services.get(service_name)
        if not facade:
            return ServiceHealth.UNKNOWN

        try:
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"health-{service_name}"
            ) as executor:
                future = executor.submit(facade.health_check)
                health = future.result(timeout=timeout)
                return health

        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            # Graceful degradation based on service criticality
            config = self._service_configs.get(service_name)
            if config and not config.critical:
                return (
                    ServiceHealth.DEGRADED
                )  # Non-critical services degrade gracefully
            else:
                return ServiceHealth.UNHEALTHY  # Critical services marked as unhealthy

    def add_initialization_callback(self, callback: Callable) -> None:
        """Add callback to run after successful initialization."""
        self._initialization_callbacks.append(callback)

    def shutdown(self) -> None:
        """Gracefully shutdown the service orchestrator."""
        logger.info("Shutting down service orchestrator")

        # Stop monitoring threads
        self._health_monitor_running = False
        self._metrics_running = False

        if self._health_monitor_thread:
            self._health_monitor_thread.join(timeout=5)

        if self._metrics_collector_thread:
            self._metrics_collector_thread.join(timeout=5)

        # Cleanup services
        for name, facade in self._services.items():
            try:
                if hasattr(facade, "shutdown"):
                    facade.shutdown()
            except Exception as e:
                logger.warning(f"Failed to shutdown service {name}: {e}")

        logger.info("Service orchestrator shutdown complete")

    def _register_default_service_configs(self) -> None:
        """Register default service configurations."""
        self._service_configs.update(
            {
                "chat": ServiceConfig(
                    name="chat",
                    facade_class=ChatServiceFacade,
                    dependencies=[],
                    critical=True,
                ),
                "document": ServiceConfig(
                    name="document",
                    facade_class=DocumentServiceFacade,
                    dependencies=[],
                    critical=True,
                ),
                "feeds": ServiceConfig(
                    name="feeds",
                    facade_class=FeedsServiceFacade,
                    dependencies=[],
                    critical=False,
                ),
            }
        )

    def _calculate_initialization_order(self) -> list[str]:
        """Calculate service initialization order based on dependencies."""
        # Topological sort for dependency resolution
        visited = set()
        temp_mark = set()
        result = []

        def visit(service_name: str):
            if service_name in temp_mark:
                raise ValueError(f"Circular dependency detected: {service_name}")

            if service_name in visited:
                return

            temp_mark.add(service_name)

            # Visit dependencies first
            config = self._service_configs.get(service_name)
            if config:
                for dep in config.dependencies:
                    if dep in self._service_configs:
                        visit(dep)

            temp_mark.remove(service_name)
            visited.add(service_name)
            result.append(service_name)

        # Visit all registered services
        for service_name in self._service_configs:
            if service_name not in visited:
                visit(service_name)

        return result

    def _initialize_service(self, service_name: str) -> bool:
        """Initialize a single service with retry logic."""
        config = self._service_configs[service_name]
        facade = self._services.get(service_name)

        if not facade:
            logger.error(f"No facade found for service {service_name}")
            return False

        # FAST INIT: Skip health checks during initialization to avoid blocking
        # Health monitoring thread will check services after UI is mounted
        logger.info(
            f"Initializing service {service_name} (fast init - health check deferred)"
        )

        try:
            # Just verify the service exists and is accessible
            if facade.service is not None:
                logger.info(
                    f"Service {service_name} initialized successfully (health check deferred to monitoring thread)"
                )
                return True
            else:
                logger.warning(
                    f"Service {service_name} has no underlying service object"
                )
                return False
        except Exception as e:
            logger.error(f"Service {service_name} initialization failed: {e}")
            return False

    def _start_health_monitoring(self) -> None:
        """Start background health monitoring thread."""
        if self._health_monitor_thread and self._health_monitor_thread.is_alive():
            return

        self._health_monitor_running = True
        self._health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop, name="service-health-monitor", daemon=True
        )
        self._health_monitor_thread.start()
        logger.info("Started health monitoring thread")

    def _health_monitor_loop(self) -> None:
        """Enhanced health monitoring loop with exponential backoff and recovery detection."""
        base_interval = 60  # Base interval: 60 seconds

        while self._health_monitor_running:
            try:
                # Perform health checks
                health_results = self.perform_health_checks()

                # Track service recovery
                self._track_service_recovery(health_results)

                # Reset failure count on successful health check
                self._health_monitor_failure_count = 0

                # Normal interval between successful checks
                time.sleep(base_interval)

            except Exception as e:
                self._health_monitor_failure_count += 1

                # Calculate exponential backoff (cap at 10 minutes)
                backoff_interval = min(
                    base_interval * (2 ** (self._health_monitor_failure_count - 1)), 600
                )

                logger.error(
                    f"Health monitoring error (attempt {self._health_monitor_failure_count}): {e}"
                )
                logger.info(f"Retrying health monitoring in {backoff_interval} seconds")

                time.sleep(backoff_interval)

    def _track_service_recovery(self, health_results: dict[str, ServiceHealth]) -> None:
        """Track service recovery and log significant state changes."""
        current_time = time.time()

        for service_name, current_health in health_results.items():
            if service_name not in self._service_recovery_tracker:
                # Initialize tracking for new services
                self._service_recovery_tracker[service_name] = {
                    "previous_health": ServiceHealth.UNKNOWN,
                    "state_change_time": current_time,
                    "failure_start_time": None,
                    "consecutive_failures": 0,
                    "recovery_count": 0,
                }

            tracker = self._service_recovery_tracker[service_name]
            previous_health = tracker["previous_health"]

            # Detect state changes
            if current_health != previous_health:
                tracker["state_change_time"] = current_time

                # Log significant state changes
                if current_health == ServiceHealth.HEALTHY and previous_health in [
                    ServiceHealth.UNHEALTHY,
                    ServiceHealth.DEGRADED,
                ]:
                    # Service recovered
                    if tracker["failure_start_time"]:
                        downtime = current_time - tracker["failure_start_time"]
                        tracker["recovery_count"] += 1
                        logger.info(
                            f"🟢 Service {service_name} recovered after {downtime:.1f}s downtime (recovery #{tracker['recovery_count']})"
                        )
                        tracker["failure_start_time"] = None
                        tracker["consecutive_failures"] = 0

                elif (
                    current_health in [ServiceHealth.UNHEALTHY, ServiceHealth.DEGRADED]
                    and previous_health == ServiceHealth.HEALTHY
                ):
                    # Service failed
                    tracker["failure_start_time"] = current_time
                    tracker["consecutive_failures"] = 1
                    logger.warning(
                        f"🔴 Service {service_name} failed: {previous_health.value} → {current_health.value}"
                    )

                elif current_health in [
                    ServiceHealth.UNHEALTHY,
                    ServiceHealth.DEGRADED,
                ]:
                    # Consecutive failure
                    tracker["consecutive_failures"] += 1
                    if (
                        tracker["consecutive_failures"] % 5 == 0
                    ):  # Log every 5th consecutive failure
                        logger.warning(
                            f"🔴 Service {service_name} still failing ({tracker['consecutive_failures']} consecutive failures)"
                        )

                tracker["previous_health"] = current_health

    def get_service_recovery_info(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive service recovery information for debugging."""
        recovery_info = {}
        current_time = time.time()

        for service_name, tracker in self._service_recovery_tracker.items():
            current_health = self._service_health.get(
                service_name, ServiceHealth.UNKNOWN
            )

            info = {
                "current_health": current_health.value,
                "previous_health": tracker["previous_health"].value,
                "time_in_current_state": current_time - tracker["state_change_time"],
                "recovery_count": tracker["recovery_count"],
                "consecutive_failures": tracker["consecutive_failures"],
            }

            # Add downtime info if currently failing
            if tracker["failure_start_time"]:
                info["current_downtime"] = current_time - tracker["failure_start_time"]

            recovery_info[service_name] = info

        return recovery_info

    def _start_metrics_collection(self) -> None:
        """Start background metrics collection thread."""
        if self._metrics_collector_thread and self._metrics_collector_thread.is_alive():
            return

        self._metrics_running = True
        self._metrics_collector_thread = threading.Thread(
            target=self._metrics_collection_loop,
            name="service-metrics-collector",
            daemon=True,
        )
        self._metrics_collector_thread.start()
        logger.info("Started metrics collection thread")

    def _metrics_collection_loop(self) -> None:
        """Metrics collection loop."""
        while self._metrics_running:
            try:
                self._collect_global_metrics()
                time.sleep(300)  # Collect every 5 minutes

            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(60)  # Retry after 1 minute on error

    def _collect_global_metrics(self) -> None:
        """Collect global orchestrator metrics."""
        with self._lock:
            # Update service availability metrics
            total_services = len(self._services)
            healthy_services = len(
                [h for h in self._service_health.values() if h == ServiceHealth.HEALTHY]
            )

            self._global_metrics["service_availability"] = {
                "total": total_services,
                "healthy": healthy_services,
                "availability_percentage": (
                    (healthy_services / total_services * 100)
                    if total_services > 0
                    else 0
                ),
            }

            # Collect aggregated performance metrics
            total_requests = 0
            total_failures = 0
            avg_response_times = []

            for facade in self._services.values():
                try:
                    metrics = facade.get_metrics()
                    total_requests += metrics.get("total_requests", 0)
                    total_failures += metrics.get("failed_requests", 0)
                    avg_response = metrics.get("avg_response_time", 0)
                    if avg_response > 0:
                        avg_response_times.append(avg_response)
                except Exception:
                    continue

            self._global_metrics["total_requests"] = total_requests
            self._global_metrics["failed_requests"] = total_failures
            self._global_metrics["performance_metrics"] = {
                "overall_avg_response_time": (
                    sum(avg_response_times) / len(avg_response_times)
                    if avg_response_times
                    else 0
                ),
                "success_rate": (
                    ((total_requests - total_failures) / total_requests * 100)
                    if total_requests > 0
                    else 100
                ),
            }

    def _update_overall_status(self) -> None:
        """Update overall orchestrator status based on service health."""
        healthy_count = len(
            [h for h in self._service_health.values() if h == ServiceHealth.HEALTHY]
        )
        total_services = len(self._services)
        critical_services = [
            name for name, config in self._service_configs.items() if config.critical
        ]
        critical_healthy = len(
            [
                name
                for name in critical_services
                if self._service_health.get(name) == ServiceHealth.HEALTHY
            ]
        )

        if critical_healthy == len(critical_services):
            if healthy_count == total_services:
                self._status = ServiceStatus.READY
            else:
                self._status = ServiceStatus.DEGRADED
        else:
            self._status = ServiceStatus.FAILED
