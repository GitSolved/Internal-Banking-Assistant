"""UI Service Layer

This module provides service facade abstractions for the UI layer,
implementing clean service orchestration, error handling, and performance optimization.

Phase 3: Service Layer & Component Completion
"""

from .chat_service_facade import ChatServiceFacade
from .document_service_facade import DocumentServiceFacade
from .feeds_service_facade import FeedsServiceFacade
from .performance_optimizer import PerformanceOptimizer
from .service_facade import ServiceFacade, ServiceHealth
from .service_factory import ServiceFactory
from .service_orchestrator import ServiceOrchestrator
from .ui_service_integration import (
    ServiceCompatibilityLayer,
    UIServiceIntegration,
    create_ui_service_integration,
)

__all__ = [
    "ChatServiceFacade",
    "DocumentServiceFacade",
    "FeedsServiceFacade",
    "PerformanceOptimizer",
    "ServiceCompatibilityLayer",
    "ServiceFacade",
    "ServiceFactory",
    "ServiceHealth",
    "ServiceOrchestrator",
    "UIServiceIntegration",
    "create_ui_service_integration",
]
