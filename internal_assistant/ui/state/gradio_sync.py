"""
Gradio-State Synchronization System

This module provides automatic synchronization between the centralized state
management system and Gradio UI components. It solves the critical issue where
state changes don't automatically update UI components.

Part of Phase 2.5: State Management Integration Fix
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from threading import Lock
import gradio as gr
from dataclasses import dataclass, field
from collections import defaultdict

from .state_manager import StateObserver, StateChange, StateStore
from .app_state import ApplicationState

logger = logging.getLogger(__name__)


@dataclass
class ComponentBinding:
    """Represents a binding between a Gradio component and a state path."""

    component_name: str
    component_ref: Any  # Gradio component reference
    state_path: str
    transform_to_ui: Optional[Callable[[Any], Any]] = (
        None  # Transform state value for UI
    )
    transform_from_ui: Optional[Callable[[Any], Any]] = (
        None  # Transform UI value for state
    )
    update_trigger: Optional[Any] = None  # Component event that triggers state update


class GradioStateSync:
    """
    Manages synchronization between Gradio components and centralized state.

    This class solves the critical issue where state observers can't directly
    update Gradio components. Instead, it maintains a queue of pending updates
    and provides methods to apply them through Gradio's proper update mechanism.
    """

    def __init__(self, state_store: StateStore):
        """
        Initialize Gradio state synchronization.

        Args:
            state_store: The centralized state store to sync with
        """
        self.state_store = state_store
        self._bindings: Dict[str, ComponentBinding] = {}
        self._state_to_components: Dict[str, List[str]] = defaultdict(list)
        self._pending_updates: Dict[str, Any] = {}
        self._update_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = Lock()
        self._observers: Dict[str, StateObserver] = {}

        logger.info("GradioStateSync initialized")

    def bind_component(
        self,
        component_name: str,
        component_ref: Any,
        state_path: str,
        bidirectional: bool = True,
        transform_to_ui: Optional[Callable[[Any], Any]] = None,
        transform_from_ui: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        """
        Bind a Gradio component to a state path with automatic synchronization.

        Args:
            component_name: Unique name for the component
            component_ref: Gradio component reference
            state_path: Path in state to bind to
            bidirectional: If True, component changes update state
            transform_to_ui: Optional transform for state->UI values
            transform_from_ui: Optional transform for UI->state values
        """
        with self._lock:
            # Create binding
            binding = ComponentBinding(
                component_name=component_name,
                component_ref=component_ref,
                state_path=state_path,
                transform_to_ui=transform_to_ui,
                transform_from_ui=transform_from_ui,
            )

            self._bindings[component_name] = binding
            self._state_to_components[state_path].append(component_name)

            # Create state observer for this binding
            observer = self._create_component_observer(component_name)
            self._observers[component_name] = observer
            self.state_store.subscribe(state_path, observer)

            logger.info(
                f"Bound Gradio component '{component_name}' to state path '{state_path}'"
            )

            # DEFERRED: Don't set initial values during bind to avoid triggering callbacks
            # that might make blocking calls. Initial values will be set after UI mount.
            # current_value = self.state_store.get(state_path)
            # if current_value is not None:
            #     self._queue_update(component_name, current_value)

    def _create_component_observer(self, component_name: str) -> StateObserver:
        """Create a state observer for a specific component."""

        class ComponentObserver(StateObserver):
            def __init__(self, sync_manager, comp_name):
                self.sync_manager = sync_manager
                self.comp_name = comp_name

            def on_state_change(
                self, path: str, old_value: Any, new_value: Any, change: StateChange
            ) -> None:
                """Handle state change by queueing UI update."""
                self.sync_manager._queue_update(self.comp_name, new_value)
                logger.debug(
                    f"State change detected for {self.comp_name}: {path} = {new_value}"
                )

        return ComponentObserver(self, component_name)

    def _queue_update(self, component_name: str, value: Any) -> None:
        """Queue a UI update for a component."""
        with self._lock:
            binding = self._bindings.get(component_name)
            if not binding:
                return

            # Transform value if needed
            if binding.transform_to_ui:
                try:
                    value = binding.transform_to_ui(value)
                except Exception as e:
                    logger.error(f"Transform error for {component_name}: {e}")
                    return

            # Queue the update
            self._pending_updates[component_name] = value

            # Trigger any registered callbacks
            for callback in self._update_callbacks.get(component_name, []):
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Update callback error for {component_name}: {e}")

    def get_pending_updates(self) -> Dict[str, Any]:
        """
        Get all pending UI updates and clear the queue.

        Returns:
            Dictionary of component names to their new values
        """
        with self._lock:
            updates = self._pending_updates.copy()
            self._pending_updates.clear()
            return updates

    def create_update_handler(self, component_names: List[str]) -> Callable:
        """
        Create a Gradio event handler that applies pending updates.

        This is the key to making state changes update the UI. Use this
        handler in Gradio event callbacks to apply state changes.

        Args:
            component_names: List of component names to update

        Returns:
            Handler function that returns updated values for components
        """

        def handler(*args) -> Tuple[Any, ...]:
            updates = self.get_pending_updates()
            results = []

            for comp_name in component_names:
                if comp_name in updates:
                    results.append(updates[comp_name])
                else:
                    # Return current value if no update pending
                    binding = self._bindings.get(comp_name)
                    if binding:
                        current = self.state_store.get(binding.state_path)
                        if binding.transform_to_ui:
                            current = binding.transform_to_ui(current)
                        results.append(current)
                    else:
                        results.append(gr.update())  # No change

            return (
                tuple(results)
                if len(results) > 1
                else results[0] if results else gr.update()
            )

        return handler

    def create_state_update_handler(
        self, component_name: str, state_path: str
    ) -> Callable:
        """
        Create a handler that updates state when a component changes.

        Args:
            component_name: Name of the component
            state_path: State path to update

        Returns:
            Handler function for component change events
        """

        def handler(value: Any) -> Any:
            binding = self._bindings.get(component_name)

            # Transform value if needed
            if binding and binding.transform_from_ui:
                try:
                    value = binding.transform_from_ui(value)
                except Exception as e:
                    logger.error(f"Transform error for {component_name}: {e}")
                    return value

            # Update state
            self.state_store.set(state_path, value, source=f"ui.{component_name}")
            logger.debug(
                f"State updated from component {component_name}: {state_path} = {value}"
            )

            return value

        return handler

    def register_update_callback(
        self, component_name: str, callback: Callable[[Any], None]
    ) -> None:
        """
        Register a callback to be called when a component needs updating.

        This is useful for complex components that need custom update logic.

        Args:
            component_name: Name of the component
            callback: Function to call with new value
        """
        with self._lock:
            self._update_callbacks[component_name].append(callback)
            logger.debug(f"Registered update callback for {component_name}")

    def sync_all_components(self) -> Dict[str, Any]:
        """
        Get current values for all bound components from state.

        Returns:
            Dictionary of component names to their current values
        """
        values = {}
        with self._lock:
            for comp_name, binding in self._bindings.items():
                try:
                    value = self.state_store.get(binding.state_path)
                    if binding.transform_to_ui:
                        value = binding.transform_to_ui(value)
                    values[comp_name] = value
                except Exception as e:
                    logger.error(f"Error syncing {comp_name}: {e}")
                    values[comp_name] = None

        return values

    def create_periodic_sync_handler(
        self, component_names: List[str], interval_ms: int = 500
    ) -> Tuple[Callable, Any]:
        """
        Create a periodic sync handler that updates components at regular intervals.

        This ensures UI stays in sync even if individual updates are missed.

        Args:
            component_names: Components to sync
            interval_ms: Update interval in milliseconds

        Returns:
            Tuple of (handler function, Timer component)
        """

        def sync_handler() -> Tuple[Any, ...]:
            values = self.sync_all_components()
            results = []

            for comp_name in component_names:
                if comp_name in values:
                    results.append(values[comp_name])
                else:
                    results.append(gr.update())

            return (
                tuple(results)
                if len(results) > 1
                else results[0] if results else gr.update()
            )

        # Create timer component (placeholder - use actual Gradio timer in real implementation)
        timer = None  # Would be gr.Timer in actual implementation

        return sync_handler, timer

    def unbind_component(self, component_name: str) -> None:
        """
        Remove a component binding and its observer.

        Args:
            component_name: Name of component to unbind
        """
        with self._lock:
            binding = self._bindings.get(component_name)
            if not binding:
                return

            # Unsubscribe observer
            observer = self._observers.get(component_name)
            if observer:
                self.state_store.unsubscribe(binding.state_path, observer)
                del self._observers[component_name]

            # Remove binding
            del self._bindings[component_name]
            self._state_to_components[binding.state_path].remove(component_name)

            # Clear any pending updates
            if component_name in self._pending_updates:
                del self._pending_updates[component_name]

            logger.info(f"Unbound component '{component_name}'")


def create_gradio_sync(state_store: StateStore) -> GradioStateSync:
    """
    Factory function to create a GradioStateSync instance.

    Args:
        state_store: The state store to sync with

    Returns:
        Configured GradioStateSync instance
    """
    return GradioStateSync(state_store)
