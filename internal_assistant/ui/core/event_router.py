"""Event Router

This module provides centralized event handling and routing for the Internal Assistant
UI system. It manages the complex web of Gradio event handlers while maintaining
clean separation between UI components.

The EventRouter ensures:
- Event handlers are registered in the correct Gradio context
- Cross-component communication is handled cleanly
- Event conflicts are avoided
- Component events can be easily debugged and traced
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)


class EventHandler:
    """Wrapper for event handler functions with metadata.

    This class provides additional functionality around event handlers,
    including logging, error handling, and performance monitoring.
    """

    def __init__(
        self,
        handler_func: Callable,
        component_id: str,
        event_type: str,
        description: str | None = None,
    ):
        """Initialize an event handler.

        Args:
            handler_func: The actual handler function
            component_id: ID of the component that owns this handler
            event_type: Type of event (click, change, submit, etc.)
            description: Optional description for debugging
        """
        self.handler_func = handler_func
        self.component_id = component_id
        self.event_type = event_type
        self.description = description or f"{component_id}_{event_type}"
        self.call_count = 0

        # Wrap the handler for logging and monitoring
        self.wrapped_handler = self._wrap_handler(handler_func)

    def _wrap_handler(self, func: Callable) -> Callable:
        """Wrap a handler function with logging and error handling.

        Args:
            func: Original handler function

        Returns:
            Wrapped handler function
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.call_count += 1
            logger.debug(
                f"Event handler called: {self.description} (#{self.call_count})"
            )

            try:
                result = func(*args, **kwargs)
                logger.debug(f"Event handler completed: {self.description}")
                return result
            except Exception as e:
                logger.error(f"Event handler failed: {self.description}, Error: {e}")
                raise

        return wrapper

    def __call__(self, *args, **kwargs):
        """Make the EventHandler callable."""
        return self.wrapped_handler(*args, **kwargs)


class EventRouter:
    """Central router for managing UI event handlers.

    This class provides a structured way to register, organize, and manage
    event handlers across multiple UI components. It ensures proper event
    registration within the Gradio framework constraints.
    """

    def __init__(self):
        """Initialize the event router."""
        self._handlers: dict[str, list[EventHandler]] = {}
        self._registered_events: list[tuple[str, str, Any]] = []
        self._component_refs: dict[str, dict[str, Any]] = {}

    def register_handler(
        self,
        component_id: str,
        event_type: str,
        handler_func: Callable,
        description: str | None = None,
    ) -> EventHandler:
        """Register an event handler for a component.

        Args:
            component_id: ID of the component
            event_type: Type of event (click, change, submit, etc.)
            handler_func: Function to handle the event
            description: Optional description for debugging

        Returns:
            The created EventHandler instance
        """
        handler = EventHandler(handler_func, component_id, event_type, description)

        if component_id not in self._handlers:
            self._handlers[component_id] = []

        self._handlers[component_id].append(handler)

        logger.debug(f"Registered event handler: {handler.description}")
        return handler

    def register_component_refs(self, component_id: str, refs: dict[str, Any]) -> None:
        """Register component references for event binding.

        Args:
            component_id: ID of the component
            refs: Dictionary of component references
        """
        self._component_refs[component_id] = refs
        logger.debug(f"Registered component refs for: {component_id}")

    def bind_events(self, demo: gr.Blocks) -> None:
        """Bind all registered event handlers to their components within the Gradio context.

        Args:
            demo: The main gr.Blocks context where events should be registered
        """
        for component_id, handlers in self._handlers.items():
            component_refs = self._component_refs.get(component_id, {})

            for handler in handlers:
                self._bind_single_event(demo, component_id, handler, component_refs)

    def _bind_single_event(
        self,
        demo: gr.Blocks,
        component_id: str,
        handler: EventHandler,
        component_refs: dict[str, Any],
    ) -> None:
        """Bind a single event handler to its component.

        Args:
            demo: Gradio blocks context
            component_id: ID of the component
            handler: Event handler to bind
            component_refs: Component references for this component
        """
        try:
            # This is where we'd implement the actual event binding logic
            # The specific implementation depends on the event type and component structure

            event_info = (component_id, handler.event_type, handler.description)
            self._registered_events.append(event_info)

            logger.debug(f"Bound event: {handler.description}")

        except Exception as e:
            logger.error(f"Failed to bind event {handler.description}: {e}")

    def get_handlers_for_component(self, component_id: str) -> list[EventHandler]:
        """Get all event handlers for a specific component.

        Args:
            component_id: ID of the component

        Returns:
            List of event handlers for the component
        """
        return self._handlers.get(component_id, [])

    def get_all_handlers(self) -> dict[str, list[EventHandler]]:
        """Get all registered event handlers."""
        return self._handlers.copy()

    def get_registered_events(self) -> list[tuple[str, str, Any]]:
        """Get list of all registered events."""
        return self._registered_events.copy()

    def remove_component_handlers(self, component_id: str) -> None:
        """Remove all event handlers for a component.

        Args:
            component_id: ID of the component
        """
        if component_id in self._handlers:
            del self._handlers[component_id]
            logger.debug(f"Removed all handlers for component: {component_id}")

    def get_handler_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics about event handler usage.

        Returns:
            Dictionary with handler statistics
        """
        stats = {}

        for component_id, handlers in self._handlers.items():
            component_stats = {
                "handler_count": len(handlers),
                "event_types": list(set(h.event_type for h in handlers)),
                "total_calls": sum(h.call_count for h in handlers),
                "handlers": [
                    {
                        "description": h.description,
                        "event_type": h.event_type,
                        "call_count": h.call_count,
                    }
                    for h in handlers
                ],
            }
            stats[component_id] = component_stats

        return stats


class EventBridge:
    """Bridge for handling cross-component communication.

    This class provides a way for components to communicate with each other
    through events without direct coupling.
    """

    def __init__(self, router: EventRouter):
        """Initialize the event bridge.

        Args:
            router: The main event router
        """
        self.router = router
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe to a cross-component event.

        Args:
            event_name: Name of the event to subscribe to
            callback: Function to call when event occurs
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(callback)
        logger.debug(f"Subscribed to event: {event_name}")

    def publish(self, event_name: str, data: Any = None) -> None:
        """Publish a cross-component event.

        Args:
            event_name: Name of the event
            data: Optional data to pass to subscribers
        """
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event subscriber failed for {event_name}: {e}")

        logger.debug(f"Published event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe from a cross-component event.

        Args:
            event_name: Name of the event
            callback: Callback function to remove
        """
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_name}")
            except ValueError:
                logger.warning(f"Callback not found for event: {event_name}")


def create_gradio_event_helper():
    """Create helper functions for common Gradio event patterns.

    Returns:
        Dictionary of helper functions for Gradio events
    """

    def create_click_handler(
        component: Any,
        handler: Callable,
        inputs: list[Any] | None = None,
        outputs: list[Any] | None = None,
    ) -> None:
        """Helper for creating click event handlers."""
        component.click(fn=handler, inputs=inputs or [], outputs=outputs or [])

    def create_change_handler(
        component: Any,
        handler: Callable,
        inputs: list[Any] | None = None,
        outputs: list[Any] | None = None,
    ) -> None:
        """Helper for creating change event handlers."""
        component.change(fn=handler, inputs=inputs or [], outputs=outputs or [])

    def create_submit_handler(
        component: Any,
        handler: Callable,
        inputs: list[Any] | None = None,
        outputs: list[Any] | None = None,
    ) -> None:
        """Helper for creating submit event handlers."""
        component.submit(fn=handler, inputs=inputs or [], outputs=outputs or [])

    return {
        "click": create_click_handler,
        "change": create_change_handler,
        "submit": create_submit_handler,
    }
