"""
UI Component Abstract Base Class

This module defines the foundational interface for all UI components in the Internal Assistant
system. It ensures consistency across components while maintaining Gradio framework compatibility.

The UIComponent ABC enforces a standardized pattern for:
- Component interface building (returns Gradio components)
- Event registration (handles user interactions)
- Component reference management (for cross-component communication)
- Service dependency injection (clean architecture)

Key Architectural Constraints:
- Single gr.Blocks() context maintained in main UI
- Event handlers registered in main blocks context
- Components return tuples/dictionaries for integration
- Native Gradio state management preserved
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import gradio as gr


class UIComponent(ABC):
    """
    Abstract base class for all UI components in the Internal Assistant system.

    This class defines the contract that all UI components must follow to ensure
    consistency, testability, and proper integration with the Gradio framework.

    Design Principles:
    1. Single Responsibility: Each component handles one UI concern
    2. Dependency Injection: Services injected via constructor
    3. Gradio Compatibility: Works within single gr.Blocks() context
    4. Event Separation: UI building separate from event handling
    5. Reference Management: Components expose references for integration
    """

    def __init__(self, component_id: str, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the UI component.

        Args:
            component_id: Unique identifier for this component
            services: Dictionary of injected services this component needs
        """
        self.component_id = component_id
        self.services = services or {}
        self._component_refs: Dict[str, Any] = {}
        self._is_built = False

    @abstractmethod
    def build_interface(self) -> Union[Any, Tuple[Any, ...], Dict[str, Any]]:
        """
        Build the Gradio interface components for this UI component.

        This method creates all Gradio components (textboxes, buttons, etc.) needed
        for this component's functionality. It should NOT register event handlers -
        that's handled separately in register_events().

        Returns:
            Either a single Gradio component, tuple of components, or dictionary
            mapping component names to Gradio components.

        Note:
            - Must be idempotent (safe to call multiple times)
            - Should not have side effects beyond component creation
            - Must populate self._component_refs for event registration
        """
        pass

    @abstractmethod
    def register_events(self, demo: gr.Blocks) -> None:
        """
        Register event handlers for this component within the main Gradio blocks.

        This method sets up all click handlers, change events, and other interactions
        for the components created in build_interface(). All event registration must
        happen within the provided gr.Blocks context.

        Args:
            demo: The main gr.Blocks context where events should be registered

        Note:
            - Must be called after build_interface()
            - Events registered here will be active in the main UI
            - Should use self._component_refs to access components
        """
        pass

    @abstractmethod
    def get_component_refs(self) -> Dict[str, Any]:
        """
        Get references to this component's Gradio components.

        This enables other components or the main UI to interact with this
        component's elements (e.g., updating values, triggering events).

        Returns:
            Dictionary mapping component names to Gradio component instances

        Example:
            {
                "chat_input": gr.Textbox(...),
                "send_button": gr.Button(...),
                "chat_history": gr.Chatbot(...)
            }
        """
        pass

    def is_built(self) -> bool:
        """Check if this component has been built."""
        return self._is_built

    def get_service(self, service_name: str) -> Any:
        """
        Get an injected service by name.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            The requested service instance

        Raises:
            KeyError: If the service is not available
        """
        if service_name not in self.services:
            raise KeyError(
                f"Service '{service_name}' not available in {self.component_id}"
            )
        return self.services[service_name]

    def has_service(self, service_name: str) -> bool:
        """Check if a service is available."""
        return service_name in self.services

    def validate_dependencies(self) -> List[str]:
        """
        Validate that all required services are available.

        Returns:
            List of missing service names (empty if all dependencies met)
        """
        missing = []
        for required_service in self.get_required_services():
            if not self.has_service(required_service):
                missing.append(required_service)
        return missing

    def get_required_services(self) -> List[str]:
        """
        Get list of service names this component requires.

        Override this method to specify dependencies.

        Returns:
            List of required service names
        """
        return []

    def _mark_built(self) -> None:
        """Mark this component as built (internal use)."""
        self._is_built = True

    def _store_component_ref(self, name: str, component: Any) -> None:
        """Store a reference to a Gradio component (internal use)."""
        self._component_refs[name] = component


class StatefulUIComponent(UIComponent):
    """
    Extended UI component that includes state management capabilities.

    This class provides additional functionality for components that need to
    maintain internal state beyond basic Gradio component state.
    """

    def __init__(self, component_id: str, services: Optional[Dict[str, Any]] = None):
        super().__init__(component_id, services)
        self._state: Dict[str, Any] = {}

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value."""
        self._state[key] = value

    def get_all_state(self) -> Dict[str, Any]:
        """Get all state as a dictionary."""
        return self._state.copy()

    def clear_state(self) -> None:
        """Clear all component state."""
        self._state.clear()


class ServiceContainer:
    """
    Simple service container for dependency injection.

    This class holds references to application services and provides them
    to UI components that need them.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """Get a service by name."""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        return self._services[name]

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def get_all(self) -> Dict[str, Any]:
        """Get all services as a dictionary."""
        return self._services.copy()
