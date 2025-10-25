"""UI Error Boundaries Implementation

This module provides comprehensive error boundary infrastructure for the Gradio-based UI,
implementing graceful error handling with fallback UIs and user-friendly error messages.

Part of Phase 2: Error Boundaries Implementation for production readiness.
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    LOW = "low"  # Minor issues, component still functional
    MEDIUM = "medium"  # Component degraded but recoverable
    HIGH = "high"  # Component unavailable, fallback required
    CRITICAL = "critical"  # System-wide issue, requires immediate attention


class ErrorCategory(Enum):
    """Error categories for better user understanding."""

    NETWORK = "network"  # Network connectivity issues
    SERVICE = "service"  # Backend service failures
    VALIDATION = "validation"  # Input validation errors
    PERMISSION = "permission"  # Access/permission issues
    RESOURCE = "resource"  # Resource limitations (memory, disk, etc.)
    SYSTEM = "system"  # System-level errors
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class ErrorInfo:
    """Comprehensive error information for logging and display."""

    timestamp: float
    component_name: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    traceback: str
    user_message: str
    recovery_suggestions: list[str]
    context: dict[str, Any]
    is_recoverable: bool = True


class UIErrorBoundary(ABC):
    """Base class for UI error boundaries.

    Provides the foundation for implementing error boundaries around UI components,
    with automatic error detection, logging, and fallback UI generation.
    """

    def __init__(self, component_name: str, fallback_message: str | None = None):
        """Initialize error boundary.

        Args:
            component_name: Name of the component being protected
            fallback_message: Custom fallback message for this component
        """
        self.component_name = component_name
        self.fallback_message = (
            fallback_message or f"{component_name} temporarily unavailable"
        )
        self._error_history: list[ErrorInfo] = []
        self._error_count = 0
        self._last_error_time = 0.0
        self._is_in_fallback_mode = False
        self._recovery_callback: Callable | None = None

        logger.info(f"Error boundary initialized for component: {component_name}")

    def wrap_function(self, func: Callable) -> Callable:
        """Decorator to wrap functions with error boundary protection.

        Args:
            func: Function to protect

        Returns:
            Wrapped function with error handling
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Check if we're in fallback mode and should attempt recovery
                if self._is_in_fallback_mode and self._should_attempt_recovery():
                    logger.info(f"Attempting recovery for {self.component_name}")
                    self._is_in_fallback_mode = False

                # Execute the original function
                result = func(*args, **kwargs)

                # Reset error count on successful execution
                if self._error_count > 0:
                    logger.info(
                        f"Component {self.component_name} recovered after {self._error_count} errors"
                    )
                    self._error_count = 0

                return result

            except Exception as e:
                # Handle the error and return fallback
                error_info = self._create_error_info(e, func.__name__)
                return self._handle_error(error_info)

        return wrapper

    def _create_error_info(self, exception: Exception, function_name: str) -> ErrorInfo:
        """Create comprehensive error information."""
        current_time = time.time()

        # Categorize the error
        error_category = self._categorize_error(exception)
        severity = self._assess_severity(exception, error_category)

        # Generate user-friendly message and recovery suggestions
        user_message, recovery_suggestions = self._generate_user_guidance(
            exception, error_category
        )

        return ErrorInfo(
            timestamp=current_time,
            component_name=self.component_name,
            error_type=type(exception).__name__,
            error_message=str(exception),
            severity=severity,
            category=error_category,
            traceback=traceback.format_exc(),
            user_message=user_message,
            recovery_suggestions=recovery_suggestions,
            context={
                "function_name": function_name,
                "error_count": self._error_count + 1,
                "time_since_last_error": (
                    current_time - self._last_error_time
                    if self._last_error_time > 0
                    else 0
                ),
            },
            is_recoverable=self._is_error_recoverable(exception),
        )

    def _handle_error(self, error_info: ErrorInfo) -> Any:
        """Handle error with logging and fallback generation."""
        self._error_count += 1
        self._last_error_time = error_info.timestamp
        self._error_history.append(error_info)

        # Log the error appropriately based on severity
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Error in {self.component_name}: {error_info.error_message}")
            logger.debug(f"Traceback: {error_info.traceback}")
        else:
            logger.warning(
                f"Minor error in {self.component_name}: {error_info.error_message}"
            )

        # Enter fallback mode if error is severe or repeated
        if (
            error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            or self._error_count >= 3
        ):
            self._is_in_fallback_mode = True

        # Generate fallback UI
        return self._create_fallback_ui(error_info)

    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize error based on exception type and message."""
        error_msg = str(exception).lower()
        exception_type = type(exception).__name__

        # Network-related errors
        if any(
            keyword in error_msg
            for keyword in ["connection", "network", "timeout", "unreachable"]
        ):
            return ErrorCategory.NETWORK

        # Service-related errors
        if any(
            keyword in error_msg for keyword in ["service", "server", "api", "endpoint"]
        ):
            return ErrorCategory.SERVICE

        # Validation errors
        if any(
            keyword in error_msg
            for keyword in ["validation", "invalid", "format", "parse"]
        ):
            return ErrorCategory.VALIDATION

        # Permission errors
        if any(
            keyword in error_msg
            for keyword in ["permission", "access", "forbidden", "unauthorized"]
        ):
            return ErrorCategory.PERMISSION

        # Resource errors
        if any(
            keyword in error_msg
            for keyword in ["memory", "disk", "space", "resource", "limit"]
        ):
            return ErrorCategory.RESOURCE

        # System errors
        if exception_type in ["SystemError", "OSError", "RuntimeError"]:
            return ErrorCategory.SYSTEM

        return ErrorCategory.UNKNOWN

    def _assess_severity(
        self, exception: Exception, category: ErrorCategory
    ) -> ErrorSeverity:
        """Assess error severity based on type and category."""
        exception_type = type(exception).__name__

        # Critical system errors
        if category == ErrorCategory.SYSTEM or exception_type in [
            "SystemExit",
            "KeyboardInterrupt",
        ]:
            return ErrorSeverity.CRITICAL

        # High severity for service and network issues
        if category in [ErrorCategory.NETWORK, ErrorCategory.SERVICE]:
            return ErrorSeverity.HIGH

        # Medium severity for validation and permission issues
        if category in [ErrorCategory.VALIDATION, ErrorCategory.PERMISSION]:
            return ErrorSeverity.MEDIUM

        # Low severity for unknown issues (might be transient)
        return ErrorSeverity.LOW

    def _generate_user_guidance(
        self, exception: Exception, category: ErrorCategory
    ) -> tuple[str, list[str]]:
        """Generate user-friendly message and recovery suggestions."""
        base_messages = {
            ErrorCategory.NETWORK: (
                "Connection issue detected",
                [
                    "Check your internet connection",
                    "Try refreshing the page",
                    "Wait a moment and try again",
                ],
            ),
            ErrorCategory.SERVICE: (
                "Service temporarily unavailable",
                [
                    "The service may be restarting",
                    "Try again in a few moments",
                    "Check system status",
                ],
            ),
            ErrorCategory.VALIDATION: (
                "Input validation error",
                [
                    "Check your input format",
                    "Ensure all required fields are filled",
                    "Try with different data",
                ],
            ),
            ErrorCategory.PERMISSION: (
                "Access permission issue",
                [
                    "Check your permissions",
                    "Contact your administrator",
                    "Try logging in again",
                ],
            ),
            ErrorCategory.RESOURCE: (
                "Resource limitation encountered",
                [
                    "Try with smaller data",
                    "Wait for system resources to free up",
                    "Contact support if persistent",
                ],
            ),
            ErrorCategory.SYSTEM: (
                "System error occurred",
                [
                    "Try refreshing the page",
                    "Contact support if error persists",
                    "Check system logs",
                ],
            ),
            ErrorCategory.UNKNOWN: (
                "Unexpected error occurred",
                [
                    "Try refreshing the component",
                    "Contact support if error persists",
                    "Check your input data",
                ],
            ),
        }

        return base_messages.get(category, base_messages[ErrorCategory.UNKNOWN])

    def _is_error_recoverable(self, exception: Exception) -> bool:
        """Determine if error is recoverable."""
        non_recoverable_types = ["SystemExit", "KeyboardInterrupt", "MemoryError"]
        return type(exception).__name__ not in non_recoverable_types

    def _should_attempt_recovery(self) -> bool:
        """Determine if recovery should be attempted."""
        # Wait at least 30 seconds before attempting recovery
        if time.time() - self._last_error_time < 30:
            return False

        # Don't attempt recovery if too many recent errors
        if self._error_count >= 5:
            return False

        return True

    @abstractmethod
    def _create_fallback_ui(self, error_info: ErrorInfo) -> Any:
        """Create fallback UI for the specific component type."""
        pass

    def set_recovery_callback(self, callback: Callable) -> None:
        """Set callback to call when component recovers."""
        self._recovery_callback = callback

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of errors for debugging."""
        recent_errors = [
            e for e in self._error_history if time.time() - e.timestamp < 3600
        ]  # Last hour

        return {
            "component_name": self.component_name,
            "total_errors": len(self._error_history),
            "recent_errors": len(recent_errors),
            "current_error_count": self._error_count,
            "is_in_fallback_mode": self._is_in_fallback_mode,
            "last_error_time": self._last_error_time,
            "error_categories": {
                cat.value: len([e for e in recent_errors if e.category == cat])
                for cat in ErrorCategory
            },
        }


class ComponentErrorHandler(UIErrorBoundary):
    """Error handler for Gradio components with fallback UI generation.

    Creates appropriate fallback UIs based on component type and error severity.
    """

    def __init__(
        self,
        component_name: str,
        component_type: str = "generic",
        fallback_message: str | None = None,
    ):
        """Initialize component error handler.

        Args:
            component_name: Name of the component
            component_type: Type of component (chat, document, feeds, etc.)
            fallback_message: Custom fallback message
        """
        super().__init__(component_name, fallback_message)
        self.component_type = component_type

    def _create_fallback_ui(self, error_info: ErrorInfo) -> Any:
        """Create appropriate fallback UI based on component type and error severity."""
        # Create fallback based on component type
        if self.component_type == "chat":
            return self._create_chat_fallback(error_info)
        elif self.component_type == "document":
            return self._create_document_fallback(error_info)
        elif self.component_type == "feeds":
            return self._create_feeds_fallback(error_info)
        else:
            return self._create_generic_fallback(error_info)

    def _create_chat_fallback(self, error_info: ErrorInfo) -> str:
        """Create fallback for chat components."""
        if error_info.severity == ErrorSeverity.CRITICAL:
            return "🚨 Chat service is currently unavailable. Please try refreshing the page or contact support."

        return f"⚠️ {error_info.user_message}. You can try asking your question again or refresh the chat interface."

    def _create_document_fallback(self, error_info: ErrorInfo) -> Any:
        """Create fallback for document components."""
        if error_info.category == ErrorCategory.PERMISSION:
            return gr.HTML(
                """
                <div style='padding: 20px; border: 1px solid #ffa500; border-radius: 5px; background-color: #fff3cd;'>
                    <h4>🔒 Document Access Issue</h4>
                    <p>There's an issue accessing documents. Please check your permissions or contact your administrator.</p>
                </div>
            """
            )

        return gr.HTML(
            f"""
            <div style='padding: 20px; border: 1px solid #dc3545; border-radius: 5px; background-color: #f8d7da;'>
                <h4>📄 Document Service Unavailable</h4>
                <p>{error_info.user_message}</p>
                <ul>
                    {''.join(f'<li>{suggestion}</li>' for suggestion in error_info.recovery_suggestions)}
                </ul>
            </div>
        """
        )

    def _create_feeds_fallback(self, error_info: ErrorInfo) -> Any:
        """Create fallback for feeds components."""
        return gr.HTML(
            f"""
            <div style='padding: 20px; border: 1px solid #6c757d; border-radius: 5px; background-color: #e2e3e5;'>
                <h4>📡 Threat Intelligence Feeds Unavailable</h4>
                <p>{error_info.user_message}</p>
                <p><small>Last updated data may still be available in cache.</small></p>
                <button onclick="location.reload()" style='margin-top: 10px; padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px;'>
                    🔄 Refresh Feeds
                </button>
            </div>
        """
        )

    def _create_generic_fallback(self, error_info: ErrorInfo) -> Any:
        """Create generic fallback UI."""
        severity_colors = {
            ErrorSeverity.LOW: "#d1ecf1",
            ErrorSeverity.MEDIUM: "#fff3cd",
            ErrorSeverity.HIGH: "#f8d7da",
            ErrorSeverity.CRITICAL: "#f5c6cb",
        }

        severity_icons = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️",
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.CRITICAL: "🚨",
        }

        return gr.HTML(
            f"""
            <div style='padding: 20px; border: 1px solid #ccc; border-radius: 5px; background-color: {severity_colors[error_info.severity]};'>
                <h4>{severity_icons[error_info.severity]} {self.component_name} Temporarily Unavailable</h4>
                <p>{error_info.user_message}</p>
                <details style='margin-top: 10px;'>
                    <summary>Recovery Options</summary>
                    <ul style='margin-top: 10px;'>
                        {''.join(f'<li>{suggestion}</li>' for suggestion in error_info.recovery_suggestions)}
                    </ul>
                </details>
            </div>
        """
        )


class ErrorReporter:
    """Centralized error reporting and logging system.
    """

    def __init__(self):
        self._error_log: list[ErrorInfo] = []
        self._error_handlers: dict[str, ComponentErrorHandler] = {}

    def register_handler(self, handler: ComponentErrorHandler) -> None:
        """Register an error handler."""
        self._error_handlers[handler.component_name] = handler
        logger.info(f"Registered error handler for {handler.component_name}")

    def report_error(self, error_info: ErrorInfo) -> None:
        """Report an error to the centralized system."""
        self._error_log.append(error_info)

        # Log based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                f"CRITICAL ERROR in {error_info.component_name}: {error_info.error_message}"
            )
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(
                f"HIGH SEVERITY ERROR in {error_info.component_name}: {error_info.error_message}"
            )
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                f"MEDIUM SEVERITY ERROR in {error_info.component_name}: {error_info.error_message}"
            )
        else:
            logger.info(
                f"Low severity error in {error_info.component_name}: {error_info.error_message}"
            )

    def get_error_dashboard(self) -> dict[str, Any]:
        """Get comprehensive error dashboard data."""
        current_time = time.time()
        recent_errors = [
            e for e in self._error_log if current_time - e.timestamp < 3600
        ]  # Last hour

        dashboard = {
            "total_errors": len(self._error_log),
            "recent_errors": len(recent_errors),
            "components_in_fallback": [
                name
                for name, handler in self._error_handlers.items()
                if handler._is_in_fallback_mode
            ],
            "error_by_category": {},
            "error_by_severity": {},
            "component_summaries": {},
        }

        # Categorize recent errors
        for category in ErrorCategory:
            dashboard["error_by_category"][category.value] = len(
                [e for e in recent_errors if e.category == category]
            )

        for severity in ErrorSeverity:
            dashboard["error_by_severity"][severity.value] = len(
                [e for e in recent_errors if e.severity == severity]
            )

        # Component summaries
        for name, handler in self._error_handlers.items():
            dashboard["component_summaries"][name] = handler.get_error_summary()

        return dashboard


# Global error reporter instance
error_reporter = ErrorReporter()


def create_error_boundary(
    component_name: str,
    component_type: str = "generic",
    fallback_message: str | None = None,
) -> ComponentErrorHandler:
    """Factory function to create and register error boundaries.

    Args:
        component_name: Name of the component to protect
        component_type: Type of component (chat, document, feeds, etc.)
        fallback_message: Custom fallback message

    Returns:
        Configured error handler
    """
    handler = ComponentErrorHandler(component_name, component_type, fallback_message)
    error_reporter.register_handler(handler)
    return handler


def with_error_boundary(component_name: str, component_type: str = "generic"):
    """Decorator to automatically wrap functions with error boundaries.

    Args:
        component_name: Name of the component
        component_type: Type of component
    """

    def decorator(func: Callable) -> Callable:
        handler = create_error_boundary(component_name, component_type)
        return handler.wrap_function(func)

    return decorator


# ============================================================================
# ERROR UI COMPONENTS (Phase 2.4)
# ============================================================================


class ErrorUIComponents:
    """Reusable error display components for consistent error presentation across the UI.

    Provides:
    - Inline error messages
    - Error toast notifications
    - Loading/error state indicators
    - Fallback UI components
    """

    @staticmethod
    def create_inline_error(
        message: str, error_type: str = "error", show_retry: bool = True
    ) -> str:
        """Create an inline error message component.

        Args:
            message: Error message to display
            error_type: Type of error (error, warning, info)
            show_retry: Whether to show retry guidance

        Returns:
            HTML string for inline error display
        """
        error_colors = {"error": "#dc3545", "warning": "#ffc107", "info": "#17a2b8"}

        error_icons = {"error": "⚠️", "warning": "⚠️", "info": "ℹ️"}

        color = error_colors.get(error_type, "#dc3545")
        icon = error_icons.get(error_type, "⚠️")

        retry_text = ""
        if show_retry and error_type == "error":
            retry_text = "<div style='font-size: 12px; margin-top: 8px; color: #666;'>Please try again or contact support if the issue persists.</div>"

        return f"""
        <div style='
            border: 1px solid {color};
            background-color: {color}15;
            color: {color};
            padding: 12px;
            border-radius: 4px;
            margin: 8px 0;
            font-size: 14px;
        '>
            <div style='display: flex; align-items: center; gap: 8px;'>
                <span style='font-size: 16px;'>{icon}</span>
                <span>{message}</span>
            </div>
            {retry_text}
        </div>
        """

    @staticmethod
    def create_error_toast(
        message: str, duration: int = 5000, error_type: str = "error"
    ) -> str:
        """Create an error toast notification.

        Args:
            message: Error message to display
            duration: Duration in milliseconds
            error_type: Type of error (error, warning, success, info)

        Returns:
            HTML string with JavaScript for toast functionality
        """
        toast_colors = {
            "error": "#dc3545",
            "warning": "#ffc107",
            "success": "#28a745",
            "info": "#17a2b8",
        }

        toast_icons = {"error": "❌", "warning": "⚠️", "success": "✅", "info": "ℹ️"}

        color = toast_colors.get(error_type, "#dc3545")
        icon = toast_icons.get(error_type, "❌")

        return f"""
        <div id="error-toast-{hash(message) % 10000}" style='
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: {color};
            color: white;
            padding: 12px 16px;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 8px;
            max-width: 400px;
            font-size: 14px;
        '>
            <span>{icon}</span>
            <span>{message}</span>
            <button onclick="this.parentElement.remove()" style='
                background: none;
                border: none;
                color: white;
                font-size: 16px;
                cursor: pointer;
                padding: 0;
                margin-left: 8px;
            '>×</button>
        </div>
        <script>
            setTimeout(function() {{
                var toast = document.getElementById('error-toast-{hash(message) % 10000}');
                if (toast) toast.remove();
            }}, {duration});
        </script>
        """

    @staticmethod
    def create_loading_state(
        message: str = "Loading...", show_spinner: bool = True
    ) -> str:
        """Create a loading state indicator.

        Args:
            message: Loading message to display
            show_spinner: Whether to show spinner animation

        Returns:
            HTML string for loading state
        """
        spinner = ""
        if show_spinner:
            spinner = """
            <div style='
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 8px;
            '></div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
            """

        return f"""
        <div style='
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
        '>
            {spinner}
            <span>{message}</span>
        </div>
        """

    @staticmethod
    def create_error_state(
        message: str,
        error_type: str = "error",
        show_retry_btn: bool = True,
        retry_action: str = None,
    ) -> str:
        """Create an error state indicator with optional retry.

        Args:
            message: Error message to display
            error_type: Type of error
            show_retry_btn: Whether to show retry button
            retry_action: JavaScript action for retry button

        Returns:
            HTML string for error state
        """
        error_colors = {"error": "#dc3545", "warning": "#ffc107", "info": "#17a2b8"}

        color = error_colors.get(error_type, "#dc3545")

        retry_button = ""
        if show_retry_btn:
            action = retry_action or "location.reload()"
            retry_button = f"""
            <button onclick="{action}" style='
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 12px;
                font-size: 12px;
            '>
                🔄 Try Again
            </button>
            """

        return f"""
        <div style='
            text-align: center;
            padding: 40px 20px;
            color: {color};
            border: 1px solid {color}30;
            border-radius: 8px;
            background-color: {color}08;
        '>
            <div style='font-size: 24px; margin-bottom: 8px;'>⚠️</div>
            <div style='font-size: 16px; margin-bottom: 8px; font-weight: 500;'>Something went wrong</div>
            <div style='font-size: 14px; color: #666; margin-bottom: 16px;'>{message}</div>
            {retry_button}
        </div>
        """

    @staticmethod
    def create_fallback_component(
        component_name: str, error_message: str = None
    ) -> str:
        """Create a fallback component when the main component fails.

        Args:
            component_name: Name of the failed component
            error_message: Specific error message

        Returns:
            HTML string for fallback component
        """
        default_message = f"{component_name} is temporarily unavailable"
        display_message = error_message or default_message

        return f"""
        <div style='
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #6c757d;
        '>
            <div style='font-size: 20px; margin-bottom: 8px;'>🔧</div>
            <div style='font-size: 16px; margin-bottom: 8px; font-weight: 500;'>{component_name} Unavailable</div>
            <div style='font-size: 14px;'>{display_message}</div>
            <div style='font-size: 12px; margin-top: 12px; color: #adb5bd;'>
                This component will automatically recover when the issue is resolved.
            </div>
        </div>
        """

    @staticmethod
    def create_status_indicator(status: str, message: str = None) -> str:
        """Create a status indicator for various states.

        Args:
            status: Status type (loading, success, error, warning)
            message: Optional status message

        Returns:
            HTML string for status indicator
        """
        status_config = {
            "loading": {"color": "#17a2b8", "icon": "🔄", "text": "Loading"},
            "success": {"color": "#28a745", "icon": "✅", "text": "Success"},
            "error": {"color": "#dc3545", "icon": "❌", "text": "Error"},
            "warning": {"color": "#ffc107", "icon": "⚠️", "text": "Warning"},
        }

        config = status_config.get(status, status_config["error"])
        display_message = message or config["text"]

        return f"""
        <div style='
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 8px;
            background-color: {config["color"]}15;
            color: {config["color"]};
            border: 1px solid {config["color"]}30;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        '>
            <span>{config["icon"]}</span>
            <span>{display_message}</span>
        </div>
        """


# ============================================================================
# ERROR UI FACTORY FUNCTIONS
# ============================================================================


def create_error_display(error_type: str, message: str, **kwargs) -> str:
    """Factory function to create error displays.

    Args:
        error_type: Type of error display (inline, toast, state, fallback, status)
        message: Error message
        **kwargs: Additional parameters for specific error types

    Returns:
        HTML string for the error display
    """
    if error_type == "inline":
        return ErrorUIComponents.create_inline_error(message, **kwargs)
    elif error_type == "toast":
        return ErrorUIComponents.create_error_toast(message, **kwargs)
    elif error_type == "loading":
        return ErrorUIComponents.create_loading_state(message, **kwargs)
    elif error_type == "state":
        return ErrorUIComponents.create_error_state(message, **kwargs)
    elif error_type == "fallback":
        return ErrorUIComponents.create_fallback_component(
            kwargs.get("component_name", "Component"), message
        )
    elif error_type == "status":
        return ErrorUIComponents.create_status_indicator(
            kwargs.get("status", "error"), message
        )
    else:
        return ErrorUIComponents.create_inline_error(
            f"Unknown error display type: {error_type}"
        )
