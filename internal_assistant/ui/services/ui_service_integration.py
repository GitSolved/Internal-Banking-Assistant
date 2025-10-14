"""
UI Service Integration

Provides integration layer between the UI and service facades,
replacing direct service dependencies with orchestrated facades.
"""

import logging
from typing import Optional, Any, Dict, List, Tuple
from pathlib import Path

from .service_orchestrator import ServiceOrchestrator, ServiceStatus
from .service_factory import ServiceFactory
from .chat_service_facade import ChatServiceFacade
from .document_service_facade import DocumentServiceFacade
from .feeds_service_facade import FeedsServiceFacade

logger = logging.getLogger(__name__)


class UIServiceIntegration:
    """
    Integration layer that provides clean service access for the UI layer.
    Replaces direct service injection with orchestrated facade access.
    """

    def __init__(self, injector=None):
        """
        Initialize UI service integration.

        Args:
            injector: Optional dependency injector
        """
        self._orchestrator: Optional[ServiceOrchestrator] = None
        self._injector = injector
        self._initialization_completed = False

        logger.info("UI Service Integration initialized")

    def initialize(self) -> bool:
        """
        Initialize the service orchestrator and all services.

        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing UI service integration")

            # Create and configure orchestrator
            self._orchestrator = ServiceFactory.create_service_orchestrator(
                self._injector
            )

            # Initialize services
            success = self._orchestrator.initialize_services()

            if success:
                self._initialization_completed = True
                logger.info("UI service integration initialization completed")
            else:
                logger.error("UI service integration initialization failed")

            return success

        except Exception as e:
            logger.error(f"Failed to initialize UI service integration: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        """Check if service integration is ready."""
        if not self._orchestrator or not self._initialization_completed:
            return False

        return self._orchestrator.get_orchestrator_status() in [
            ServiceStatus.READY,
            ServiceStatus.DEGRADED,
        ]

    @property
    def chat_service(self) -> Optional[ChatServiceFacade]:
        """Get chat service facade."""
        if not self._orchestrator:
            return None
        return self._orchestrator.get_service("chat")

    @property
    def document_service(self) -> Optional[DocumentServiceFacade]:
        """Get document service facade."""
        if not self._orchestrator:
            return None
        return self._orchestrator.get_service("document")

    @property
    def feeds_service(self) -> Optional[FeedsServiceFacade]:
        """Get feeds service facade."""
        if not self._orchestrator:
            return None
        return self._orchestrator.get_service("feeds")

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status information.

        Returns:
            Dictionary with service status details
        """
        if not self._orchestrator:
            return {
                "integration_status": "not_initialized",
                "services": {},
                "overall_health": "unknown",
            }

        return {
            "integration_status": "ready" if self.is_ready else "not_ready",
            "orchestrator_status": self._orchestrator.get_orchestrator_status().value,
            "service_health": self._orchestrator.get_service_health(),
            "metrics": self._orchestrator.get_comprehensive_metrics(),
        }

    def perform_health_checks(self) -> Dict[str, Any]:
        """
        Perform health checks on all services.

        Returns:
            Health check results
        """
        if not self._orchestrator:
            return {"error": "orchestrator not initialized"}

        return self._orchestrator.perform_health_checks()

    def shutdown(self) -> None:
        """Gracefully shutdown service integration."""
        if self._orchestrator:
            self._orchestrator.shutdown()

        logger.info("UI service integration shutdown completed")


class ServiceCompatibilityLayer:
    """
    Compatibility layer that provides the same interface as direct service injection
    but uses the service facades underneath.

    This allows gradual migration from direct service usage to facade-based access.
    """

    def __init__(self, ui_integration: UIServiceIntegration):
        self.ui_integration = ui_integration

    # Chat Service Compatibility Methods
    def stream_chat(self, messages, use_context=True, context_filter=None):
        """Compatibility method for chat streaming."""
        chat_service = self.ui_integration.chat_service
        if not chat_service:
            raise RuntimeError("Chat service not available")

        return chat_service.stream_chat(
            messages=messages, use_context=use_context, context_filter=context_filter
        )

    # Document Service Compatibility Methods
    def list_ingested_files(self):
        """Compatibility method for listing ingested files."""
        doc_service = self.ui_integration.document_service
        if not doc_service:
            return [["[Service not available]"]]

        return doc_service.list_ingested_files()

    def bulk_ingest(self, files_to_ingest):
        """Compatibility method for bulk ingestion."""
        doc_service = self.ui_integration.document_service
        if not doc_service:
            raise RuntimeError("Document service not available")

        return doc_service.bulk_ingest(files_to_ingest)

    def ingest_folder(self, folder_path, **kwargs):
        """Compatibility method for folder ingestion."""
        doc_service = self.ui_integration.document_service
        if not doc_service:
            return [], "Document service not available"

        return doc_service.ingest_folder(folder_path, **kwargs)

    def delete_all_documents(self):
        """Compatibility method for deleting all documents."""
        doc_service = self.ui_integration.document_service
        if not doc_service:
            return [], "Document service not available"

        return doc_service.delete_all_documents()

    # Feeds Service Compatibility Methods
    def get_feeds(self, source_filter=None, days_filter=None):
        """Compatibility method for getting feeds."""
        feeds_service = self.ui_integration.feeds_service
        if not feeds_service:
            return []

        return feeds_service.get_feeds(source_filter, days_filter)

    def get_cve_data(self):
        """Compatibility method for getting CVE data."""
        feeds_service = self.ui_integration.feeds_service
        if not feeds_service:
            return []

        return feeds_service.get_cve_data()

    def get_mitre_data(self):
        """Compatibility method for getting MITRE data."""
        feeds_service = self.ui_integration.feeds_service
        if not feeds_service:
            return {"techniques": [], "tactics": [], "groups": []}

        return feeds_service.get_mitre_data()

    def refresh_feeds(self, force=False):
        """Compatibility method for refreshing feeds."""
        feeds_service = self.ui_integration.feeds_service
        if not feeds_service:
            return {"status": "service_unavailable"}

        return feeds_service.refresh_feeds(force)


def create_ui_service_integration(injector=None) -> UIServiceIntegration:
    """
    Factory function to create and initialize UI service integration.

    Args:
        injector: Optional dependency injector

    Returns:
        Initialized UIServiceIntegration instance
    """
    integration = UIServiceIntegration(injector)
    success = integration.initialize()

    if not success:
        logger.warning(
            "Failed to fully initialize UI service integration, some features may be degraded"
        )

    return integration
