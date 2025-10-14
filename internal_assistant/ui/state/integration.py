"""
State Integration Utilities

This module provides utilities for integrating the new centralized state management
system with existing UI components and migrating from scattered state variables.

Part of Phase 2.2: State Schema Design and Implementation  
Author: UI Refactoring Team
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from internal_assistant.ui.state.app_state import (
    ApplicationState,
    ChatMessage,
    DocumentMetadata,
    FeedItem,
    CVEInfo,
    create_default_application_state,
    create_application_state_from_legacy,
)
from internal_assistant.ui.state.state_manager import (
    StateStore,
    StateObserver,
    StateChange,
)
from internal_assistant.ui.state.selectors import register_all_selectors

logger = logging.getLogger(__name__)


class UIStateObserver(StateObserver):
    """Observer that updates UI components when state changes."""

    def __init__(self, update_callback: Callable[[str, Any, Any], None]):
        """
        Initialize UI state observer.

        Args:
            update_callback: Function to call when state changes
                            Signature: (path: str, old_value: Any, new_value: Any) -> None
        """
        self.update_callback = update_callback

    def on_state_change(
        self, path: str, old_value: Any, new_value: Any, change: StateChange
    ) -> None:
        """Handle state change by updating UI components."""
        try:
            self.update_callback(path, old_value, new_value)
            logger.debug(f"UI updated for state change: {path}")
        except Exception as e:
            logger.error(f"Failed to update UI for state change {path}: {e}")


class StateIntegrationManager:
    """
    Manages integration between the new state system and existing UI components.

    This class provides a bridge between the centralized state management system
    and the scattered Gradio components throughout the existing UI.
    """

    def __init__(self, initial_state: Optional[ApplicationState] = None):
        """
        Initialize the state integration manager.

        Args:
            initial_state: Optional initial application state
        """
        self.app_state = initial_state or create_default_application_state()
        self.state_store = StateStore(self.app_state.dict())

        # Component reference mapping
        self._component_refs: Dict[str, Any] = {}
        self._state_to_component_map: Dict[str, List[str]] = {}
        self._component_to_state_map: Dict[str, str] = {}

        # UI update callbacks
        self._ui_observers: List[UIStateObserver] = []

        # Register all selectors
        register_all_selectors(self.state_store)

        logger.info("StateIntegrationManager initialized")

    def register_component(
        self, component_name: str, component_ref: Any, state_path: Optional[str] = None
    ) -> None:
        """
        Register a UI component with the state system.

        Args:
            component_name: Name/ID of the component
            component_ref: Reference to the Gradio component
            state_path: Optional state path this component is bound to
        """
        self._component_refs[component_name] = component_ref

        if state_path:
            self._component_to_state_map[component_name] = state_path

            if state_path not in self._state_to_component_map:
                self._state_to_component_map[state_path] = []
            self._state_to_component_map[state_path].append(component_name)

        logger.debug(f"Registered component: {component_name} -> {state_path}")

    def register_ui_observer(
        self, callback: Callable[[str, Any, Any], None]
    ) -> UIStateObserver:
        """
        Register a UI observer callback.

        Args:
            callback: Function to call when state changes

        Returns:
            Created UIStateObserver instance
        """
        observer = UIStateObserver(callback)
        self._ui_observers.append(observer)

        # Subscribe to all state changes
        self.state_store.subscribe("*", observer)

        logger.debug("UI observer registered")
        return observer

    def bind_component_to_state(
        self, component_name: str, state_path: str, bidirectional: bool = True
    ) -> None:
        """
        Bind a component to a state path for automatic updates.

        Args:
            component_name: Name of the component to bind
            state_path: State path to bind to
            bidirectional: Whether changes in component should update state
        """
        if component_name not in self._component_refs:
            logger.warning(f"Component {component_name} not registered")
            return

        # Store the binding
        self._component_to_state_map[component_name] = state_path

        if state_path not in self._state_to_component_map:
            self._state_to_component_map[state_path] = []
        self._state_to_component_map[state_path].append(component_name)

        # Create observer for this specific binding
        def update_component(path: str, old_value: Any, new_value: Any) -> None:
            if path == state_path:
                try:
                    component = self._component_refs[component_name]
                    if hasattr(component, "update"):
                        component.update(value=new_value)
                    elif hasattr(component, "value"):
                        component.value = new_value
                    logger.debug(
                        f"Updated component {component_name} with value: {new_value}"
                    )
                except Exception as e:
                    logger.error(f"Failed to update component {component_name}: {e}")

        observer = UIStateObserver(update_component)
        self.state_store.subscribe(state_path, observer)

        logger.info(f"Bound component {component_name} to state {state_path}")

    def update_state_from_component(self, component_name: str, value: Any) -> None:
        """
        Update state when a component value changes.

        Args:
            component_name: Name of the component that changed
            value: New value from the component
        """
        if component_name not in self._component_to_state_map:
            logger.debug(f"Component {component_name} not bound to state")
            return

        state_path = self._component_to_state_map[component_name]
        try:
            self.state_store.set(
                state_path, value, source=f"component:{component_name}"
            )
            # Update the app_state object
            self._sync_state_to_app_state()
            logger.debug(f"Updated state {state_path} from component {component_name}")
        except Exception as e:
            logger.error(f"Failed to update state from component {component_name}: {e}")

    def get_state_value(self, path: str, default: Any = None) -> Any:
        """
        Get a value from the state.

        Args:
            path: State path to retrieve
            default: Default value if path doesn't exist

        Returns:
            Value at the state path
        """
        return self.state_store.get(path, default)

    def set_state_value(
        self, path: str, value: Any, source: Optional[str] = None
    ) -> None:
        """
        Set a value in the state.

        Args:
            path: State path to set
            value: Value to set
            source: Optional source identifier
        """
        self.state_store.set(path, value, source)
        self._sync_state_to_app_state()

    def update_state_values(
        self, updates: Dict[str, Any], source: Optional[str] = None
    ) -> None:
        """
        Update multiple state values atomically.

        Args:
            updates: Dictionary of path -> value updates
            source: Optional source identifier
        """
        self.state_store.update(updates, source)
        self._sync_state_to_app_state()

    def select(self, selector_name: str) -> Any:
        """
        Get a computed value from a registered selector.

        Args:
            selector_name: Name of the selector

        Returns:
            Computed value
        """
        return self.state_store.select(selector_name)

    def migrate_from_legacy_ui(self, legacy_ui_instance: Any) -> None:
        """
        Migrate state from a legacy UI instance.

        Args:
            legacy_ui_instance: Instance of the old UI class with scattered state
        """
        try:
            # Extract common legacy state variables
            legacy_values = {}

            # Try to extract common attributes
            for attr_name in [
                "mode",
                "_default_mode",
                "system_prompt",
                "_system_prompt",
            ]:
                if hasattr(legacy_ui_instance, attr_name):
                    value = getattr(legacy_ui_instance, attr_name)
                    if attr_name in ["mode", "_default_mode"]:
                        legacy_values["legacy_mode"] = value
                    elif attr_name in ["system_prompt", "_system_prompt"]:
                        legacy_values["legacy_system_prompt"] = value

            # Create new state from legacy values
            new_app_state = create_application_state_from_legacy(**legacy_values)

            # Update our state
            self.app_state = new_app_state
            self.state_store.import_state(
                new_app_state.dict(), source="legacy_migration"
            )

            logger.info("Successfully migrated from legacy UI state")

        except Exception as e:
            logger.error(f"Failed to migrate from legacy UI: {e}")

    def extract_gradio_state(self, gradio_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract current values from Gradio components.

        Args:
            gradio_components: Dictionary of component_name -> component_ref

        Returns:
            Dictionary of component values
        """
        extracted_state = {}

        for name, component in gradio_components.items():
            try:
                if hasattr(component, "value"):
                    extracted_state[name] = component.value
                elif hasattr(component, "choices") and hasattr(component, "value"):
                    # Handle Radio, Dropdown, etc.
                    extracted_state[name] = component.value
                else:
                    logger.debug(f"Could not extract value from component: {name}")
            except Exception as e:
                logger.warning(f"Error extracting value from {name}: {e}")

        return extracted_state

    def sync_with_gradio_state(self, gradio_state_dict: Dict[str, Any]) -> None:
        """
        Synchronize our state with values from Gradio state.

        Args:
            gradio_state_dict: Dictionary of component values from Gradio
        """
        # Map common Gradio component names to state paths
        gradio_to_state_map = {
            "mode_selector": "chat.mode",
            "system_prompt": "settings.system_prompt",
            "temperature": "settings.chat.temperature",
            "similarity_threshold": "settings.rag.similarity_threshold",
            "citation_style": "settings.chat.citation_style",
            "current_filter_type": "documents.filter.type",
            "current_search_query": "documents.filter.search_query",
        }

        updates = {}
        for gradio_name, state_path in gradio_to_state_map.items():
            if gradio_name in gradio_state_dict:
                updates[state_path] = gradio_state_dict[gradio_name]

        if updates:
            self.update_state_values(updates, source="gradio_sync")
            logger.info(f"Synced {len(updates)} values from Gradio state")

    def create_gradio_update_handler(self, component_name: str) -> Callable[[Any], Any]:
        """
        Create a handler function for Gradio component updates.

        Args:
            component_name: Name of the component

        Returns:
            Handler function that can be used as a Gradio callback
        """

        def handler(new_value: Any) -> Any:
            self.update_state_from_component(component_name, new_value)
            return new_value

        return handler

    def get_component_ref(self, component_name: str) -> Any:
        """
        Get a reference to a registered component.

        Args:
            component_name: Name of the component

        Returns:
            Component reference or None if not found
        """
        return self._component_refs.get(component_name)

    def _sync_state_to_app_state(self) -> None:
        """Synchronize the state store with the app_state object."""
        try:
            # PERFORMANCE FIX: Don't recreate the entire ApplicationState object
            # on every state change - this causes expensive Pydantic validation
            # and blocks the UI initialization.
            # Instead, rely on state_store as the single source of truth.

            # Just update the activity timestamp
            self.app_state.update_activity_timestamp()

        except Exception as e:
            logger.error(f"Failed to sync state to app_state: {e}")

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state.

        Returns:
            State summary dictionary
        """
        return self.app_state.get_summary()

    def export_state_for_persistence(self) -> Dict[str, Any]:
        """
        Export state for persistence/debugging.

        Returns:
            Serializable state dictionary
        """
        return {
            "app_state": self.app_state.dict(),
            "state_store": self.state_store.export_state(),
            "component_bindings": self._component_to_state_map,
            "export_timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# Helper Functions for Common Migrations
# ============================================================================


def create_chat_state_from_history(
    history: List[List[str]], mode: str = "RAG Mode"
) -> Dict[str, Any]:
    """
    Create chat state from legacy history format.

    Args:
        history: List of [user_message, assistant_message] pairs
        mode: Chat mode

    Returns:
        Chat state dictionary
    """
    messages = []
    for i, (user_msg, assistant_msg) in enumerate(history):
        if user_msg:
            messages.append(
                ChatMessage(
                    role="user",
                    content=user_msg,
                    timestamp=datetime.now(),  # Would need actual timestamps
                )
            )

        if assistant_msg:
            messages.append(
                ChatMessage(
                    role="assistant", content=assistant_msg, timestamp=datetime.now()
                )
            )

    return {
        "chat.mode": mode,
        "chat.history": history,
        "chat.messages": [msg.dict() for msg in messages],
        "chat.is_processing": False,
    }


def migrate_document_metadata(legacy_files: List[Any]) -> Dict[str, Any]:
    """
    Migrate legacy document file list to new metadata format.

    Args:
        legacy_files: List of legacy file data

    Returns:
        Document state updates
    """
    documents = {}
    counts = {
        "total": 0,
        "pdf_count": 0,
        "docx_count": 0,
        "txt_count": 0,
        "other_count": 0,
    }

    for i, file_data in enumerate(legacy_files or []):
        if not file_data or len(file_data) == 0:
            continue

        file_name = file_data[0] if len(file_data) > 0 else f"unknown_{i}"
        doc_id = f"doc_{i}"

        # Determine file type
        file_type = "other"
        if file_name.lower().endswith(".pdf"):
            file_type = "pdf"
            counts["pdf_count"] += 1
        elif file_name.lower().endswith(".docx"):
            file_type = "docx"
            counts["docx_count"] += 1
        elif file_name.lower().endswith(".txt"):
            file_type = "txt"
            counts["txt_count"] += 1
        else:
            counts["other_count"] += 1

        documents[doc_id] = DocumentMetadata(
            doc_id=doc_id,
            file_name=file_name,
            file_type=file_type,
            upload_date=datetime.now(),
        ).dict()

        counts["total"] += 1

    return {"documents.documents": documents, "documents.counts": counts}


def setup_state_integration(ui_instance: Any) -> StateIntegrationManager:
    """
    Set up state integration for an existing UI instance.

    Args:
        ui_instance: Existing UI instance to integrate with

    Returns:
        Configured StateIntegrationManager
    """
    # Create manager
    manager = StateIntegrationManager()

    # Migrate legacy state if possible
    try:
        manager.migrate_from_legacy_ui(ui_instance)
    except Exception as e:
        logger.warning(f"Could not migrate legacy state: {e}")

    # Set up common component bindings (would be customized per UI)
    # This would be expanded based on actual UI structure

    logger.info("State integration setup complete")
    return manager
