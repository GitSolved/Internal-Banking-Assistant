"""
UI State Management

This module defines state management models for the Internal Assistant UI.
It provides structured ways to manage component state, user sessions, and UI configuration.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SessionState(BaseModel):
    """
    Model for managing user session state.
    """

    session_id: str = Field(..., description="Unique session identifier")

    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation timestamp"
    )

    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )

    current_mode: str = Field("RAG Mode", description="Current assistant mode")

    chat_history: List[tuple] = Field(
        default_factory=list, description="Chat message history"
    )

    uploaded_files: List[str] = Field(
        default_factory=list, description="List of uploaded file names"
    )

    settings: Dict[str, Any] = Field(
        default_factory=dict, description="User-specific settings"
    )

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def add_message(self, user_msg: str, bot_response: str) -> None:
        """Add a message exchange to history."""
        self.chat_history.append((user_msg, bot_response))
        self.update_activity()

    def clear_history(self) -> None:
        """Clear chat history."""
        self.chat_history = []
        self.update_activity()


class ComponentState(BaseModel):
    """
    Model for managing individual component state.
    """

    component_id: str = Field(..., description="Component identifier")

    is_visible: bool = Field(True, description="Component visibility")

    is_enabled: bool = Field(True, description="Component enabled state")

    data: Dict[str, Any] = Field(
        default_factory=dict, description="Component-specific data"
    )

    def update_data(self, key: str, value: Any) -> None:
        """Update component data."""
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get component data value."""
        return self.data.get(key, default)


class UIConfiguration(BaseModel):
    """
    Model for UI configuration settings.
    """

    theme: str = Field("dark", description="UI theme (dark/light)")

    layout: str = Field("default", description="Layout configuration")

    sidebar_visible: bool = Field(True, description="Sidebar visibility")

    auto_refresh: bool = Field(False, description="Auto-refresh enabled")

    refresh_interval: int = Field(300, description="Refresh interval in seconds")

    show_advanced: bool = Field(False, description="Show advanced options")

    component_settings: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Per-component settings"
    )

    def get_component_setting(
        self, component: str, key: str, default: Any = None
    ) -> Any:
        """Get a component-specific setting."""
        if component in self.component_settings:
            return self.component_settings[component].get(key, default)
        return default

    def set_component_setting(self, component: str, key: str, value: Any) -> None:
        """Set a component-specific setting."""
        if component not in self.component_settings:
            self.component_settings[component] = {}
        self.component_settings[component][key] = value


class FilterState(BaseModel):
    """
    Model for managing filter states across components.
    """

    search_term: str = Field("", description="Current search term")

    file_type: str = Field("All", description="File type filter")

    category: str = Field("All", description="Category filter")

    severity: str = Field("All", description="Severity filter (for CVE/alerts)")

    date_range: Optional[tuple] = Field(
        None, description="Date range filter (start, end)"
    )

    tags: List[str] = Field(default_factory=list, description="Tag filters")

    def reset(self) -> None:
        """Reset all filters to defaults."""
        self.search_term = ""
        self.file_type = "All"
        self.category = "All"
        self.severity = "All"
        self.date_range = None
        self.tags = []

    def apply_to_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply filter state to a query dictionary.

        Args:
            query: Base query dictionary

        Returns:
            Query with filters applied
        """
        filtered_query = query.copy()

        if self.search_term:
            filtered_query["search"] = self.search_term

        if self.file_type != "All":
            filtered_query["file_type"] = self.file_type

        if self.category != "All":
            filtered_query["category"] = self.category

        if self.severity != "All":
            filtered_query["severity"] = self.severity

        if self.date_range:
            filtered_query["date_start"] = self.date_range[0]
            filtered_query["date_end"] = self.date_range[1]

        if self.tags:
            filtered_query["tags"] = self.tags

        return filtered_query


class NotificationType(str, Enum):
    """Notification types."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(BaseModel):
    """
    Model for UI notifications.
    """

    message: str = Field(..., description="Notification message")

    type: NotificationType = Field(
        NotificationType.INFO, description="Notification type"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now, description="Notification timestamp"
    )

    duration: int = Field(5000, description="Display duration in milliseconds")

    dismissible: bool = Field(True, description="Can be dismissed by user")

    action: Optional[Dict[str, Any]] = Field(
        None, description="Optional action button configuration"
    )

    def to_gradio_format(self) -> Dict[str, Any]:
        """
        Convert to Gradio-compatible format.

        Returns:
            Dictionary for Gradio notification
        """
        return {
            "value": self.message,
            "variant": self.type.value,
            "duration": self.duration / 1000,  # Convert to seconds
        }


class ApplicationState(BaseModel):
    """
    Model for overall application state.
    """

    session: SessionState
    ui_config: UIConfiguration
    components: Dict[str, ComponentState] = Field(
        default_factory=dict, description="Component states"
    )
    filters: FilterState = Field(
        default_factory=FilterState, description="Global filter state"
    )
    notifications: List[Notification] = Field(
        default_factory=list, description="Active notifications"
    )

    def get_component_state(self, component_id: str) -> Optional[ComponentState]:
        """Get state for a specific component."""
        return self.components.get(component_id)

    def set_component_state(self, component_id: str, state: ComponentState) -> None:
        """Set state for a specific component."""
        self.components[component_id] = state

    def add_notification(
        self, message: str, type: NotificationType = NotificationType.INFO
    ) -> None:
        """Add a notification."""
        notification = Notification(message=message, type=type)
        self.notifications.append(notification)

    def clear_notifications(self) -> None:
        """Clear all notifications."""
        self.notifications = []
