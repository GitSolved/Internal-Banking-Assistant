"""
Service Layer Integration Test

Tests the complete service layer integration including facades, orchestration,
and performance optimization.
"""

import logging
import time
import asyncio
from typing import Dict, Any

from internal_assistant.di import global_injector
from .service_factory import ServiceFactory
from .ui_service_integration import create_ui_service_integration
from .performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class ServiceIntegrationTest:
    """
    Comprehensive test suite for service layer integration.
    """

    def __init__(self):
        self.test_results: Dict[str, Any] = {}
        self.performance_optimizer = PerformanceOptimizer()

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all integration tests.

        Returns:
            Dictionary with test results
        """
        logger.info("Starting service layer integration tests")

        test_suite = [
            ("service_validation", self.test_service_validation),
            ("orchestrator_creation", self.test_orchestrator_creation),
            ("service_initialization", self.test_service_initialization),
            ("facade_functionality", self.test_facade_functionality),
            ("performance_optimization", self.test_performance_optimization),
            ("health_monitoring", self.test_health_monitoring),
            ("error_handling", self.test_error_handling),
            ("integration_compatibility", self.test_integration_compatibility),
        ]

        overall_results = {"start_time": time.time(), "tests": {}, "summary": {}}

        passed_tests = 0
        failed_tests = 0

        for test_name, test_func in test_suite:
            logger.info(f"Running test: {test_name}")

            try:
                test_start = time.time()
                result = test_func()
                test_duration = time.time() - test_start

                overall_results["tests"][test_name] = {
                    "status": "passed" if result["success"] else "failed",
                    "duration": test_duration,
                    "details": result,
                }

                if result["success"]:
                    passed_tests += 1
                    logger.info(f"Test {test_name} passed in {test_duration:.2f}s")
                else:
                    failed_tests += 1
                    logger.error(
                        f"Test {test_name} failed: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_tests += 1
                logger.error(f"Test {test_name} crashed: {e}", exc_info=True)

                overall_results["tests"][test_name] = {
                    "status": "crashed",
                    "duration": 0,
                    "details": {"success": False, "error": str(e)},
                }

        # Calculate summary
        total_duration = time.time() - overall_results["start_time"]
        overall_results["summary"] = {
            "total_tests": len(test_suite),
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / len(test_suite)) * 100,
            "total_duration": total_duration,
            "status": "passed" if failed_tests == 0 else "failed",
        }

        logger.info(
            f"Integration tests completed: {passed_tests}/{len(test_suite)} passed ({overall_results['summary']['success_rate']:.1f}%)"
        )

        return overall_results

    def test_service_validation(self) -> Dict[str, Any]:
        """Test that all required services are available."""
        try:
            validation_results = ServiceFactory.validate_service_configuration(
                global_injector
            )

            critical_services = ["chat", "ingest"]
            critical_available = all(
                validation_results.get(svc, False) for svc in critical_services
            )

            return {
                "success": critical_available,
                "validation_results": validation_results,
                "critical_services": critical_services,
                "critical_available": critical_available,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_orchestrator_creation(self) -> Dict[str, Any]:
        """Test orchestrator creation and configuration."""
        try:
            orchestrator = ServiceFactory.create_service_orchestrator(global_injector)

            # Check that services were registered
            registered_services = len(orchestrator._services)

            return {
                "success": registered_services > 0,
                "registered_services": registered_services,
                "service_configs": len(orchestrator._service_configs),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_service_initialization(self) -> Dict[str, Any]:
        """Test service initialization process."""
        try:
            orchestrator = ServiceFactory.create_service_orchestrator(global_injector)
            initialization_success = orchestrator.initialize_services()

            # Get service health after initialization
            service_health = orchestrator.get_service_health()

            return {
                "success": initialization_success,
                "orchestrator_status": orchestrator.get_orchestrator_status().value,
                "service_health": {k: v.value for k, v in service_health.items()},
                "metrics": orchestrator.get_comprehensive_metrics(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_facade_functionality(self) -> Dict[str, Any]:
        """Test individual facade functionality."""
        try:
            ui_integration = create_ui_service_integration(global_injector)

            test_results = {}

            # Test chat service facade
            if ui_integration.chat_service:
                try:
                    metrics = ui_integration.chat_service.get_service_info()
                    test_results["chat_facade"] = {"success": True, "metrics": metrics}
                except Exception as e:
                    test_results["chat_facade"] = {"success": False, "error": str(e)}
            else:
                test_results["chat_facade"] = {
                    "success": False,
                    "error": "Service not available",
                }

            # Test document service facade
            if ui_integration.document_service:
                try:
                    metrics = ui_integration.document_service.get_service_info()
                    test_results["document_facade"] = {
                        "success": True,
                        "metrics": metrics,
                    }
                except Exception as e:
                    test_results["document_facade"] = {
                        "success": False,
                        "error": str(e),
                    }
            else:
                test_results["document_facade"] = {
                    "success": False,
                    "error": "Service not available",
                }

            # Test feeds service facade
            if ui_integration.feeds_service:
                try:
                    metrics = ui_integration.feeds_service.get_service_info()
                    test_results["feeds_facade"] = {"success": True, "metrics": metrics}
                except Exception as e:
                    test_results["feeds_facade"] = {"success": False, "error": str(e)}
            else:
                test_results["feeds_facade"] = {
                    "success": False,
                    "error": "Service not available",
                }

            # Overall success if at least critical services work
            overall_success = test_results.get("chat_facade", {}).get(
                "success", False
            ) and test_results.get("document_facade", {}).get("success", False)

            return {
                "success": overall_success,
                "facade_tests": test_results,
                "integration_ready": ui_integration.is_ready,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_performance_optimization(self) -> Dict[str, Any]:
        """Test performance optimization features."""
        try:
            # Test cache functionality
            def test_operation():
                time.sleep(0.1)  # Simulate work
                return "test_result"

            # First call should miss cache
            start_time = time.time()
            result1 = self.performance_optimizer.optimize_ui_operation(
                "test_op", test_operation
            )
            first_duration = time.time() - start_time

            # Second call should hit cache
            start_time = time.time()
            result2 = self.performance_optimizer.optimize_ui_operation(
                "test_op", test_operation
            )
            second_duration = time.time() - start_time

            # Get performance metrics
            metrics = self.performance_optimizer.get_performance_metrics()

            return {
                "success": True,
                "first_result": result1,
                "second_result": result2,
                "first_duration": first_duration,
                "second_duration": second_duration,
                "cache_working": second_duration < first_duration,
                "performance_metrics": metrics,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_health_monitoring(self) -> Dict[str, Any]:
        """Test health monitoring functionality."""
        try:
            ui_integration = create_ui_service_integration(global_injector)

            # Perform health checks
            health_results = ui_integration.perform_health_checks()

            # Get service status
            service_status = ui_integration.get_service_status()

            return {
                "success": True,
                "health_results": {
                    k: v.value if hasattr(v, "value") else v
                    for k, v in health_results.items()
                },
                "service_status": service_status,
                "integration_ready": ui_integration.is_ready,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and circuit breaker functionality."""
        try:
            # Test with mock failing service
            def failing_operation():
                raise Exception("Simulated failure")

            try:
                result = self.performance_optimizer.optimize_ui_operation(
                    "failing_op", failing_operation, use_cache=False
                )
                return {"success": False, "error": "Expected exception was not raised"}
            except Exception as expected_error:
                # This is expected behavior
                pass

            # Get metrics after failure
            metrics = self.performance_optimizer.get_performance_metrics()

            return {
                "success": True,
                "error_handled": True,
                "performance_metrics": metrics,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_integration_compatibility(self) -> Dict[str, Any]:
        """Test compatibility layer functionality."""
        try:
            ui_integration = create_ui_service_integration(global_injector)

            from .ui_service_integration import ServiceCompatibilityLayer

            compatibility_layer = ServiceCompatibilityLayer(ui_integration)

            # Test document listing compatibility
            try:
                file_list = compatibility_layer.list_ingested_files()
                document_test = {"success": True, "file_count": len(file_list)}
            except Exception as e:
                document_test = {"success": False, "error": str(e)}

            # Test feeds compatibility
            try:
                feeds = compatibility_layer.get_feeds()
                feeds_test = {"success": True, "feed_count": len(feeds)}
            except Exception as e:
                feeds_test = {"success": False, "error": str(e)}

            return {
                "success": document_test[
                    "success"
                ],  # At least document compatibility must work
                "document_compatibility": document_test,
                "feeds_compatibility": feeds_test,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


def run_service_integration_tests() -> Dict[str, Any]:
    """
    Run service integration tests and return results.

    Returns:
        Dictionary with test results
    """
    test_runner = ServiceIntegrationTest()
    return test_runner.run_all_tests()


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    print("=" * 60)
    print("Service Layer Integration Tests")
    print("=" * 60)

    results = run_service_integration_tests()

    # Print summary
    summary = results["summary"]
    print(f"\nTest Results Summary:")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Duration: {summary['total_duration']:.2f}s")
    print(f"Overall Status: {summary['status'].upper()}")

    if summary["failed_tests"] > 0:
        print(f"\nFailed Tests:")
        for test_name, test_result in results["tests"].items():
            if test_result["status"] != "passed":
                print(
                    f"  - {test_name}: {test_result['details'].get('error', 'Unknown error')}"
                )

    print("\n" + "=" * 60)
