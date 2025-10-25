"""Internal Assistant UI State Management

This package provides centralized state management for the Internal Assistant UI,
replacing scattered state management with a clean, predictable architecture.

Phase 2: State Management System - Complete implementation with:
- Centralized StateStore with observer pattern
- Typed state schemas with Pydantic validation
- Cross-component communication via MessageBus
- Session management with persistence
- State selectors for computed values
- Migration utilities for legacy state
"""

from .app_state import (
    ApplicationState,
    ChatState,
    DocumentState,
    ExternalInfoState,
    SettingsState,
    UIState,
    create_application_state_from_legacy,
    validate_application_state,
)

# Gradio synchronization system - Phase 2.5 fix
from .gradio_sync import ComponentBinding, GradioStateSync, create_gradio_sync

# Integration manager - required import
from .integration import StateIntegrationManager
from .message_bus import (
    ChatComponentHandler,
    DocumentComponentHandler,
    Message,
    MessageBus,
    MessageFilter,
    MessageHandler,
    MessagePriority,
    MessageType,
    SimpleMessageFilter,
    UIComponentHandler,
)
from .session_manager import (
    ConversationHistory,
    SessionManager,
    SessionMetadata,
    SessionStorage,
    create_default_session_manager,
    migrate_legacy_conversation_history,
)
from .state_manager import (
    MemoizedSelector,
    StateChange,
    StateChangeType,
    StateObserver,
    StatePersistence,
    StateSelector,
    StateStore,
    create_chat_state_selector,
    create_document_state_selector,
)

# Convenience imports for integration
try:
    from .integration import StateObserverAdapter
    from .selectors import (
        ChatStateSelector,
        DashboardSummarySelector,
        DocumentCountSelector,
        SystemHealthSelector,
        ThreatIntelligenceSelector,
        UILayoutSelector,
    )
except ImportError:
    # These modules may not exist yet, graceful fallback
    pass

__all__ = [
    # Core state management
    "StateStore",
    "StateObserver",
    "StateSelector",
    "MemoizedSelector",
    "StateChange",
    "StateChangeType",
    "StatePersistence",
    # State schemas
    "ApplicationState",
    "ChatState",
    "DocumentState",
    "SettingsState",
    "ExternalInfoState",
    "UIState",
    # Message bus
    "MessageBus",
    "Message",
    "MessageType",
    "MessagePriority",
    "MessageHandler",
    "MessageFilter",
    "SimpleMessageFilter",
    "UIComponentHandler",
    "ChatComponentHandler",
    "DocumentComponentHandler",
    # Session management
    "SessionManager",
    "SessionMetadata",
    "ConversationHistory",
    "SessionStorage",
    # Utility functions
    "create_chat_state_selector",
    "create_document_state_selector",
    "create_application_state_from_legacy",
    "validate_application_state",
    "create_default_session_manager",
    "migrate_legacy_conversation_history",
    # Gradio synchronization
    "GradioStateSync",
    "create_gradio_sync",
    "ComponentBinding",
    # Integration
    "StateIntegrationManager",
]

# Version info
__version__ = "2.0.0"
__phase__ = "Phase 2: State Management System"
__status__ = "Complete"
