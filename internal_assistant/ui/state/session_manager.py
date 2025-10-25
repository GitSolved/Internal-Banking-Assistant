"""Session Manager

This module handles user session tracking, conversation history management,
and session persistence for the Internal Assistant UI.

Part of Phase 2.4: Session Management implementation.
"""

import asyncio
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .app_state import ApplicationState
from .message_bus import MessageBus, MessageType

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Metadata about a user session."""

    session_id: str
    user_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    last_message_time: datetime | None = None
    message_count: int = 0
    documents_accessed: set[str] = field(default_factory=set)
    modes_used: set[str] = field(default_factory=set)
    settings_modified: dict[str, datetime] = field(default_factory=dict)
    session_duration: timedelta = field(default_factory=lambda: timedelta())
    is_active: bool = True
    client_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "last_message_time": (
                self.last_message_time.isoformat() if self.last_message_time else None
            ),
            "message_count": self.message_count,
            "documents_accessed": list(self.documents_accessed),
            "modes_used": list(self.modes_used),
            "settings_modified": {
                k: v.isoformat() for k, v in self.settings_modified.items()
            },
            "session_duration": self.session_duration.total_seconds(),
            "is_active": self.is_active,
            "client_info": self.client_info,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            last_message_time=(
                datetime.fromisoformat(data["last_message_time"])
                if data.get("last_message_time")
                else None
            ),
            message_count=data.get("message_count", 0),
            documents_accessed=set(data.get("documents_accessed", [])),
            modes_used=set(data.get("modes_used", [])),
            settings_modified={
                k: datetime.fromisoformat(v)
                for k, v in data.get("settings_modified", {}).items()
            },
            session_duration=timedelta(seconds=data.get("session_duration", 0)),
            is_active=data.get("is_active", True),
            client_info=data.get("client_info", {}),
        )


@dataclass
class ConversationHistory:
    """Represents a conversation history for a session."""

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    total_messages: int = 0
    total_tokens_estimated: int = 0

    def add_message(
        self,
        user_message: str,
        assistant_response: str,
        mode: str,
        sources: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message pair to the conversation."""
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "mode": mode,
            "sources": sources or [],
            "metadata": metadata or {},
            "message_id": str(uuid4()),
        }

        self.messages.append(message_entry)
        self.total_messages += 1
        self.last_updated = datetime.now()

        # Rough token estimation
        text_length = len(user_message) + len(assistant_response)
        estimated_tokens = text_length // 4  # Rough approximation
        self.total_tokens_estimated += estimated_tokens

    def get_recent_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent messages."""
        return self.messages[-limit:] if self.messages else []

    def clear_messages(self) -> None:
        """Clear all messages from history."""
        self.messages.clear()
        self.total_messages = 0
        self.total_tokens_estimated = 0
        self.last_updated = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "total_messages": self.total_messages,
            "total_tokens_estimated": self.total_tokens_estimated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationHistory":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            messages=data.get("messages", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            total_messages=data.get("total_messages", 0),
            total_tokens_estimated=data.get("total_tokens_estimated", 0),
        )


class SessionStorage:
    """Handles persistence of session data to disk."""

    def __init__(self, storage_path: Path):
        """Initialize session storage.

        Args:
            storage_path: Directory to store session files
        """
        self.storage_path = storage_path
        self.sessions_path = storage_path / "sessions"
        self.conversations_path = storage_path / "conversations"
        self.states_path = storage_path / "states"

        # Create directories
        for path in [self.sessions_path, self.conversations_path, self.states_path]:
            path.mkdir(parents=True, exist_ok=True)

    def save_session_metadata(self, metadata: SessionMetadata) -> None:
        """Save session metadata to disk."""
        try:
            file_path = self.sessions_path / f"{metadata.session_id}.json"
            with open(file_path, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2, default=str)
            logger.debug(f"Session metadata saved: {metadata.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session metadata {metadata.session_id}: {e}")

    def load_session_metadata(self, session_id: str) -> SessionMetadata | None:
        """Load session metadata from disk."""
        try:
            file_path = self.sessions_path / f"{session_id}.json"
            if not file_path.exists():
                return None

            with open(file_path) as f:
                data = json.load(f)

            return SessionMetadata.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load session metadata {session_id}: {e}")
            return None

    def save_conversation_history(self, history: ConversationHistory) -> None:
        """Save conversation history to disk."""
        try:
            file_path = self.conversations_path / f"{history.session_id}.json"
            with open(file_path, "w") as f:
                json.dump(history.to_dict(), f, indent=2, default=str)
            logger.debug(f"Conversation history saved: {history.session_id}")
        except Exception as e:
            logger.error(
                f"Failed to save conversation history {history.session_id}: {e}"
            )

    def load_conversation_history(
        self, session_id: str
    ) -> ConversationHistory | None:
        """Load conversation history from disk."""
        try:
            file_path = self.conversations_path / f"{session_id}.json"
            if not file_path.exists():
                return ConversationHistory(session_id=session_id)

            with open(file_path) as f:
                data = json.load(f)

            return ConversationHistory.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load conversation history {session_id}: {e}")
            return ConversationHistory(session_id=session_id)

    def save_session_state(self, session_id: str, state: ApplicationState) -> None:
        """Save application state for a session."""
        try:
            file_path = self.states_path / f"{session_id}.pkl"
            with open(file_path, "wb") as f:
                pickle.dump(state.dict(), f)
            logger.debug(f"Session state saved: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save session state {session_id}: {e}")

    def load_session_state(self, session_id: str) -> ApplicationState | None:
        """Load application state for a session."""
        try:
            file_path = self.states_path / f"{session_id}.pkl"
            if not file_path.exists():
                return None

            with open(file_path, "rb") as f:
                state_data = pickle.load(f)

            return ApplicationState(**state_data)
        except Exception as e:
            logger.error(f"Failed to load session state {session_id}: {e}")
            return None

    def list_sessions(
        self, active_only: bool = False, limit: int | None = None
    ) -> list[str]:
        """List all session IDs.

        Args:
            active_only: Only return active sessions
            limit: Maximum number of sessions to return

        Returns:
            List of session IDs
        """
        try:
            session_files = list(self.sessions_path.glob("*.json"))
            session_ids = []

            for file_path in session_files:
                session_id = file_path.stem
                if active_only:
                    metadata = self.load_session_metadata(session_id)
                    if metadata and metadata.is_active:
                        session_ids.append(session_id)
                else:
                    session_ids.append(session_id)

            # Sort by most recent first
            session_ids.sort(reverse=True)

            if limit:
                session_ids = session_ids[:limit]

            return session_ids
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> None:
        """Delete all files for a session."""
        try:
            files_to_delete = [
                self.sessions_path / f"{session_id}.json",
                self.conversations_path / f"{session_id}.json",
                self.states_path / f"{session_id}.pkl",
            ]

            for file_path in files_to_delete:
                if file_path.exists():
                    file_path.unlink()

            logger.info(f"Session deleted: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")


class SessionManager:
    """Manages user sessions, conversation history, and session persistence.

    Handles session lifecycle, automatic cleanup, conversation tracking,
    and session restoration capabilities.
    """

    def __init__(
        self,
        storage_path: Path,
        message_bus: MessageBus | None = None,
        session_timeout: timedelta = timedelta(hours=24),
        max_sessions: int = 1000,
    ):
        """Initialize session manager.

        Args:
            storage_path: Path for session storage
            message_bus: Optional message bus for session events
            session_timeout: Time before sessions are considered inactive
            max_sessions: Maximum number of sessions to keep
        """
        self.storage = SessionStorage(storage_path)
        self.message_bus = message_bus
        self.session_timeout = session_timeout
        self.max_sessions = max_sessions

        # In-memory session tracking
        self._active_sessions: dict[str, SessionMetadata] = {}
        self._conversation_histories: dict[str, ConversationHistory] = {}
        self._session_states: dict[str, ApplicationState] = {}
        self._lock = Lock()

        # Statistics
        self._stats = {
            "sessions_created": 0,
            "sessions_restored": 0,
            "sessions_expired": 0,
            "messages_tracked": 0,
            "state_saves": 0,
            "state_restores": 0,
        }

        # Load recent active sessions
        self._load_recent_sessions()

        # Initialize cleanup task (will be started lazily when needed)
        self._cleanup_task: asyncio.Task | None = None

        logger.info("SessionManager initialized")

    def create_session(
        self,
        user_id: str | None = None,
        client_info: dict[str, Any] | None = None,
    ) -> str:
        """Create a new session.

        Args:
            user_id: Optional user identifier
            client_info: Optional client information

        Returns:
            New session ID
        """
        session_id = str(uuid4())

        with self._lock:
            metadata = SessionMetadata(
                session_id=session_id, user_id=user_id, client_info=client_info or {}
            )

            self._active_sessions[session_id] = metadata
            self._conversation_histories[session_id] = ConversationHistory(
                session_id=session_id
            )
            self._session_states[session_id] = ApplicationState()

            self._stats["sessions_created"] += 1

        # Persist to disk
        self.storage.save_session_metadata(metadata)

        # Publish session created event
        if self.message_bus:
            asyncio.create_task(
                self.message_bus.publish_simple(
                    MessageType.SYSTEM_INFO,
                    {
                        "event": "session_created",
                        "session_id": session_id,
                        "user_id": user_id,
                    },
                    source="session_manager",
                )
            )

        logger.info(f"Session created: {session_id} for user: {user_id}")
        return session_id

    def get_session(self, session_id: str) -> SessionMetadata | None:
        """Get session metadata."""
        with self._lock:
            return self._active_sessions.get(session_id)

    def update_session_access(self, session_id: str) -> None:
        """Update session last access time."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].last_accessed = datetime.now()
                # Save to disk periodically (every 10 accesses)
                if self._active_sessions[session_id].message_count % 10 == 0:
                    self.storage.save_session_metadata(
                        self._active_sessions[session_id]
                    )

    def add_conversation_message(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        mode: str,
        sources: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to session conversation history.

        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_response: Assistant's response
            mode: Chat mode used
            sources: Optional sources used
            metadata: Optional message metadata
        """
        with self._lock:
            if session_id not in self._conversation_histories:
                self._conversation_histories[session_id] = ConversationHistory(
                    session_id=session_id
                )

            if session_id in self._active_sessions:
                # Update session metadata
                session = self._active_sessions[session_id]
                session.last_message_time = datetime.now()
                session.message_count += 1
                session.modes_used.add(mode)

                # Track document access
                if sources:
                    for source in sources:
                        if "file" in source:
                            session.documents_accessed.add(source["file"])

        # Add to conversation history
        self._conversation_histories[session_id].add_message(
            user_message, assistant_response, mode, sources, metadata
        )

        self._stats["messages_tracked"] += 1

        # Save conversation to disk
        self.storage.save_conversation_history(self._conversation_histories[session_id])

        # Publish message tracked event
        if self.message_bus:
            asyncio.create_task(
                self.message_bus.publish_simple(
                    MessageType.SYSTEM_INFO,
                    {
                        "event": "message_tracked",
                        "session_id": session_id,
                        "message_count": self._active_sessions.get(
                            session_id, SessionMetadata(session_id)
                        ).message_count,
                    },
                    source="session_manager",
                )
            )

        logger.debug(f"Message added to session {session_id}")

    def get_conversation_history(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages

        Returns:
            List of conversation messages
        """
        with self._lock:
            if session_id not in self._conversation_histories:
                return []

            history = self._conversation_histories[session_id]
            if limit:
                return history.get_recent_messages(limit)
            else:
                return history.messages.copy()

    def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        with self._lock:
            if session_id in self._conversation_histories:
                self._conversation_histories[session_id].clear_messages()
                self.storage.save_conversation_history(
                    self._conversation_histories[session_id]
                )

        logger.info(f"Conversation history cleared for session: {session_id}")

    def save_session_state(self, session_id: str, state: ApplicationState) -> None:
        """Save application state for a session.

        Args:
            session_id: Session identifier
            state: Application state to save
        """
        with self._lock:
            self._session_states[session_id] = state
            self._stats["state_saves"] += 1

        # Persist to disk
        self.storage.save_session_state(session_id, state)

        logger.debug(f"Session state saved: {session_id}")

    def restore_session_state(self, session_id: str) -> ApplicationState | None:
        """Restore application state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Restored application state or None
        """
        # Try memory first
        with self._lock:
            if session_id in self._session_states:
                self._stats["state_restores"] += 1
                return self._session_states[session_id]

        # Try disk
        state = self.storage.load_session_state(session_id)
        if state:
            with self._lock:
                self._session_states[session_id] = state
                self._stats["state_restores"] += 1
            logger.info(f"Session state restored from disk: {session_id}")
            return state

        logger.debug(f"No saved state found for session: {session_id}")
        return None

    def expire_session(self, session_id: str) -> None:
        """Mark a session as expired and clean up."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].is_active = False
                self.storage.save_session_metadata(self._active_sessions[session_id])

                # Remove from active tracking but keep data for potential restoration
                del self._active_sessions[session_id]

                # Keep conversation history and state for potential restoration
                # Only remove from memory, disk files remain

                self._stats["sessions_expired"] += 1

        logger.info(f"Session expired: {session_id}")

    def delete_session(self, session_id: str, permanent: bool = False) -> None:
        """Delete a session.

        Args:
            session_id: Session to delete
            permanent: If True, delete all files; if False, just mark inactive
        """
        with self._lock:
            # Remove from memory
            self._active_sessions.pop(session_id, None)
            self._conversation_histories.pop(session_id, None)
            self._session_states.pop(session_id, None)

        if permanent:
            # Delete from disk
            self.storage.delete_session(session_id)
            logger.info(f"Session permanently deleted: {session_id}")
        else:
            # Just mark as inactive
            metadata = self.storage.load_session_metadata(session_id)
            if metadata:
                metadata.is_active = False
                self.storage.save_session_metadata(metadata)
            logger.info(f"Session marked inactive: {session_id}")

    def list_sessions(
        self,
        user_id: str | None = None,
        active_only: bool = True,
        limit: int | None = None,
    ) -> list[SessionMetadata]:
        """List sessions.

        Args:
            user_id: Filter by user ID
            active_only: Only return active sessions
            limit: Maximum number of sessions

        Returns:
            List of session metadata
        """
        sessions = []

        # Get from memory first
        with self._lock:
            for metadata in self._active_sessions.values():
                if user_id and metadata.user_id != user_id:
                    continue
                if active_only and not metadata.is_active:
                    continue
                sessions.append(metadata)

        # Sort by most recent access
        sessions.sort(key=lambda s: s.last_accessed, reverse=True)

        if limit:
            sessions = sessions[:limit]

        return sessions

    def get_session_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            active_count = len(self._active_sessions)
            total_messages = sum(
                h.total_messages for h in self._conversation_histories.values()
            )

            return {
                **self._stats,
                "active_sessions": active_count,
                "total_messages_in_memory": total_messages,
                "average_messages_per_session": (
                    total_messages / active_count if active_count > 0 else 0
                ),
            }

    def _load_recent_sessions(self) -> None:
        """Load recent active sessions from disk."""
        try:
            session_ids = self.storage.list_sessions(active_only=True, limit=100)
            loaded_count = 0

            for session_id in session_ids:
                metadata = self.storage.load_session_metadata(session_id)
                if metadata and metadata.is_active:
                    # Check if session hasn't timed out
                    if datetime.now() - metadata.last_accessed < self.session_timeout:
                        self._active_sessions[session_id] = metadata
                        self._conversation_histories[session_id] = (
                            self.storage.load_conversation_history(session_id)
                        )

                        # Load state if available
                        state = self.storage.load_session_state(session_id)
                        if state:
                            self._session_states[session_id] = state
                        else:
                            self._session_states[session_id] = ApplicationState()

                        loaded_count += 1
                        self._stats["sessions_restored"] += 1

            logger.info(f"Loaded {loaded_count} recent sessions from disk")

        except Exception as e:
            logger.error(f"Failed to load recent sessions: {e}")

    def _start_cleanup_task(self) -> None:
        """Start the session cleanup background task (only if event loop is running)."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(
                    self._cleanup_sessions_periodically()
                )
        except RuntimeError:
            # No event loop running - cleanup task will be started later when needed
            pass

    async def _cleanup_sessions_periodically(self) -> None:
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        now = datetime.now()
        expired_sessions = []

        with self._lock:
            for session_id, metadata in list(self._active_sessions.items()):
                if now - metadata.last_accessed > self.session_timeout:
                    expired_sessions.append(session_id)

        # Expire sessions
        for session_id in expired_sessions:
            self.expire_session(session_id)

        if expired_sessions:
            logger.info(f"Expired {len(expired_sessions)} sessions due to timeout")

        # Also clean up if we have too many sessions
        if len(self._active_sessions) > self.max_sessions:
            # Remove oldest sessions
            with self._lock:
                sessions_by_access = sorted(
                    self._active_sessions.items(), key=lambda x: x[1].last_accessed
                )

                sessions_to_remove = len(sessions_by_access) - self.max_sessions
                for session_id, _ in sessions_by_access[:sessions_to_remove]:
                    self.expire_session(session_id)

            logger.info(
                f"Expired {sessions_to_remove} sessions due to max session limit"
            )

    def shutdown(self) -> None:
        """Shutdown the session manager."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        # Save all active sessions
        with self._lock:
            for metadata in self._active_sessions.values():
                self.storage.save_session_metadata(metadata)

            for history in self._conversation_histories.values():
                self.storage.save_conversation_history(history)

            for session_id, state in self._session_states.items():
                self.storage.save_session_state(session_id, state)

        logger.info("SessionManager shutdown complete")


# Helper functions for common session operations
def create_default_session_manager(
    storage_path: Path, message_bus: MessageBus | None = None
) -> SessionManager:
    """Create a session manager with default settings.

    Args:
        storage_path: Path for session storage
        message_bus: Optional message bus

    Returns:
        Configured SessionManager instance
    """
    return SessionManager(
        storage_path=storage_path,
        message_bus=message_bus,
        session_timeout=timedelta(hours=24),
        max_sessions=1000,
    )


def migrate_legacy_conversation_history(
    legacy_history: list[list[str]], session_id: str
) -> ConversationHistory:
    """Migrate legacy Gradio chat history to new conversation format.

    Args:
        legacy_history: Legacy chat history in [[user, assistant], ...] format
        session_id: Session ID for the new history

    Returns:
        ConversationHistory instance
    """
    history = ConversationHistory(session_id=session_id)

    for entry in legacy_history:
        if len(entry) >= 2 and entry[0] and entry[1]:
            user_message = entry[0]
            assistant_response = entry[1]

            # Extract sources if present (simple heuristic)
            sources = []
            if "<hr>Sources:" in assistant_response:
                # Basic source extraction - this could be improved
                pass

            history.add_message(
                user_message=user_message,
                assistant_response=assistant_response,
                mode="Unknown",  # Legacy mode not preserved
                sources=sources,
            )

    return history
