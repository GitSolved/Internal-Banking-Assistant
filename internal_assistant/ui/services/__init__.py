"""
UI Service Layer

This module provides service facade abstractions for the UI layer,
implementing clean service orchestration, error handling, and performance optimization.

Phase 3: Service Layer & Component Completion
"""

from .service_facade import ServiceFacade, ServiceHealth
from .chat_service_facade import ChatServiceFacade
from .document_service_facade import DocumentServiceFacade
from .feeds_service_facade import FeedsServiceFacade
from .service_orchestrator import ServiceOrchestrator
from .service_factory import ServiceFactory
from .ui_service_integration import (
    UIServiceIntegration,
    ServiceCompatibilityLayer,
    create_ui_service_integration,
)
from .performance_optimizer import PerformanceOptimizer

__all__ = [
    "ServiceFacade",
    "ServiceHealth",
    "ChatServiceFacade",
    "DocumentServiceFacade",
    "FeedsServiceFacade",
    "ServiceOrchestrator",
    "ServiceFactory",
    "UIServiceIntegration",
    "ServiceCompatibilityLayer",
    "create_ui_service_integration",
    "PerformanceOptimizer",
]
