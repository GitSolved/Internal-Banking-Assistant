"""
Service Factory

Factory for creating and configuring service facades and orchestrator
with dependency injection integration.
"""

import logging
from typing import Optional, Any, Dict

from internal_assistant.di import global_injector
from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.chunks.chunks_service import ChunksService
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.server.recipes.summarize.summarize_service import (
    SummarizeService,
)

from .service_orchestrator import ServiceOrchestrator
from .chat_service_facade import ChatServiceFacade
from .document_service_facade import DocumentServiceFacade
from .feeds_service_facade import FeedsServiceFacade

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory for creating configured service facades and orchestrator.
    Integrates with the application's dependency injection system.
    """

    @staticmethod
    def create_service_orchestrator(
        injector: Optional[Any] = None,
    ) -> ServiceOrchestrator:
        """
        Create a fully configured service orchestrator.

        Args:
            injector: Optional dependency injector (uses global if not provided)

        Returns:
            Configured ServiceOrchestrator instance
        """
        if injector is None:
            injector = global_injector

        logger.info("Creating service orchestrator with dependency injection")

        orchestrator = ServiceOrchestrator()

        try:
            # Register chat service
            chat_service = injector.get(ChatService)
            orchestrator.register_service(
                name="chat",
                service=chat_service,
                facade_class=ChatServiceFacade,
                dependencies=[],
                critical=True,
            )
            logger.info("Registered chat service")

        except Exception as e:
            logger.error(f"Failed to register chat service: {e}")
            raise

        try:
            # Register document services
            ingest_service = injector.get(IngestService)
            chunks_service = None

            try:
                chunks_service = injector.get(ChunksService)
            except Exception as e:
                logger.warning(f"Chunks service not available: {e}")

            # Create document facade with optional chunks service
            document_facade_factory = lambda ingest_svc: DocumentServiceFacade(
                ingest_svc, chunks_service
            )

            orchestrator.register_service(
                name="document",
                service=ingest_service,
                facade_class=document_facade_factory,
                dependencies=[],
                critical=True,
            )
            logger.info("Registered document services")

        except Exception as e:
            logger.error(f"Failed to register document services: {e}")
            raise

        try:
            # Register feeds service (non-critical)
            feeds_service = injector.get(RSSFeedService)
            orchestrator.register_service(
                name="feeds",
                service=feeds_service,
                facade_class=FeedsServiceFacade,
                dependencies=[],
                critical=False,
            )
            logger.info("Registered feeds service")

        except Exception as e:
            logger.warning(f"Failed to register feeds service (non-critical): {e}")

        try:
            # Register summarize service (non-critical)
            summarize_service = injector.get(SummarizeService)
            # Note: No specific facade for summarize service yet, could be added if needed
            logger.info("Summarize service available")

        except Exception as e:
            logger.warning(f"Summarize service not available: {e}")

        logger.info(
            f"Service orchestrator created with {len(orchestrator._services)} services"
        )
        return orchestrator

    @staticmethod
    def create_chat_service_facade(injector: Optional[Any] = None) -> ChatServiceFacade:
        """
        Create a standalone chat service facade.

        Args:
            injector: Optional dependency injector

        Returns:
            ChatServiceFacade instance
        """
        if injector is None:
            injector = global_injector

        chat_service = injector.get(ChatService)
        return ChatServiceFacade(chat_service)

    @staticmethod
    def create_document_service_facade(
        injector: Optional[Any] = None,
    ) -> DocumentServiceFacade:
        """
        Create a standalone document service facade.

        Args:
            injector: Optional dependency injector

        Returns:
            DocumentServiceFacade instance
        """
        if injector is None:
            injector = global_injector

        ingest_service = injector.get(IngestService)

        # Try to get chunks service
        chunks_service = None
        try:
            chunks_service = injector.get(ChunksService)
        except Exception:
            logger.info("Chunks service not available for document facade")

        return DocumentServiceFacade(ingest_service, chunks_service)

    @staticmethod
    def create_feeds_service_facade(
        injector: Optional[Any] = None,
    ) -> FeedsServiceFacade:
        """
        Create a standalone feeds service facade.

        Args:
            injector: Optional dependency injector

        Returns:
            FeedsServiceFacade instance
        """
        if injector is None:
            injector = global_injector

        feeds_service = injector.get(RSSFeedService)
        return FeedsServiceFacade(feeds_service)

    @staticmethod
    def create_service_mock_factory() -> Dict[str, Any]:
        """
        Create mock services for testing purposes.

        Returns:
            Dictionary of mock service instances
        """
        logger.info("Creating mock services for testing")

        # Mock implementations for testing
        class MockChatService:
            def stream_chat(self, messages, use_context=True, context_filter=None):
                from internal_assistant.server.chat.chat_service import CompletionGen

                def mock_generator():
                    yield "Mock response"

                return CompletionGen(response=mock_generator(), sources=None)

            def health_check(self):
                return True

        class MockIngestService:
            def list_ingested(self):
                return []

            def bulk_ingest(self, files):
                pass

            def delete_all(self):
                pass

        class MockFeedsService:
            def get_feeds(self, source_filter=None, days_filter=None):
                return []

        return {
            "chat": MockChatService(),
            "ingest": MockIngestService(),
            "feeds": MockFeedsService(),
        }

    @staticmethod
    def create_test_orchestrator() -> ServiceOrchestrator:
        """
        Create orchestrator with mock services for testing.

        Returns:
            ServiceOrchestrator with mock services
        """
        logger.info("Creating test service orchestrator")

        orchestrator = ServiceOrchestrator()
        mock_services = ServiceFactory.create_service_mock_factory()

        # Register mock services
        orchestrator.register_service(
            name="chat",
            service=mock_services["chat"],
            facade_class=ChatServiceFacade,
            critical=True,
        )

        orchestrator.register_service(
            name="document",
            service=mock_services["ingest"],
            facade_class=lambda svc: DocumentServiceFacade(svc, None),
            critical=True,
        )

        orchestrator.register_service(
            name="feeds",
            service=mock_services["feeds"],
            facade_class=FeedsServiceFacade,
            critical=False,
        )

        return orchestrator

    @staticmethod
    def validate_service_configuration(
        injector: Optional[Any] = None,
    ) -> Dict[str, bool]:
        """
        Validate that all required services are available.

        Args:
            injector: Optional dependency injector

        Returns:
            Dictionary mapping service names to availability status
        """
        if injector is None:
            injector = global_injector

        logger.info("Validating service configuration")

        validation_results = {}

        # Test critical services
        try:
            injector.get(ChatService)
            validation_results["chat"] = True
        except Exception as e:
            logger.error(f"Chat service validation failed: {e}")
            validation_results["chat"] = False

        try:
            injector.get(IngestService)
            validation_results["ingest"] = True
        except Exception as e:
            logger.error(f"Ingest service validation failed: {e}")
            validation_results["ingest"] = False

        # Test optional services
        try:
            injector.get(ChunksService)
            validation_results["chunks"] = True
        except Exception:
            validation_results["chunks"] = False

        try:
            injector.get(RSSFeedService)
            validation_results["feeds"] = True
        except Exception:
            validation_results["feeds"] = False

        try:
            injector.get(SummarizeService)
            validation_results["summarize"] = True
        except Exception:
            validation_results["summarize"] = False

        critical_services = ["chat", "ingest"]
        critical_available = all(
            validation_results.get(svc, False) for svc in critical_services
        )

        logger.info(f"Service validation results: {validation_results}")
        logger.info(f"Critical services available: {critical_available}")

        return validation_results
