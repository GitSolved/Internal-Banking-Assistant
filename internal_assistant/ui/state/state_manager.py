"""State Manager

This module provides centralized state management for the Internal Assistant UI.
It implements an observer pattern with state validation, persistence, and debugging
capabilities to replace the scattered state management throughout the UI.

Part of Phase 2: State Management System refactoring.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StateChangeType(str, Enum):
    """Types of state changes for debugging and logging."""

    SET = "SET"
    UPDATE = "UPDATE"
    RESET = "RESET"
    MERGE = "MERGE"
    DELETE = "DELETE"


@dataclass
class StateChange:
    """Represents a single state change for debugging and history."""

    timestamp: datetime
    change_type: StateChangeType
    path: str
    old_value: Any
    new_value: Any
    source: str | None = None  # Component or handler that triggered the change

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type.value,
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
        }


class StateObserver(ABC):
    """Abstract base class for state observers."""

    @abstractmethod
    def on_state_change(
        self, path: str, old_value: Any, new_value: Any, change: StateChange
    ) -> None:
        """Called when observed state changes."""
        pass


class StateSelector(ABC, Generic[T]):
    """Abstract base class for state selectors that compute derived values."""

    @abstractmethod
    def select(self, state: dict[str, Any]) -> T:
        """Compute and return the derived value from state."""
        pass

    @abstractmethod
    def get_dependencies(self) -> set[str]:
        """Return set of state paths this selector depends on."""
        pass


class MemoizedSelector(StateSelector[T]):
    """A selector that memoizes its result until dependencies change."""

    def __init__(
        self, selector_func: Callable[[dict[str, Any]], T], dependencies: set[str]
    ):
        """Initialize memoized selector.

        Args:
            selector_func: Function that computes the derived value
            dependencies: Set of state paths this selector depends on
        """
        self.selector_func = selector_func
        self.dependencies = dependencies
        self._cached_value: T | None = None
        self._cache_valid = False
        self._last_state_hash: str | None = None

    def select(self, state: dict[str, Any]) -> T:
        """Get the computed value, using cache if dependencies haven't changed."""
        # Create hash of dependency values to check for changes
        dep_values = {}
        for path in self.dependencies:
            dep_values[path] = self._get_nested_value(state, path)

        current_hash = str(hash(str(sorted(dep_values.items()))))

        if not self._cache_valid or self._last_state_hash != current_hash:
            self._cached_value = self.selector_func(state)
            self._cache_valid = True
            self._last_state_hash = current_hash
            logger.debug(f"Selector recomputed for dependencies: {self.dependencies}")

        return self._cached_value

    def get_dependencies(self) -> set[str]:
        """Return the set of dependencies."""
        return self.dependencies

    def invalidate(self) -> None:
        """Manually invalidate the cache."""
        self._cache_valid = False

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value


class StateStore:
    """Central state store with observer pattern, validation, and persistence.

    This replaces the scattered state management throughout the UI with a
    centralized, predictable state management solution.
    """

    def __init__(self, initial_state: dict[str, Any] | None = None):
        """Initialize the state store.

        Args:
            initial_state: Initial state dictionary
        """
        self._state: dict[str, Any] = initial_state or {}
        self._observers: dict[str, list[StateObserver]] = {}
        self._selectors: dict[str, StateSelector] = {}
        self._change_history: list[StateChange] = []
        self._lock = Lock()
        self._max_history = 1000  # Limit history size

        # Validation schemas (can be extended)
        self._validators: dict[str, Callable[[Any], bool]] = {}

        logger.info("StateStore initialized")

    def get(self, path: str, default: Any = None) -> Any:
        """Get value from state using dot notation.

        Args:
            path: Dot-separated path to the value (e.g., 'chat.mode')
            default: Default value if path doesn't exist

        Returns:
            The value at the path or default
        """
        with self._lock:
            keys = path.split(".")
            value = self._state

            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default

            return value

    def set(self, path: str, value: Any, source: str | None = None) -> None:
        """Set value in state using dot notation.

        Args:
            path: Dot-separated path to set (e.g., 'chat.mode')
            value: Value to set
            source: Optional source identifier for debugging
        """
        with self._lock:
            # Validate the new value
            if path in self._validators:
                if not self._validators[path](value):
                    raise ValueError(
                        f"Validation failed for path '{path}' with value: {value}"
                    )

            old_value = self.get(path)

            # Set the nested value
            keys = path.split(".")
            current = self._state

            # Navigate to parent
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Set the final value
            current[keys[-1]] = value

            # Record the change
            change = StateChange(
                timestamp=datetime.now(),
                change_type=StateChangeType.SET,
                path=path,
                old_value=old_value,
                new_value=value,
                source=source,
            )

            self._add_change_to_history(change)

            # Notify observers
            self._notify_observers(path, old_value, value, change)

            # Invalidate relevant selectors
            self._invalidate_selectors_for_path(path)

            logger.debug(f"State set: {path} = {value} (source: {source})")

    def update(self, updates: dict[str, Any], source: str | None = None) -> None:
        """Update multiple state values atomically.

        Args:
            updates: Dictionary of path -> value updates
            source: Optional source identifier for debugging
        """
        with self._lock:
            for path, value in updates.items():
                self.set(path, value, source)

    def merge(
        self, path: str, updates: dict[str, Any], source: str | None = None
    ) -> None:
        """Merge updates into an existing dictionary at path.

        Args:
            path: Path to the dictionary to merge into
            updates: Updates to merge
            source: Optional source identifier
        """
        with self._lock:
            current_value = self.get(path, {})
            if not isinstance(current_value, dict):
                raise ValueError(f"Cannot merge into non-dictionary at path '{path}'")

            old_value = current_value.copy()
            new_value = {**current_value, **updates}

            self.set(path, new_value, source)

            change = StateChange(
                timestamp=datetime.now(),
                change_type=StateChangeType.MERGE,
                path=path,
                old_value=old_value,
                new_value=new_value,
                source=source,
            )

            self._add_change_to_history(change)

    def reset(self, path: str, source: str | None = None) -> None:
        """Reset a state path to its initial value or delete it.

        Args:
            path: Path to reset
            source: Optional source identifier
        """
        with self._lock:
            old_value = self.get(path)

            keys = path.split(".")
            current = self._state

            # Navigate to parent and delete the key
            for key in keys[:-1]:
                if key not in current:
                    return  # Path doesn't exist
                current = current[key]

            if keys[-1] in current:
                del current[keys[-1]]

            change = StateChange(
                timestamp=datetime.now(),
                change_type=StateChangeType.RESET,
                path=path,
                old_value=old_value,
                new_value=None,
                source=source,
            )

            self._add_change_to_history(change)
            self._notify_observers(path, old_value, None, change)
            self._invalidate_selectors_for_path(path)

            logger.debug(f"State reset: {path} (source: {source})")

    def subscribe(self, path: str, observer: StateObserver) -> None:
        """Subscribe an observer to changes at a specific path.

        Args:
            path: State path to observe
            observer: Observer to notify of changes
        """
        with self._lock:
            if path not in self._observers:
                self._observers[path] = []
            self._observers[path].append(observer)

            logger.debug(f"Observer subscribed to path: {path}")

    def unsubscribe(self, path: str, observer: StateObserver) -> None:
        """Unsubscribe an observer from a path.

        Args:
            path: State path
            observer: Observer to remove
        """
        with self._lock:
            if path in self._observers:
                try:
                    self._observers[path].remove(observer)
                    if not self._observers[path]:
                        del self._observers[path]
                    logger.debug(f"Observer unsubscribed from path: {path}")
                except ValueError:
                    logger.warning(f"Observer not found for path: {path}")

    def register_selector(self, name: str, selector: StateSelector) -> None:
        """Register a state selector for computed values.

        Args:
            name: Name of the selector
            selector: StateSelector instance
        """
        self._selectors[name] = selector
        logger.debug(f"Selector registered: {name}")

    def select(self, selector_name: str) -> Any:
        """Get computed value from a registered selector.

        Args:
            selector_name: Name of the selector

        Returns:
            Computed value from the selector
        """
        if selector_name not in self._selectors:
            raise KeyError(f"Selector '{selector_name}' not registered")

        return self._selectors[selector_name].select(self._state)

    def add_validator(self, path: str, validator: Callable[[Any], bool]) -> None:
        """Add a validator function for a state path.

        Args:
            path: State path to validate
            validator: Function that returns True if value is valid
        """
        self._validators[path] = validator
        logger.debug(f"Validator added for path: {path}")

    def get_change_history(self, limit: int | None = None) -> list[StateChange]:
        """Get the history of state changes.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of StateChange objects
        """
        with self._lock:
            if limit:
                return self._change_history[-limit:]
            return self._change_history.copy()

    def export_state(self) -> dict[str, Any]:
        """Export the current state for persistence or debugging.

        Returns:
            Copy of the current state
        """
        with self._lock:
            return self._deep_copy(self._state)

    def import_state(self, state: dict[str, Any], source: str | None = None) -> None:
        """Import state from external source.

        Args:
            state: State dictionary to import
            source: Optional source identifier
        """
        with self._lock:
            old_state = self._deep_copy(self._state)
            self._state = self._deep_copy(state)

            change = StateChange(
                timestamp=datetime.now(),
                change_type=StateChangeType.SET,
                path="__root__",
                old_value=old_state,
                new_value=state,
                source=source,
            )

            self._add_change_to_history(change)

            # Notify all observers of complete state change
            for path in self._observers:
                old_value = self._get_nested_value(old_state, path)
                new_value = self.get(path)
                if old_value != new_value:
                    self._notify_observers(path, old_value, new_value, change)

            # Invalidate all selectors
            for selector in self._selectors.values():
                if hasattr(selector, "invalidate"):
                    selector.invalidate()

            logger.info(f"State imported from source: {source}")

    def _notify_observers(
        self, path: str, old_value: Any, new_value: Any, change: StateChange
    ) -> None:
        """Notify all observers of a state change."""
        # Notify exact path observers
        if path in self._observers:
            for observer in self._observers[path]:
                try:
                    observer.on_state_change(path, old_value, new_value, change)
                except Exception as e:
                    logger.error(f"Observer error for path '{path}': {e}")

        # Notify wildcard observers (e.g., '*' or parent paths)
        # This could be extended to support more complex path matching
        if "*" in self._observers:
            for observer in self._observers["*"]:
                try:
                    observer.on_state_change(path, old_value, new_value, change)
                except Exception as e:
                    logger.error(f"Wildcard observer error for path '{path}': {e}")

    def _invalidate_selectors_for_path(self, path: str) -> None:
        """Invalidate selectors that depend on the changed path."""
        for selector in self._selectors.values():
            if (
                hasattr(selector, "get_dependencies")
                and path in selector.get_dependencies()
            ):
                if hasattr(selector, "invalidate"):
                    selector.invalidate()

    def _add_change_to_history(self, change: StateChange) -> None:
        """Add a change to the history, maintaining size limit."""
        self._change_history.append(change)
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history :]

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of an object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj


class StatePersistence:
    """Handles state persistence to disk."""

    def __init__(self, storage_path: Path):
        """Initialize state persistence.

        Args:
            storage_path: Path to store state files
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_state(self, state_store: StateStore, name: str = "app_state") -> None:
        """Save state to disk.

        Args:
            state_store: StateStore to save
            name: Name of the state file
        """
        try:
            state_data = {
                "state": state_store.export_state(),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
            }

            file_path = self.storage_path / f"{name}.json"
            with open(file_path, "w") as f:
                json.dump(state_data, f, indent=2, default=str)

            logger.info(f"State saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_state(self, state_store: StateStore, name: str = "app_state") -> bool:
        """Load state from disk.

        Args:
            state_store: StateStore to load into
            name: Name of the state file

        Returns:
            True if state was loaded successfully
        """
        try:
            file_path = self.storage_path / f"{name}.json"
            if not file_path.exists():
                logger.info(f"No saved state found at {file_path}")
                return False

            with open(file_path) as f:
                state_data = json.load(f)

            state_store.import_state(state_data["state"], source="persistence")
            logger.info(f"State loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False


# Helper functions for common selectors
def create_chat_state_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for chat-related state."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": state.get("chat", {}).get("mode", "RAG Mode"),
            "history": state.get("chat", {}).get("history", []),
            "system_prompt": state.get("settings", {}).get("system_prompt", ""),
            "is_processing": state.get("chat", {}).get("is_processing", False),
        }

    dependencies = {
        "chat.mode",
        "chat.history",
        "settings.system_prompt",
        "chat.is_processing",
    }
    return MemoizedSelector(selector, dependencies)


def create_document_state_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for document-related state."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "filter_type": state.get("documents", {}).get("filter_type", "all"),
            "search_query": state.get("documents", {}).get("search_query", ""),
            "library_content": state.get("documents", {}).get("library_content", ""),
            "counts": state.get("documents", {}).get("counts", {}),
        }

    dependencies = {
        "documents.filter_type",
        "documents.search_query",
        "documents.library_content",
        "documents.counts",
    }
    return MemoizedSelector(selector, dependencies)
