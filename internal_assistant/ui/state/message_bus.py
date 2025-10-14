"""
Message Bus for Cross-Component Communication

This module implements a publish-subscribe message bus for decoupled communication
between UI components. Part of Phase 2.3: Cross-Component Communication.

The message bus enables components to communicate without direct coupling,
supporting async operations, queued messages, and event sourcing.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from threading import Lock
import uuid
from collections import deque

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels for queue ordering."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageType(str, Enum):
    """Standard message types for the Internal Assistant UI."""

    # Chat events
    CHAT_MESSAGE_SENT = "chat.message.sent"
    CHAT_MODE_CHANGED = "chat.mode.changed"
    CHAT_HISTORY_CLEARED = "chat.history.cleared"
    CHAT_ERROR_OCCURRED = "chat.error.occurred"

    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_SEARCH_UPDATED = "document.search.updated"
    DOCUMENT_FILTER_CHANGED = "document.filter.changed"
    DOCUMENT_LIBRARY_REFRESHED = "document.library.refreshed"

    # Settings events
    SETTINGS_CHANGED = "settings.changed"
    SYSTEM_PROMPT_UPDATED = "settings.system_prompt.updated"
    MODEL_SETTINGS_CHANGED = "settings.model.changed"

    # External info events
    FEEDS_REFRESHED = "external.feeds.refreshed"
    CVE_DATA_UPDATED = "external.cve.updated"
    MITRE_DATA_UPDATED = "external.mitre.updated"
    THREAT_ALERT_RECEIVED = "external.threat.alert"

    # UI events
    COMPONENT_VISIBILITY_CHANGED = "ui.component.visibility.changed"
    NOTIFICATION_SHOWN = "ui.notification.shown"
    MODAL_OPENED = "ui.modal.opened"
    MODAL_CLOSED = "ui.modal.closed"
    THEME_CHANGED = "ui.theme.changed"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"
    STATE_PERSISTED = "system.state.persisted"
    STATE_RESTORED = "system.state.restored"


@dataclass
class Message:
    """Represents a message in the message bus."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.SYSTEM_INFO
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    target: Optional[str] = None  # Specific component target, None for broadcast
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # For linking related messages
    reply_to: Optional[str] = None  # For request-response patterns

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "type": (
                self.type.value if isinstance(self.type, MessageType) else self.type
            ),
            "data": self.data,
            "source": self.source,
            "target": self.target,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            id=data["id"],
            type=(
                MessageType(data["type"])
                if data["type"] in [mt.value for mt in MessageType]
                else data["type"]
            ),
            data=data.get("data", {}),
            source=data.get("source"),
            target=data.get("target"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=MessagePriority(
                data.get("priority", MessagePriority.NORMAL.value)
            ),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )


class MessageHandler(ABC):
    """Abstract base class for message handlers."""

    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """
        Handle a received message.

        Args:
            message: The message to handle

        Returns:
            Optional reply message
        """
        pass

    @abstractmethod
    def get_handled_types(self) -> Set[MessageType]:
        """Return the set of message types this handler processes."""
        pass


class MessageFilter(ABC):
    """Abstract base class for message filters."""

    @abstractmethod
    def should_process(self, message: Message, handler_id: str) -> bool:
        """Determine if a message should be processed by a handler."""
        pass


class SimpleMessageFilter(MessageFilter):
    """Simple message filter based on message type and target."""

    def __init__(
        self,
        allowed_types: Optional[Set[MessageType]] = None,
        allowed_sources: Optional[Set[str]] = None,
        allowed_targets: Optional[Set[str]] = None,
    ):
        """
        Initialize the filter.

        Args:
            allowed_types: Set of allowed message types
            allowed_sources: Set of allowed source components
            allowed_targets: Set of allowed target components
        """
        self.allowed_types = allowed_types
        self.allowed_sources = allowed_sources
        self.allowed_targets = allowed_targets

    def should_process(self, message: Message, handler_id: str) -> bool:
        """Check if message passes filter criteria."""
        if self.allowed_types and message.type not in self.allowed_types:
            return False

        if self.allowed_sources and message.source not in self.allowed_sources:
            return False

        if self.allowed_targets and message.target and message.target != handler_id:
            return False

        return True


class MessageQueue:
    """Priority queue for messages with async processing."""

    def __init__(self, max_size: int = 10000):
        """
        Initialize message queue.

        Args:
            max_size: Maximum number of messages in queue
        """
        self.max_size = max_size
        self._queues = {
            MessagePriority.CRITICAL: deque(),
            MessagePriority.HIGH: deque(),
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque(),
        }
        self._lock = Lock()
        self._message_count = 0

    def put(self, message: Message) -> bool:
        """
        Add message to queue.

        Args:
            message: Message to queue

        Returns:
            True if message was queued, False if queue is full
        """
        with self._lock:
            if self._message_count >= self.max_size:
                # Remove oldest low priority message to make room
                if self._queues[MessagePriority.LOW]:
                    self._queues[MessagePriority.LOW].popleft()
                    self._message_count -= 1
                else:
                    logger.warning("Message queue full, dropping message")
                    return False

            self._queues[message.priority].append(message)
            self._message_count += 1
            return True

    def get(self) -> Optional[Message]:
        """
        Get next message from queue (highest priority first).

        Returns:
            Next message or None if queue is empty
        """
        with self._lock:
            # Check queues in priority order
            for priority in [
                MessagePriority.CRITICAL,
                MessagePriority.HIGH,
                MessagePriority.NORMAL,
                MessagePriority.LOW,
            ]:
                if self._queues[priority]:
                    message = self._queues[priority].popleft()
                    self._message_count -= 1
                    return message
            return None

    def size(self) -> int:
        """Get total number of messages in queue."""
        with self._lock:
            return self._message_count

    def clear(self) -> None:
        """Clear all messages from queue."""
        with self._lock:
            for queue in self._queues.values():
                queue.clear()
            self._message_count = 0


class MessageBus:
    """
    Central message bus for cross-component communication.

    Implements publish-subscribe pattern with async message processing,
    message queuing, filtering, and event sourcing capabilities.
    """

    def __init__(self, max_queue_size: int = 10000, max_history: int = 5000):
        """
        Initialize the message bus.

        Args:
            max_queue_size: Maximum size of message queue
            max_history: Maximum number of messages to keep in history
        """
        self._handlers: Dict[str, MessageHandler] = {}
        self._subscriptions: Dict[MessageType, Set[str]] = {}
        self._filters: Dict[str, MessageFilter] = {}
        self._queue = MessageQueue(max_queue_size)
        self._message_history: List[Message] = []
        self._max_history = max_history
        self._lock = Lock()
        self._processing = False
        self._stats = {
            "messages_sent": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "handlers_registered": 0,
        }

        logger.info("MessageBus initialized")

    def register_handler(
        self,
        handler_id: str,
        handler: MessageHandler,
        message_filter: Optional[MessageFilter] = None,
    ) -> None:
        """
        Register a message handler.

        Args:
            handler_id: Unique identifier for the handler
            handler: MessageHandler implementation
            message_filter: Optional filter for messages
        """
        with self._lock:
            self._handlers[handler_id] = handler

            if message_filter:
                self._filters[handler_id] = message_filter

            # Subscribe to all message types the handler processes
            for message_type in handler.get_handled_types():
                if message_type not in self._subscriptions:
                    self._subscriptions[message_type] = set()
                self._subscriptions[message_type].add(handler_id)

            self._stats["handlers_registered"] += 1
            logger.info(f"Handler registered: {handler_id}")

    def unregister_handler(self, handler_id: str) -> None:
        """
        Unregister a message handler.

        Args:
            handler_id: Handler identifier to remove
        """
        with self._lock:
            if handler_id in self._handlers:
                handler = self._handlers[handler_id]

                # Remove from subscriptions
                for message_type in handler.get_handled_types():
                    if message_type in self._subscriptions:
                        self._subscriptions[message_type].discard(handler_id)
                        if not self._subscriptions[message_type]:
                            del self._subscriptions[message_type]

                # Remove handler and filter
                del self._handlers[handler_id]
                if handler_id in self._filters:
                    del self._filters[handler_id]

                self._stats["handlers_registered"] -= 1
                logger.info(f"Handler unregistered: {handler_id}")

    async def publish(self, message: Message) -> bool:
        """
        Publish a message to the bus.

        Args:
            message: Message to publish

        Returns:
            True if message was queued successfully
        """
        # Add to history
        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history = self._message_history[-self._max_history :]

            self._stats["messages_sent"] += 1

        # Queue the message
        queued = self._queue.put(message)

        if queued:
            logger.debug(f"Message published: {message.type} from {message.source}")

            # Start processing if not already running
            if not self._processing:
                asyncio.create_task(self._process_messages())
        else:
            logger.error(f"Failed to queue message: {message.type}")

        return queued

    async def publish_simple(
        self,
        message_type: MessageType,
        data: Dict[str, Any],
        source: Optional[str] = None,
        target: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """
        Convenience method to publish a simple message.

        Args:
            message_type: Type of message
            data: Message data
            source: Source component
            target: Target component (None for broadcast)
            priority: Message priority

        Returns:
            True if message was published successfully
        """
        message = Message(
            type=message_type,
            data=data,
            source=source,
            target=target,
            priority=priority,
        )

        return await self.publish(message)

    async def request_response(
        self, message: Message, timeout: float = 30.0
    ) -> Optional[Message]:
        """
        Send a message and wait for a response.

        Args:
            message: Request message
            timeout: Timeout in seconds

        Returns:
            Response message or None if timeout
        """
        # Set up response tracking
        response_event = asyncio.Event()
        response_message = None

        def response_handler(msg: Message):
            nonlocal response_message
            if msg.reply_to == message.id:
                response_message = msg
                response_event.set()

        # Register temporary handler for response
        temp_handler_id = f"response_{message.id}"

        class ResponseHandler(MessageHandler):
            async def handle_message(self, msg: Message) -> Optional[Message]:
                response_handler(msg)
                return None

            def get_handled_types(self) -> Set[MessageType]:
                return set(MessageType)  # Listen to all types for response

        response_handler_obj = ResponseHandler()
        self.register_handler(temp_handler_id, response_handler_obj)

        try:
            # Send the request
            await self.publish(message)

            # Wait for response
            await asyncio.wait_for(response_event.wait(), timeout=timeout)
            return response_message

        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for message: {message.id}")
            return None
        finally:
            # Clean up temporary handler
            self.unregister_handler(temp_handler_id)

    async def _process_messages(self) -> None:
        """Process messages from the queue asynchronously."""
        self._processing = True

        try:
            while True:
                message = self._queue.get()
                if not message:
                    await asyncio.sleep(0.1)  # Small delay when no messages
                    continue

                await self._process_single_message(message)

        except Exception as e:
            logger.error(f"Error in message processing: {e}")
        finally:
            self._processing = False

    async def _process_single_message(self, message: Message) -> None:
        """Process a single message."""
        try:
            # Find handlers for this message type
            handlers_to_notify = set()

            if message.target:
                # Targeted message
                if message.target in self._handlers:
                    handlers_to_notify.add(message.target)
            else:
                # Broadcast message
                if message.type in self._subscriptions:
                    handlers_to_notify.update(self._subscriptions[message.type])

            # Process message with each handler
            for handler_id in handlers_to_notify:
                if handler_id not in self._handlers:
                    continue

                # Apply filter if configured
                if handler_id in self._filters:
                    if not self._filters[handler_id].should_process(
                        message, handler_id
                    ):
                        continue

                try:
                    handler = self._handlers[handler_id]
                    response = await handler.handle_message(message)

                    # If handler returned a response, publish it
                    if response:
                        response.reply_to = message.id
                        response.correlation_id = message.correlation_id or message.id
                        await self.publish(response)

                    self._stats["messages_processed"] += 1

                except Exception as e:
                    logger.error(
                        f"Handler {handler_id} failed to process message {message.id}: {e}"
                    )
                    self._stats["messages_failed"] += 1

                    # Publish error message
                    error_message = Message(
                        type=MessageType.SYSTEM_ERROR,
                        data={
                            "error": str(e),
                            "handler_id": handler_id,
                            "original_message_id": message.id,
                            "original_message_type": message.type.value,
                        },
                        source="message_bus",
                        correlation_id=message.correlation_id,
                    )
                    await self.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error processing message {message.id}: {e}")
            self._stats["messages_failed"] += 1

    def get_message_history(
        self, limit: Optional[int] = None, message_type: Optional[MessageType] = None
    ) -> List[Message]:
        """
        Get message history.

        Args:
            limit: Maximum number of messages to return
            message_type: Filter by message type

        Returns:
            List of messages
        """
        with self._lock:
            messages = self._message_history

            if message_type:
                messages = [m for m in messages if m.type == message_type]

            if limit:
                messages = messages[-limit:]

            return messages.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        with self._lock:
            return {
                **self._stats,
                "queue_size": self._queue.size(),
                "active_handlers": len(self._handlers),
                "message_types_subscribed": len(self._subscriptions),
                "history_size": len(self._message_history),
            }

    def clear_history(self) -> None:
        """Clear message history."""
        with self._lock:
            self._message_history.clear()

    def shutdown(self) -> None:
        """Shutdown the message bus."""
        with self._lock:
            self._handlers.clear()
            self._subscriptions.clear()
            self._filters.clear()
            self._queue.clear()
            self._message_history.clear()
            self._processing = False

        logger.info("MessageBus shutdown")


# Helper classes for common UI component handlers
class UIComponentHandler(MessageHandler):
    """Base handler for UI component message handling."""

    def __init__(self, component_id: str, handled_types: Set[MessageType]):
        """
        Initialize UI component handler.

        Args:
            component_id: Unique component identifier
            handled_types: Set of message types to handle
        """
        self.component_id = component_id
        self.handled_types = handled_types

    def get_handled_types(self) -> Set[MessageType]:
        """Return handled message types."""
        return self.handled_types


class ChatComponentHandler(UIComponentHandler):
    """Handler for chat component messages."""

    def __init__(self, component_id: str = "chat"):
        super().__init__(
            component_id,
            {
                MessageType.CHAT_MESSAGE_SENT,
                MessageType.CHAT_MODE_CHANGED,
                MessageType.CHAT_HISTORY_CLEARED,
                MessageType.SETTINGS_CHANGED,
                MessageType.SYSTEM_PROMPT_UPDATED,
            },
        )

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle chat-related messages."""
        if message.type == MessageType.CHAT_MESSAGE_SENT:
            # Process new chat message
            logger.info(f"Chat message received: {message.data.get('message', '')}")

        elif message.type == MessageType.CHAT_MODE_CHANGED:
            # Handle mode change
            new_mode = message.data.get("mode")
            logger.info(f"Chat mode changed to: {new_mode}")

        elif message.type == MessageType.SETTINGS_CHANGED:
            # Handle settings change that affects chat
            settings = message.data.get("settings", {})
            logger.info(f"Chat settings updated: {settings}")

        return None


class DocumentComponentHandler(UIComponentHandler):
    """Handler for document component messages."""

    def __init__(self, component_id: str = "documents"):
        super().__init__(
            component_id,
            {
                MessageType.DOCUMENT_UPLOADED,
                MessageType.DOCUMENT_DELETED,
                MessageType.DOCUMENT_PROCESSED,
                MessageType.DOCUMENT_SEARCH_UPDATED,
                MessageType.DOCUMENT_FILTER_CHANGED,
            },
        )

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle document-related messages."""
        if message.type == MessageType.DOCUMENT_UPLOADED:
            # Process document upload
            filename = message.data.get("filename")
            logger.info(f"Document uploaded: {filename}")

            # Broadcast library refresh needed
            return Message(
                type=MessageType.DOCUMENT_LIBRARY_REFRESHED,
                data={"trigger": "upload", "filename": filename},
                source=self.component_id,
            )

        elif message.type == MessageType.DOCUMENT_FILTER_CHANGED:
            # Handle filter change
            filter_type = message.data.get("filter_type")
            logger.info(f"Document filter changed to: {filter_type}")

        return None
