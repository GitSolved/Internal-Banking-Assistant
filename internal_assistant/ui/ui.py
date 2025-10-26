"""This file should be imported if and only if you want to run the UI locally."""

import asyncio
import logging
import time
from collections.abc import Callable, Iterable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import gradio as gr  # type: ignore
from fastapi import FastAPI
from injector import inject, singleton
from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.types import TokenGen
from pydantic import BaseModel, ConfigDict

from internal_assistant.constants import PROJECT_ROOT_PATH
from internal_assistant.di import global_injector
from internal_assistant.open_ai.extensions.context_filter import ContextFilter
from internal_assistant.server.chat.chat_service import ChatService, CompletionGen
from internal_assistant.server.chunks.chunks_service import Chunk, ChunksService
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.recipes.summarize.summarize_service import (
    SummarizeService,
)
from internal_assistant.settings.settings import settings
from internal_assistant.ui.components.chat.chat_events import ChatEventHandlerBuilder
from internal_assistant.ui.components.chat.chat_interface import (
    create_chat_interface,
    get_chat_component_refs,
)
from internal_assistant.ui.components.documents.document_events import (
    DocumentEventHandlerBuilder,
)
from internal_assistant.ui.components.documents.document_library import (
    DocumentLibraryBuilder,
)
from internal_assistant.ui.components.documents.document_state import (
    DocumentStateManager,
)
from internal_assistant.ui.components.documents.document_upload import (
    create_document_upload_interface,
    get_document_component_refs,
)
from internal_assistant.ui.components.documents.document_utility import (
    DocumentUtilityBuilder,
)
from internal_assistant.ui.components.feeds.complex_display import ComplexDisplayBuilder
from internal_assistant.ui.components.feeds.display_utility import DisplayUtilityBuilder
from internal_assistant.ui.components.feeds.external_info import (
    create_external_info_interface,
    get_external_info_component_refs,
)
from internal_assistant.ui.components.feeds.feeds_display import FeedsDisplayBuilder
from internal_assistant.ui.components.feeds.feeds_events import FeedsEventHandlerBuilder
from internal_assistant.ui.components.settings.settings_events import (
    SettingsEventHandlerBuilder,
)
from internal_assistant.ui.core.error_boundaries import (
    create_error_boundary,
    error_reporter,
)
from internal_assistant.ui.core.event_router import EventBridge, EventRouter
from internal_assistant.ui.services.mitre_loader import get_mitre_loader
from internal_assistant.ui.services.performance_optimizer import PerformanceOptimizer

# Phase 3: Service Layer Integration
from internal_assistant.ui.services.ui_service_integration import (
    ServiceCompatibilityLayer,
    create_ui_service_integration,
)

# Phase 2: State Management Integration
from internal_assistant.ui.state import (
    MessageBus,
    StateIntegrationManager,
    create_application_state_from_legacy,
    create_default_session_manager,
    create_gradio_sync,
)
from internal_assistant.ui.styles.css_manager import CSSManager
from internal_assistant.ui.ui_strings import (
    UI_TAB_TITLE,
)
from tools.Javascript.js_manager import JSManager

logger = logging.getLogger(__name__)

THIS_DIRECTORY_RELATIVE = Path(__file__).parent.relative_to(PROJECT_ROOT_PATH)
# Should be "internal_assistant/ui/avatar-bot.ico"
AVATAR_BOT = THIS_DIRECTORY_RELATIVE / "avatar-bot.ico"
# Internal Assistant logo
INTERNAL_LOGO = THIS_DIRECTORY_RELATIVE / "internal-assistant-logo.png"

# UI_TAB_TITLE now imported from ui_strings.py
SOURCES_SEPARATOR = "<hr>Sources: \n"


class Modes(str, Enum):
    DOCUMENT_ASSISTANT = "RAG Mode"
    GENERAL_ASSISTANT = "General LLM"

    # Deprecated modes for backward compatibility - will map to new modes
    RAG_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SEARCH_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    COMPARE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SUMMARIZE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    DIRECT_CHAT = "General LLM"  # Maps to GENERAL_ASSISTANT


MODES: list[Modes] = [
    Modes.DOCUMENT_ASSISTANT,
    Modes.GENERAL_ASSISTANT,
]

# Backward compatibility mapping
LEGACY_MODE_MAPPING = {
    "Document Assistant": Modes.DOCUMENT_ASSISTANT.value,
    "Document Search": Modes.DOCUMENT_ASSISTANT.value,
    "Document Compare": Modes.DOCUMENT_ASSISTANT.value,
    "Document Summary": Modes.DOCUMENT_ASSISTANT.value,
    "General Assistant": Modes.GENERAL_ASSISTANT.value,
    "RAG": Modes.DOCUMENT_ASSISTANT.value,
    "SEARCH": Modes.DOCUMENT_ASSISTANT.value,
    "COMPARE": Modes.DOCUMENT_ASSISTANT.value,
    "SUMMARIZE": Modes.DOCUMENT_ASSISTANT.value,
    "DIRECT": Modes.GENERAL_ASSISTANT.value,
}


def normalize_mode(mode: str) -> str:
    """Normalize any mode string to one of the two supported modes.
    Provides backward compatibility for legacy mode names.
    """
    if mode in LEGACY_MODE_MAPPING:
        return LEGACY_MODE_MAPPING[mode]

    # Direct enum value check
    if mode == Modes.DOCUMENT_ASSISTANT.value:
        return Modes.DOCUMENT_ASSISTANT.value
    elif mode == Modes.GENERAL_ASSISTANT.value:
        return Modes.GENERAL_ASSISTANT.value

    # Default to RAG Mode since this is a RAG system
    return Modes.DOCUMENT_ASSISTANT.value


class Source(BaseModel):
    file: str
    page: str
    text: str

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @staticmethod
    def curate_sources(sources: list[Chunk]) -> list["Source"]:
        curated_sources = []

        for chunk in sources:
            doc_metadata = chunk.document.doc_metadata

            file_name = doc_metadata.get("file_name", "-") if doc_metadata else "-"
            page_label = doc_metadata.get("page_label", "-") if doc_metadata else "-"

            source = Source(file=file_name, page=page_label, text=chunk.text)
            curated_sources.append(source)
            curated_sources = list(
                dict.fromkeys(curated_sources).keys()
            )  # Unique sources only

        return curated_sources


@singleton
class InternalAssistantUI:

    # Regex patterns have been removed to simplify the interface

    @inject
    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService,
        chunks_service: ChunksService,
        summarizeService: SummarizeService,
        feeds_service: RSSFeedService,
    ) -> None:
        # Legacy service references (for backward compatibility)
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._chunks_service = chunks_service
        self._summarize_service = summarizeService
        self._feeds_service = feeds_service

        # Phase 3: Initialize Service Layer Integration
        logger.info("Initializing service layer integration")
        self._ui_service_integration = create_ui_service_integration(global_injector)
        self._service_compatibility = ServiceCompatibilityLayer(
            self._ui_service_integration
        )
        self._performance_optimizer = PerformanceOptimizer()

        # Check service integration status
        if self._ui_service_integration.is_ready:
            logger.info("Service layer integration ready - using optimized facades")
            self._use_service_facades = True
        else:
            logger.warning(
                "Service layer integration not ready - falling back to direct services"
            )
            self._use_service_facades = False

        # Initialize CSS Manager
        self._css_manager = CSSManager()

        # Initialize JavaScript Manager
        self._js_manager = JSManager()

        # Initialize UI block cache
        self._ui_block = None

        # Initialize Global Error Boundary for Application-Level Error Handling
        self.global_error_boundary = create_error_boundary(
            "internal_assistant_app",
            "system",
            "Internal Assistant temporarily unavailable",
        )
        logger.info(
            "Global error boundary initialized for application-level error handling"
        )

        # Initialize Event Router Infrastructure
        self._event_router = EventRouter()
        self._event_bridge = EventBridge(self._event_router)

        # Initialize document utility builder
        self._doc_utility_builder = DocumentUtilityBuilder(
            ingest_service=ingest_service, chat_service=chat_service
        )

        # Initialize document library builder
        self._doc_library_builder = DocumentLibraryBuilder(
            ingest_service=ingest_service,
            chat_service=chat_service,
            utility_builder=self._doc_utility_builder,
        )

        # Initialize document state manager
        self._doc_state_manager = DocumentStateManager(
            ingest_service=ingest_service,
            chat_service=chat_service,
            feeds_service=feeds_service,
            utility_builder=self._doc_utility_builder,
            library_builder=self._doc_library_builder,
            event_builder=None,  # Will be set after event builder is created
        )

        # Initialize document event handler builder
        self._doc_event_builder = DocumentEventHandlerBuilder(
            ingest_service=ingest_service,
            chat_service=chat_service,
            utility_builder=self._doc_utility_builder,
            library_builder=self._doc_library_builder,
            upload_file_method=self._upload_file,
            get_model_status_method=self._doc_state_manager.get_model_status,
            document_service_facade=(
                self._ui_service_integration.document_service
                if self._use_service_facades
                else None
            ),
        )

        # Set the event builder reference in state manager
        self._doc_state_manager._event_builder = self._doc_event_builder

        # Initialize feeds display builder
        self._feeds_display_builder = FeedsDisplayBuilder(feeds_service=feeds_service)

        # Initialize display utility builder
        self._display_utility_builder = DisplayUtilityBuilder(
            feeds_service=feeds_service
        )

        # Initialize MITRE data loader for async threat intelligence loading
        self._mitre_loader = get_mitre_loader()
        logger.info("MITRE data loader initialized")

        # Start background MITRE data loading (non-blocking)
        self._mitre_loader.load_data_async()

        # Initialize complex display builder
        self._complex_display_builder = ComplexDisplayBuilder(
            ingest_service=ingest_service, doc_utility_builder=self._doc_utility_builder
        )

        # Initialize chat event handler builder
        self._chat_event_builder = ChatEventHandlerBuilder(
            chat_service=chat_service,
            chunks_service=chunks_service,
            ingest_service=ingest_service,
            summarize_service=summarizeService,
            list_ingested_files_func=self._list_ingested_files,
            create_context_filter_func=self._create_context_filter,
            system_prompt_getter=lambda: self._system_prompt,
        )

        # Initialize feeds event handler builder
        self._feeds_event_builder = FeedsEventHandlerBuilder(
            feeds_service=feeds_service
        )

        # Initialize settings event handler builder
        self._settings_event_builder = SettingsEventHandlerBuilder(
            get_default_system_prompt_func=self._get_default_system_prompt,
            reset_settings_func=None,  # Will be set after builder is created
        )

        # Set the reset function to use the builder's reset settings handler method
        self._settings_event_builder.reset_settings_func = (
            self._settings_event_builder.create_reset_settings_handler()
        )

        # Phase 2: Initialize State Management Infrastructure
        logger.info("Initializing state management system...")

        # Create initial application state from legacy values
        initial_state = create_application_state_from_legacy(
            legacy_mode=settings().ui.default_mode,
            legacy_system_prompt="",  # Will be set below
            legacy_temperature=0.1,
            legacy_similarity=0.7,
            legacy_citation_style="Include Sources",
        )

        # Initialize state integration manager with application state
        self._state_integration = StateIntegrationManager(initial_state)

        # Get references to core state management components
        self._state_store = self._state_integration.state_store
        self._app_state = self._state_integration.app_state

        # Initialize Gradio-State synchronization system (Phase 2.5 fix)
        self._gradio_sync = create_gradio_sync(self._state_store)

        # Initialize message bus for cross-component communication
        self._message_bus = MessageBus()

        # Initialize session manager for conversation persistence

        session_storage_path = PROJECT_ROOT_PATH / "local_data" / "sessions"
        self._session_manager = create_default_session_manager(
            storage_path=session_storage_path, message_bus=self._message_bus
        )

        logger.info("State management system initialized successfully")

        logger.info("⚙️ Setting up UI block cache and mode initialization")

        # Initialize system prompt based on default mode (now managed by state)
        # Map from settings keys to new mode enums with backward compatibility
        logger.info("🔧 Creating default mode map")
        default_mode_map = {
            # New mode names
            "DOCUMENT": Modes.DOCUMENT_ASSISTANT,
            "GENERAL": Modes.GENERAL_ASSISTANT,
            # Backward compatibility for old mode names
            "RAG": Modes.DOCUMENT_ASSISTANT,
            "SEARCH": Modes.DOCUMENT_ASSISTANT,
            "COMPARE": Modes.DOCUMENT_ASSISTANT,
            "SUMMARIZE": Modes.DOCUMENT_ASSISTANT,
            "DIRECT": Modes.GENERAL_ASSISTANT,
            # Full names for flexibility
            "Document Assistant": Modes.DOCUMENT_ASSISTANT,
            "Document Search": Modes.DOCUMENT_ASSISTANT,
            "Document Compare": Modes.DOCUMENT_ASSISTANT,
            "Document Summary": Modes.DOCUMENT_ASSISTANT,
            "General Assistant": Modes.GENERAL_ASSISTANT,
        }
        logger.info("🎯 Getting default mode from settings")
        default_mode = default_mode_map.get(
            settings().ui.default_mode, Modes.DOCUMENT_ASSISTANT
        )
        logger.info(f"📝 Getting default system prompt for mode: {default_mode}")
        default_system_prompt = self._get_default_system_prompt(default_mode)

        logger.info("✅ InternalAssistantUI __init__ completed successfully!")

    def _load_force_dark_js(self) -> str:
        """Load the force dark theme JavaScript.

        Returns:
            JavaScript code for forcing dark theme
        """
        js_file = Path(__file__).parent / "styles" / "force_dark.js"
        if js_file.exists():
            try:
                return js_file.read_text()
            except Exception as e:
                logger.error(f"Failed to load force dark JS: {e}")
                return ""
        return ""

    # ============================================================================
    # State Management Properties
    # ============================================================================

    @property
    def _default_mode(self) -> Modes:
        """Get the current chat mode from state."""
        mode_str = self._state_integration.get_state_value(
            "chat.mode", Modes.DOCUMENT_ASSISTANT.value
        )
        # Convert string back to enum
        if mode_str == Modes.GENERAL_ASSISTANT.value:
            return Modes.GENERAL_ASSISTANT
        return Modes.DOCUMENT_ASSISTANT

    @property
    def _system_prompt(self) -> str:
        """Get the current system prompt from state."""
        return self._state_integration.get_state_value("settings.system_prompt", "")

    @property
    def mode(self) -> str:
        """Get the current mode as string (for backward compatibility)."""
        return self._state_integration.get_state_value(
            "chat.mode", Modes.DOCUMENT_ASSISTANT.value
        )

    @mode.setter
    def mode(self, value: str) -> None:
        """Set the current mode and update state."""
        normalized_mode = normalize_mode(value)
        self._state_integration.set_state_value("chat.mode", normalized_mode)
        # Update system prompt when mode changes
        new_prompt = self._get_default_system_prompt(Modes(normalized_mode))
        self._state_integration.set_state_value("settings.system_prompt", new_prompt)

    def _register_component_state_bindings(
        self, component_refs: dict[str, Any]
    ) -> None:
        """Register UI components with the new Gradio-State synchronization system for automatic UI updates."""
        try:
            # Comprehensive component-to-state mapping with proper Gradio sync
            COMPONENT_STATE_MAPPING = {
                # Chat Components - need bidirectional sync
                "chat_input": "chat.current_input",
                "mode_selector": "chat.mode",
                # Document Management - mostly state-to-UI sync
                "doc_search_input": "documents.filter.search_query",
                "current_filter_type": "documents.filter.type",
                "current_search_query": "documents.filter.search_query",
                # Settings - bidirectional sync for form controls
                "similarity_threshold": "settings.rag.similarity_threshold",
                "response_temperature": "settings.chat.temperature",
                "citation_style": "settings.chat.citation_style",
                "response_length": "settings.chat.response_length",
                "system_prompt_templates": "settings.template.selected",
                "system_prompt_input": "settings.system_prompt",
                # Advanced Settings - bidirectional sync
                "calc_input": "settings.calculator.input",
                "definition_shortcuts": "settings.shortcuts.selected",
                "model_selection": "settings.model.selected",
                "writing_style": "settings.chat.writing_style",
                "temperature_control": "settings.chat.temperature_advanced",
            }

            # Register components with new Gradio sync system
            registered_count = 0
            for component_name, state_path in COMPONENT_STATE_MAPPING.items():
                if component_name in component_refs:
                    try:
                        # Use the new GradioStateSync system instead of old StateIntegrationManager
                        self._gradio_sync.bind_component(
                            component_name=component_name,
                            component_ref=component_refs[component_name],
                            state_path=state_path,
                            bidirectional=True,  # Most components need bidirectional sync
                        )
                        registered_count += 1
                        logger.debug(
                            f"Bound component '{component_name}' to state path '{state_path}' with GradioStateSync"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to bind component '{component_name}': {e}"
                        )

            logger.info(
                f"Successfully registered {registered_count}/{len(COMPONENT_STATE_MAPPING)} components with GradioStateSync system"
            )

            logger.info("📌 Storing component mapping")
            # Store component mapping for later use in event handlers
            self._component_state_mapping = COMPONENT_STATE_MAPPING
            logger.info("📌 Storing bound components")
            self._bound_components = component_refs
            logger.info("✅ Component state bindings completed")

        except Exception as e:
            logger.error(f"Failed to register component state bindings: {e}")

    def _register_components_with_message_bus(
        self, component_refs: dict[str, Any]
    ) -> None:
        """Register UI components with the MessageBus for cross-component communication."""
        try:
            from internal_assistant.ui.state.message_bus import MessageType

            # Component registration mapping for MessageBus
            COMPONENT_COMMUNICATION_MAPPING = {
                # Chat Components - can send/receive messages about mode changes, clear events
                "chat_input": [
                    MessageType.CHAT_INPUT_CHANGED,
                    MessageType.MODE_CHANGED,
                ],
                "chatbot": [MessageType.CHAT_HISTORY_UPDATED, MessageType.CLEAR_CHAT],
                "mode_selector": [MessageType.MODE_CHANGED, MessageType.STATE_UPDATED],
                # Document Components - can send/receive messages about uploads, filters
                "upload_button": [
                    MessageType.DOCUMENT_UPLOADED,
                    MessageType.STATE_UPDATED,
                ],
                "folder_upload_button": [
                    MessageType.BULK_UPLOAD_STARTED,
                    MessageType.STATE_UPDATED,
                ],
                "doc_search_input": [
                    MessageType.SEARCH_QUERY_CHANGED,
                    MessageType.FILTER_CHANGED,
                ],
                "current_filter_type": [
                    MessageType.FILTER_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "current_search_query": [
                    MessageType.SEARCH_QUERY_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                # Filter buttons - can send filter change messages
                "filter_all_btn": [MessageType.FILTER_CHANGED],
                "filter_recent_btn": [MessageType.FILTER_CHANGED],
                "filter_updated_btn": [MessageType.FILTER_CHANGED],
                "filter_analyzed_btn": [MessageType.FILTER_CHANGED],
                "filter_pdf_btn": [MessageType.FILTER_CHANGED],
                "filter_excel_btn": [MessageType.FILTER_CHANGED],
                "filter_word_btn": [MessageType.FILTER_CHANGED],
                "filter_other_btn": [MessageType.FILTER_CHANGED],
                # Settings Components - can send/receive settings change messages
                "similarity_threshold": [
                    MessageType.SETTINGS_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "response_temperature": [
                    MessageType.SETTINGS_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "citation_style": [
                    MessageType.SETTINGS_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "response_length": [
                    MessageType.SETTINGS_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "system_prompt_input": [
                    MessageType.PROMPT_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                # External Info Components - can send refresh messages
                "current_feed_category": [
                    MessageType.FEED_FILTER_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
                "current_days_filter": [
                    MessageType.FEED_FILTER_CHANGED,
                    MessageType.STATE_UPDATED,
                ],
            }

            registered_count = 0
            for (
                component_name,
                message_types,
            ) in COMPONENT_COMMUNICATION_MAPPING.items():
                if component_name in component_refs:
                    try:
                        # Register component as both publisher and subscriber for its message types
                        for message_type in message_types:
                            # Subscribe to relevant messages
                            self._message_bus.subscribe(
                                message_type,
                                self._create_component_message_handler(
                                    component_name, message_type
                                ),
                                subscriber_id=f"{component_name}_handler",
                            )

                        registered_count += 1
                        logger.debug(
                            f"Registered component '{component_name}' with MessageBus for {len(message_types)} message types"
                        )

                    except Exception as e:
                        logger.warning(
                            f"Failed to register component '{component_name}' with MessageBus: {e}"
                        )

            logger.info(
                f"Successfully registered {registered_count}/{len(COMPONENT_COMMUNICATION_MAPPING)} components with MessageBus"
            )

        except Exception as e:
            logger.error(f"Failed to register components with MessageBus: {e}")

    def _create_component_message_handler(
        self, component_name: str, message_type
    ) -> Callable:
        """Create a message handler for cross-component communication."""

        def handler(message_data: Any) -> None:
            try:
                logger.debug(
                    f"Component '{component_name}' received message of type {message_type}: {message_data}"
                )

                # Handle different message types
                if hasattr(message_type, "name"):
                    message_name = message_type.name
                else:
                    message_name = str(message_type)

                # Route messages to appropriate handlers based on component and message type
                if "filter" in component_name and "FILTER_CHANGED" in message_name:
                    self._handle_filter_sync_message(component_name, message_data)
                elif (
                    "mode_selector" in component_name and "MODE_CHANGED" in message_name
                ):
                    self._handle_mode_sync_message(message_data)
                elif "SETTINGS_CHANGED" in message_name:
                    self._handle_settings_sync_message(component_name, message_data)
                elif "STATE_UPDATED" in message_name:
                    self._handle_state_sync_message(component_name, message_data)

            except Exception as e:
                logger.error(f"Message handler error for {component_name}: {e}")

        return handler

    def _handle_filter_sync_message(
        self, component_name: str, message_data: Any
    ) -> None:
        """Handle filter synchronization messages."""
        try:
            # Sync filter state across all filter components
            if hasattr(message_data, "filter_type"):
                self._state_integration.set_state_value(
                    "documents.filter.type", message_data.filter_type
                )
            logger.debug(f"Synchronized filter state from {component_name}")
        except Exception as e:
            logger.error(f"Filter sync error: {e}")

    def _handle_mode_sync_message(self, message_data: Any) -> None:
        """Handle mode change synchronization messages."""
        try:
            # Update system prompt when mode changes via MessageBus
            if hasattr(message_data, "mode"):
                new_mode = message_data.mode
                new_prompt = self._get_default_system_prompt(Modes(new_mode))
                self._state_integration.set_state_value(
                    "settings.system_prompt", new_prompt
                )
            logger.debug("Synchronized mode change across components")
        except Exception as e:
            logger.error(f"Mode sync error: {e}")

    def _handle_settings_sync_message(
        self, component_name: str, message_data: Any
    ) -> None:
        """Handle settings synchronization messages."""
        try:
            # Broadcast settings changes to all relevant components
            logger.debug(
                f"Settings changed in {component_name}, broadcasting to other components"
            )
        except Exception as e:
            logger.error(f"Settings sync error: {e}")

    def _handle_state_sync_message(
        self, component_name: str, message_data: Any
    ) -> None:
        """Handle general state synchronization messages."""
        try:
            # General state synchronization logic
            logger.debug(f"State updated in {component_name}")
        except Exception as e:
            logger.error(f"State sync error: {e}")

    def _create_state_update_handler(self, state_path: str) -> Callable[[Any], Any]:
        """Create a handler that updates state when a component changes."""

        def handler(new_value: Any) -> Any:
            self._state_integration.set_state_value(state_path, new_value)
            return new_value

        return handler

    def _create_ui_sync_handler(self, component_names: list[str]) -> Callable:
        """Create a handler that applies pending UI updates from state changes.

        This is the key method that makes state changes automatically update the UI.
        Use this in Gradio event handlers to apply state-driven updates.

        Args:
            component_names: List of component names that should be updated

        Returns:
            Handler function that returns updated values for the components
        """
        return self._gradio_sync.create_update_handler(component_names)

    def _create_bidirectional_handler(
        self, component_name: str, state_path: str, update_components: list[str] = None
    ) -> Callable:
        """Create a bidirectional handler that updates state and then syncs UI.

        This combines state update + UI sync in one handler.

        Args:
            component_name: Name of the component that changed
            state_path: State path to update
            update_components: List of other components to update (default: just the changed component)

        Returns:
            Handler function for bidirectional sync
        """
        if update_components is None:
            update_components = [component_name]

        state_handler = self._gradio_sync.create_state_update_handler(
            component_name, state_path
        )
        ui_handler = self._gradio_sync.create_update_handler(update_components)

        def combined_handler(value: Any) -> Any:
            # Update state first
            state_handler(value)
            # Then sync UI
            return ui_handler()

        return combined_handler

    def _chat(
        self,
        message: str,
        history: list[list[str]],
        mode: Modes,
        system_prompt_input,
        similarity_threshold: float = 0.7,
        response_temperature: float = 0.1,
        citation_style: str = "Include Sources",
        response_length: str = "Medium",
        *_: Any,
    ) -> Any:
        # Validate input to prevent None/empty vectors from breaking vector search
        if not message or message.strip() == "" or message is None:
            yield "Please enter a valid message."
            return

        def yield_deltas(completion_gen: CompletionGen) -> Iterable[str]:
            full_response: str = ""
            stream = completion_gen.response
            for delta in stream:
                if isinstance(delta, str):
                    full_response += str(delta)
                elif isinstance(delta, ChatResponse):
                    full_response += delta.delta or ""
                yield full_response
                time.sleep(0.02)

            # Apply citation style settings for document sources with enhanced correlation
            if completion_gen.sources and citation_style != "Exclude Sources":
                full_response += SOURCES_SEPARATOR
                cur_sources = Source.curate_sources(completion_gen.sources)
                sources_text = "\n\n**📄 Document Sources:**\n\n"
                used_files = set()

                for index, source in enumerate(cur_sources, start=1):
                    if f"{source.file}-{source.page}" not in used_files:
                        if citation_style == "Minimal Citations":
                            sources_text = sources_text + f"{index}. {source.file}\n"
                        else:  # Include Sources (full citations)
                            sources_text = (
                                sources_text
                                + f"{index}. {source.file} (page {source.page}) \n\n"
                            )
                        used_files.add(f"{source.file}-{source.page}")

                sources_text += "*Document sources from knowledge base*\n"
                sources_text += "<hr>\n\n"
                full_response += sources_text

            yield full_response

        def yield_tokens(token_gen: TokenGen) -> Iterable[str]:
            full_response: str = ""
            for token in token_gen:
                full_response += str(token)
                yield full_response

        def build_history() -> list[ChatMessage]:
            history_messages: list[ChatMessage] = []

            for interaction in history:
                history_messages.append(
                    ChatMessage(content=interaction[0], role=MessageRole.USER)
                )
                if len(interaction) > 1 and interaction[1] is not None:
                    history_messages.append(
                        ChatMessage(
                            # Remove from history content the Sources information
                            content=interaction[1].split(SOURCES_SEPARATOR)[0],
                            role=MessageRole.ASSISTANT,
                        )
                    )

            # max 20 messages to try to avoid context overflow
            return history_messages[:20]

        new_message = ChatMessage(content=message, role=MessageRole.USER)
        all_messages = [*build_history(), new_message]

        # Use system prompt as-is for better performance
        system_prompt = self._system_prompt or ""

        # If a system prompt is set, add it as a system message
        if system_prompt:
            all_messages.insert(
                0,
                ChatMessage(
                    content=system_prompt,
                    role=MessageRole.SYSTEM,
                ),
            )

        # Normalize mode to ensure backward compatibility
        normalized_mode = normalize_mode(mode)
        logger.info(f"Processing query in {normalized_mode} mode")

        match normalized_mode:
            case Modes.DOCUMENT_ASSISTANT.value:
                # Document Assistant mode - search documents for contextual answers
                try:
                    available_files = self._list_ingested_files()
                    if not available_files or len(available_files) == 0:
                        yield "📄 **Document Assistant Mode - No Documents Available**\n\nI'm in Document Assistant mode but couldn't find any uploaded documents to search. Here's what you can do:\n\n• **📁 Upload Files**: Use the Upload tab to add documents\n• **📂 Upload Folders**: Use the Folder tab to ingest directories\n• **🤖 Switch Mode**: Use General Assistant for questions that don't require documents\n\n**Supported formats**: PDF, Word, Excel, PowerPoint, Text, Markdown, and more\n\nOnce documents are uploaded, I'll search through them to provide contextual answers."
                        return
                except Exception as e:
                    yield "⚠️ **Document Assistant Mode - Error**\n\nI couldn't access your document library. This might be a temporary issue.\n\n**Try these solutions:**\n• Refresh the page and try again\n• Switch to General Assistant mode for non-document questions\n• Check if your documents are still uploading\n\nIf the problem persists, please contact support."
                    return

                context_filter = self._create_context_filter()

                if self._use_service_facades:
                    query_stream = self._service_compatibility.stream_chat(
                        messages=all_messages,
                        use_context=True,
                        context_filter=context_filter,
                    )
                else:
                    query_stream = self._chat_service.stream_chat(
                        messages=all_messages,
                        use_context=True,
                        context_filter=context_filter,
                    )
                yield from yield_deltas(query_stream)

            case Modes.GENERAL_ASSISTANT.value:
                # General Assistant mode - direct LLM without document search
                if self._use_service_facades:
                    query_stream = self._service_compatibility.stream_chat(
                        messages=all_messages,
                        use_context=False,  # No document context
                        context_filter=None,
                    )
                else:
                    query_stream = self._chat_service.stream_chat(
                        messages=all_messages,
                        use_context=False,  # No document context
                        context_filter=None,
                    )
                yield from yield_deltas(query_stream)

    # On initialization and on mode change, this function set the system prompt
    # to the default prompt based on the mode (and user settings).
    @staticmethod
    def _get_default_system_prompt(mode: Modes) -> str:
        match mode:
            case Modes.DIRECT_CHAT:
                # Foundation-Sec-8B already knows cybersecurity - minimal prompt
                return "Answer questions directly and concisely."

            case Modes.RAG_MODE:
                # Foundation-Sec-8B knows how to analyze security docs - minimal prompt
                return "Use document context to answer questions."

            case Modes.COMPARE_MODE:
                # Foundation-Sec-8B knows how to compare security documents
                return "Compare and analyze the provided documents."

            case Modes.SEARCH_MODE:
                # Foundation-Sec-8B knows how to search security content
                return "Find relevant information from documents."

            case Modes.SUMMARIZE_MODE:
                # Foundation-Sec-8B knows how to summarize security content
                return "Provide concise summaries."

            case _:
                # Default fallback - minimal
                return "Answer directly."

    @staticmethod
    def _get_default_mode_explanation(mode: Modes) -> str:
        match mode:
            case Modes.RAG_MODE:
                return "💬 Ask questions about your uploaded documents with enhanced correlation analysis. Get intelligent answers that draw connections across your entire document collection."
            case Modes.SEARCH_MODE:
                return "🔍 Search through all documents to find specific information, quotes, or references with intelligent cross-document correlation."
            case Modes.COMPARE_MODE:
                return "⚖️ Advanced document correlation analysis. Compare policies, identify patterns, track changes over time, and discover relationships between documents."
            case Modes.SUMMARIZE_MODE:
                return "📄 Generate intelligent summaries that identify themes spanning multiple documents and highlight key correlations and insights."
            case Modes.DIRECT_CHAT:
                return "🧠 General banking assistant for calculations, definitions, and questions that don't require document lookup."
            case _:
                return ""

    def _set_system_prompt(self, system_prompt_input: str) -> None:
        logger.info(f"Setting system prompt to: {system_prompt_input}")
        # Update the centralized state instead of instance variable
        self._state_integration.set_state_value(
            "settings.system_prompt", system_prompt_input
        )

    # Removed _analyze_response_and_recommend method - no longer needed for deterministic mode selection

    def _get_model_info(self) -> dict:
        """Get information about the current LLM and embedding models."""
        return self._doc_state_manager.get_model_info()

    def _list_ingested_files(self) -> list[list[str]]:
        """List all ingested files using DocumentUtilityBuilder."""
        return self._doc_utility_builder.list_ingested_files()

    def _format_file_list(self) -> str:
        """Format file list as HTML using DocumentUtilityBuilder."""
        return self._doc_utility_builder.format_file_list()

    def _get_document_library_html(
        self, search_query: str = "", filter_tags: list = None
    ) -> str:
        """Generate HTML for document library using DocumentLibraryBuilder."""
        return self._doc_library_builder.get_document_library_html(
            search_query, filter_tags
        )

    def _analyze_document_types(self) -> dict:
        """Analyze document types using DocumentStateManager."""
        return self._doc_state_manager.analyze_document_types()

    def _get_processing_queue_html(self) -> str:
        """Generate HTML for processing queue with actual document processing status and stages."""
        return self._doc_state_manager.get_processing_queue_html()

    def _get_chat_mentioned_documents(self) -> set:
        """Get set of documents mentioned in chat using DocumentLibraryBuilder."""
        return self._doc_library_builder.get_chat_mentioned_documents()

    def _filter_documents(
        self, search_query: str = "", filter_type: str = "all"
    ) -> tuple[str, str]:
        """Filter documents using DocumentLibraryBuilder."""
        return self._doc_library_builder.filter_documents(search_query, filter_type)

    def _generate_filtered_document_html(
        self, filtered_files: list, doc_metadata: dict
    ) -> str:
        """Generate filtered document HTML using DocumentLibraryBuilder."""
        return self._doc_library_builder.generate_filtered_document_html(
            filtered_files, doc_metadata
        )

    def _get_document_counts(self) -> dict[str, int]:
        """Get document counts using DocumentLibraryBuilder."""
        return self._doc_library_builder.get_document_counts()

    def _format_feeds_display(
        self, source_filter: str = None, days_filter: int = None
    ) -> str:
        """Format RSS feeds for display in the UI using FeedsDisplayBuilder."""
        return self._feeds_display_builder.format_feeds_display(
            source_filter, days_filter
        )

    def _format_cve_display(
        self,
        source_filter: str = None,
        severity_filter: str = "All Severities",
        vendor_filter: str = "All Vendors",
    ) -> str:
        """Format CVE data for display using DisplayUtilityBuilder."""
        return self._display_utility_builder.format_cve_display(
            source_filter, severity_filter, vendor_filter
        )

    def _get_cve_data(self) -> list:
        """Get CVE data from feeds service using FeedsDisplayBuilder."""
        return self._feeds_display_builder.get_cve_data()

    def _is_feeds_cache_empty(self) -> bool:
        """Check if the feeds cache is empty using FeedsDisplayBuilder."""
        return self._feeds_display_builder.is_feeds_cache_empty()

    def _extract_cve_id(self, text: str) -> str:
        """Extract CVE ID from text using DisplayUtilityBuilder."""
        return self._display_utility_builder.extract_cve_id(text)

    def _determine_cve_severity(self, text: str) -> str:
        """Determine CVE severity using DisplayUtilityBuilder."""
        return self._display_utility_builder.determine_cve_severity(text)

    def _format_ai_security_feeds(
        self, time_filter: str = "7d", category_filter: str = "All"
    ) -> str:
        """Format AI & Security feeds for display.

        Args:
            time_filter: Time filter (24h, 7d, 30d, 90d)
            category_filter: Category filter (All, AI Research, AI Security, etc.)

        Returns:
            HTML string for feed display
        """
        try:
            # Parse time filter to days
            days_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days_filter = days_map.get(time_filter, 7)

            # Get feeds with filtering
            # For category filtering, we'll filter by category in the display
            # Pass None as source_filter to get all sources, then filter by category
            source_filter = None

            # Use FeedsDisplayBuilder to format display
            feeds_html = self._feeds_display_builder.format_feeds_display(
                source_filter=source_filter, days_filter=days_filter
            )

            # If category filter is not "All", filter the HTML by category
            if category_filter != "All":
                # Get feeds and filter by category
                feeds_data = self._feeds_service.get_feeds(source_filter, days_filter)

                # Filter feeds by category
                category_sources = self._feeds_service.SOURCE_CATEGORIES.get(
                    category_filter, []
                )
                if category_sources:
                    filtered_feeds = [
                        feed
                        for feed in feeds_data
                        if feed.get("source") in category_sources
                    ]

                    # If we have filtered feeds, format them
                    if filtered_feeds:
                        # Manually build HTML for filtered feeds
                        feeds_html = self._build_filtered_feeds_html(filtered_feeds)
                    else:
                        feeds_html = f"""
                        <div class='feed-content'>
                            <div style='text-align: center; color: #666; padding: 20px;'>
                                <div>🔍 No feeds found for category: {category_filter}</div>
                                <div style='font-size: 12px; margin-top: 8px;'>
                                    Try adjusting your filters or refresh the feeds
                                </div>
                            </div>
                        </div>"""

            return feeds_html

        except Exception as e:
            logger.error(f"Error formatting AI & Security feeds: {e}", exc_info=True)
            return """
            <div class='feed-content error'>
                <div style='text-align: center; color: #ff6b6b; padding: 20px;'>
                    <div>❌ Error loading feeds</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        Click REFRESH to try again
                    </div>
                </div>
            </div>"""

    def _build_filtered_feeds_html(self, feeds_data: list) -> str:
        """Build HTML for filtered feeds list.

        Args:
            feeds_data: List of feed dictionaries

        Returns:
            HTML string
        """
        try:
            html_content = """
            <script>
            function confirmOpenExternal(url, title) {
                if (confirm('Open external link: ' + title + '?')) {
                    window.open(url, '_blank');
                }
            }
            </script>
            <div class='feed-content' style='max-height: none; height: auto; overflow-y: auto; overflow-x: auto; padding-right: 8px;'>"""

            # Group feeds by source
            sources = {}
            for feed in feeds_data:
                source = feed["source"]
                if source not in sources:
                    sources[source] = []
                sources[source].append(feed)

            # Sort feeds within each source by date
            for source in sources:
                sources[source].sort(key=lambda x: x["published"], reverse=True)

            for source, source_feeds in sources.items():
                # Get source color
                source_color = feed["color"]

                html_content += f"""
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' style='color: {source_color}; margin: 16px 0 8px 0;'>
                        {source} ({len(source_feeds)} items)
                    </h4>
                    <div class='feed-items' style='margin-left: 16px;'>"""

                # Display feeds for this source (limit to 10)
                for feed in source_feeds[:10]:
                    published_date = feed.get("published", "Unknown Date")
                    title = feed.get("title", "No Title")
                    link = feed.get("link", "#")
                    summary = feed.get("summary", "No summary available")

                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                    html_content += f"""
                    <div class='feed-item' style='margin-bottom: 16px; padding: 12px; background: #1a1a1a; border-radius: 8px; border-left: 3px solid {source_color};'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                            <h5 style='margin: 0; color: #e0e0e0; font-size: 14px; font-weight: 600;'>
                                <a href='javascript:void(0)' onclick='confirmOpenExternal("{link}", "{title}")' style='color: inherit; text-decoration: none;'>{title}</a>
                            </h5>
                            <span style='color: #888; font-size: 11px; white-space: nowrap; margin-left: 8px;'>{published_date}</span>
                        </div>
                        <p style='margin: 0; color: #ccc; font-size: 12px;'>{summary}</p>
                    </div>"""

                html_content += """
                    </div>
                </div>"""

            html_content += "</div>"
            return html_content

        except Exception as e:
            logger.error(f"Error building filtered feeds HTML: {e}")
            return """
            <div class='feed-content error'>
                <div style='text-align: center; color: #ff6b6b; padding: 20px;'>
                    <div>❌ Error displaying feeds</div>
                </div>
            </div>"""

    def _format_mitre_display(
        self,
        domain_filter: str = "Enterprise",
        domain_focus: str = "All Domains",
        search_query: str = None,
        tactic_filter: str = "All Tactics",
        show_groups: bool = False,
        banking_focus: bool = False,
    ) -> str:
        """Format MITRE ATT&CK data for display using DisplayUtilityBuilder with cached data when available."""
        # Try to use cached data first to avoid blocking calls
        cached_data = self._mitre_loader.get_cached_data()
        return self._display_utility_builder.format_mitre_display(
            domain_filter,
            domain_focus,
            search_query,
            tactic_filter,
            show_groups,
            banking_focus,
            cached_data,
        )

    def _get_mitre_data(self) -> dict:
        """Get MITRE ATT&CK data using DisplayUtilityBuilder."""
        return self._display_utility_builder.get_mitre_data()

    def _get_domain_techniques(self, domain: str) -> list:
        """Get list of domain-relevant MITRE ATT&CK techniques using DisplayUtilityBuilder."""
        return self._display_utility_builder.get_domain_techniques(domain)

    def _get_mitre_loading_status(self) -> tuple[str, str]:
        """Get current MITRE loading status for UI updates.

        Returns:
            Tuple of (status_html, content_html)
        """
        status_info = self._mitre_loader.get_loading_status()

        if status_info["is_loading"]:
            status_html = (
                "<div class='feed-status loading'>🔄 Loading MITRE ATT&CK data...</div>"
            )
            content_html = """
            <div class='feed-content'>
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div>🛡️ Loading MITRE ATT&CK threat intelligence...</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        Please wait while data is being fetched and processed
                    </div>
                </div>
            </div>"""
        elif status_info["data_available"]:
            # Data is available, format it
            cached_data = self._mitre_loader.get_cached_data()
            if cached_data and cached_data.get("_metadata"):
                technique_count = cached_data["_metadata"].get("technique_count", 0)
                load_time = cached_data["_metadata"].get("load_time", "")

                status_html = f"<div class='feed-status success'>✅ MITRE data loaded ({technique_count} techniques)</div>"
                content_html = self._format_mitre_display_from_cache(cached_data)
            else:
                status_html = (
                    "<div class='feed-status success'>✅ MITRE data available</div>"
                )
                content_html = self._format_mitre_display()
        else:
            # No data available yet
            status_html = (
                "<div class='feed-status warning'>⚠️ MITRE data unavailable</div>"
            )
            content_html = """
            <div class='feed-content'>
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div>🛡️ MITRE ATT&CK data not loaded</div>
                    <div style='font-size: 12px; margin-top: 8px; color: #888;'>
                        Click the "Refresh MITRE Data" button to load threat intelligence
                    </div>
                </div>
            </div>"""

        return status_html, content_html

    def _format_mitre_display_from_cache(self, cached_data: dict) -> str:
        """Format MITRE display using cached data for optimal performance.

        Args:
            cached_data: Cached MITRE data from AsyncMitreDataLoader

        Returns:
            Formatted HTML string
        """
        try:
            techniques = cached_data.get("techniques", [])
            metadata = cached_data.get("_metadata", {})

            # Build simplified display for cached data
            html_content = "<div class='feed-content'>"
            html_content += "<h4>🎯 MITRE ATT&CK Threat Intelligence</h4>"

            # Add metadata info
            if metadata:
                technique_count = metadata.get("technique_count", len(techniques))
                last_updated = metadata.get("last_updated", "Unknown")
                html_content += f"""
                <div style='font-size: 12px; color: #666; margin-bottom: 15px;'>
                    {technique_count} techniques loaded | Last updated: {last_updated[:19] if last_updated != 'Unknown' else 'Unknown'}
                </div>"""

            # Group techniques by tactic for better organization
            tactics_dict = {}
            for technique in techniques:
                tactic = technique.get("tactic", "Unknown")
                if tactic not in tactics_dict:
                    tactics_dict[tactic] = []
                tactics_dict[tactic].append(technique)

            # Display techniques grouped by tactic
            for tactic, tactic_techniques in tactics_dict.items():
                html_content += "<div class='tactic-section'>"
                html_content += (
                    f"<h5 style='color: #2c5aa0; margin: 10px 0 5px 0;'>{tactic}</h5>"
                )

                for technique in tactic_techniques[
                    :5
                ]:  # Limit to first 5 per tactic for performance
                    technique_id = technique.get("technique_id", "Unknown")
                    name = technique.get("name", "Unknown Technique")
                    description = (
                        technique.get("description", "")[:200] + "..."
                        if len(technique.get("description", "")) > 200
                        else technique.get("description", "")
                    )

                    html_content += f"""
                    <div style='border-left: 3px solid #2c5aa0; padding-left: 10px; margin: 8px 0;'>
                        <strong>{technique_id}</strong>: {name}<br>
                        <span style='font-size: 11px; color: #666;'>{description}</span>
                    </div>"""

                if len(tactic_techniques) > 5:
                    html_content += f"<div style='font-size: 11px; color: #888; margin: 5px 0;'>... and {len(tactic_techniques) - 5} more {tactic} techniques</div>"

                html_content += "</div>"

            html_content += "</div>"
            return html_content

        except Exception as e:
            logger.error(f"Error formatting cached MITRE display: {e}")
            return self._format_mitre_display()  # Fallback to regular display

    def _refresh_mitre_data_async(self) -> tuple[str, str]:
        """Refresh MITRE data asynchronously and return immediate status.

        Returns:
            Tuple of (status_html, content_html)
        """
        try:
            # Start async refresh
            self._mitre_loader.refresh_data()

            status_html = (
                "<div class='feed-status loading'>🔄 Refreshing MITRE data...</div>"
            )
            content_html = """
            <div class='feed-content'>
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div>🛡️ Refreshing MITRE ATT&CK data...</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        Data will be updated in the background. Check back in a few moments.
                    </div>
                </div>
            </div>"""

            return status_html, content_html

        except Exception as e:
            logger.error(f"Error refreshing MITRE data: {e}")
            status_html = (
                f"<div class='feed-status error'>❌ Refresh failed: {e!s}</div>"
            )
            content_html = """
            <div class='feed-content'>
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div>⚠️ Failed to refresh MITRE data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        Please try again or check the logs for details
                    </div>
                </div>
            </div>"""
            return status_html, content_html

    def _show_active_threats(self) -> str:
        """Show active threats with attack chains in MITRE panel.

        Returns:
            HTML string with active threats display
        """
        try:
            # Get active threats display from display utility builder
            threats_html = self._display_utility_builder.format_active_threats_display(
                days_filter=7
            )
            return threats_html

        except Exception as e:
            logger.error(f"Error showing active threats: {e}", exc_info=True)
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 40px 20px;'>
                    <div style='font-size: 48px; margin-bottom: 16px;'>⚠️</div>
                    <div style='font-size: 16px; font-weight: 600; margin-bottom: 8px;'>
                        Error Loading Active Threats
                    </div>
                    <div style='font-size: 12px; color: #888; margin-bottom: 16px;'>
                        {e!s}
                    </div>
                    <div style='font-size: 11px; color: #666;'>
                        Click "Refresh MITRE Data" to try again or check application logs for details.
                    </div>
                </div>
            </div>
            """

    async def _auto_refresh_all_panels_on_startup(self):
        """Auto-refresh all feed panels when server starts (no cached data).
        This ensures users see fresh data on every server restart.

        Returns:
            Tuple of (feed_status, feed_display, cve_status, cve_display,
                     ai_feed_status, ai_feed_display)
        """
        try:
            logger.info("Auto-refreshing all panels on startup...")

            # Refresh all panels in parallel for speed
            tasks = [
                self._feeds_event_builder.get_handler().refresh_feeds(),
                self._feeds_event_builder.get_handler().refresh_cve_data(),
                self._feeds_service.refresh_feeds(),  # Refresh for AI feeds
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Format AI feed display
            try:
                ai_feed_html = self._format_ai_security_feeds("7d", "All")
                ai_feed_status_html = "<div class='feed-status success'>✅ AI & Security feeds loaded</div>"
            except Exception as e:
                logger.error(f"Failed to format AI feeds: {e}")
                ai_feed_html = "<div style='padding: 20px; text-align: center; color: #666;'>Click refresh to load AI feeds</div>"
                ai_feed_status_html = (
                    "<div class='feed-status warning'>⚠️ AI feeds not loaded</div>"
                )

            # Extract status and HTML from each result
            return (
                results[0][0],
                results[0][1],  # feed_status, feed_display
                results[1][0],
                results[1][1],  # cve_status, cve_display
                ai_feed_status_html,
                ai_feed_html,  # ai_feed_status, ai_feed_display
            )
        except Exception as e:
            logger.error(f"Auto-refresh failed: {e}", exc_info=True)
            error_msg = f"⚠️ Auto-refresh failed: {e!s}"
            empty_html = "<div style='padding: 20px; text-align: center; color: #666;'>Please click refresh manually</div>"
            # Return error for all 3 panels
            return (error_msg, empty_html) * 3

    def _check_mitre_update_status(self) -> tuple[str, str]:
        """Check for MITRE data updates and return current status.
        This can be called periodically to update the UI when background loading completes.

        Returns:
            Tuple of (status_html, content_html)
        """
        return self._get_mitre_loading_status()

    def _get_recent_documents_html(self) -> str:
        """Generate HTML for recent documents with enhanced metadata using ComplexDisplayBuilder."""
        return self._complex_display_builder.get_recent_documents_html()

    def _upload_file(self, files: list[str]) -> tuple[str, str, str]:
        """Upload files with enhanced error handling and user feedback.

        Args:
            files: List of file paths to upload

        Returns:
            Tuple of (updated_file_list, status_message, updated_document_library)
        """
        logger.info("📤 [UPLOAD_FLOW] _upload_file called with %s files", len(files))

        try:
            # Validate input files
            if not files or len(files) == 0:
                logger.warning("📤 [UPLOAD_FLOW] No files provided")
                return (
                    self._doc_utility_builder.format_file_list(),
                    "⚠️ No files selected for upload",
                    self._doc_library_builder.get_document_library_html(),
                )

            # Log file details and validate file existence
            paths = []
            invalid_files = []
            large_files = []
            total_size = 0

            for file_path in files:
                path = Path(file_path)
                if path.exists():
                    size = path.stat().st_size
                    total_size += size

                    # Check for large files (>100MB)
                    if size > 100 * 1024 * 1024:
                        large_files.append(f"{path.name} ({size // (1024*1024)}MB)")

                    paths.append(path)
                    logger.info(
                        "📤 [UPLOAD_FLOW] File: %s (size: %s bytes)", path.name, size
                    )
                else:
                    invalid_files.append(str(path))
                    logger.error("📤 [UPLOAD_FLOW] File not found: %s", file_path)

            # Handle invalid files
            if invalid_files:
                error_msg = f"❌ Upload failed: {len(invalid_files)} file(s) not found: {', '.join(invalid_files)}"
                logger.error("📤 [UPLOAD_FLOW] %s", error_msg)
                return (
                    self._doc_utility_builder.format_file_list(),
                    error_msg,
                    self._doc_library_builder.get_document_library_html(),
                )

            # Warn about large files
            if large_files:
                logger.warning("📤 [UPLOAD_FLOW] Large files detected: %s", large_files)

            # Get document count before upload
            try:
                docs_before = self._ingest_service.list_ingested()
                logger.info(
                    "📤 [UPLOAD_FLOW] Documents in index before upload: %d",
                    len(docs_before),
                )
            except Exception as e:
                logger.warning(
                    "📤 [UPLOAD_FLOW] Error checking docs before upload: %s", e
                )
                docs_before = []

            # Prepare files for ingestion
            files_to_ingest = [(str(path.name), path) for path in paths]
            logger.info(
                "📤 [UPLOAD_FLOW] Preparing to upload %d files (total size: %.2f MB)",
                len(files_to_ingest),
                total_size / (1024 * 1024),
            )

            # Perform upload with comprehensive error handling
            try:
                # Check ingest mode from settings
                from internal_assistant.settings.settings import settings

                ingest_mode = settings().embedding.ingest_mode

                if ingest_mode == "simple":
                    logger.info(
                        "📤 [UPLOAD_FLOW] Starting simple file-by-file ingestion..."
                    )
                    ingested_docs = []
                    for file_name, file_path in files_to_ingest:
                        try:
                            docs = self._ingest_service.ingest_file(
                                file_name, file_path
                            )
                            ingested_docs.extend(docs)
                            logger.info(
                                f"📤 [UPLOAD_FLOW] Ingested file: {file_name} ({len(docs)} docs)"
                            )
                        except Exception as e:
                            logger.error(
                                f"📤 [UPLOAD_FLOW] Failed to ingest {file_name}: {e}"
                            )
                    logger.info("📤 [UPLOAD_FLOW] Simple ingestion completed")
                else:
                    logger.info(f"📤 [UPLOAD_FLOW] Starting {ingest_mode} ingestion...")
                    ingested_docs = self._ingest_service.bulk_ingest(files_to_ingest)
                    logger.info(f"📤 [UPLOAD_FLOW] {ingest_mode} ingestion completed")

                # Verify upload success by checking actual ingested documents
                try:
                    # Force a small delay to ensure persistence is complete
                    import time

                    time.sleep(0.2)

                    # Get fresh document list from disk
                    docs_after = self._ingest_service.list_ingested()
                    actual_ingested = len(ingested_docs)

                    logger.info(
                        "📤 [UPLOAD_FLOW] Documents before: %d, after: %d, ingested: %d",
                        len(docs_before),
                        len(docs_after),
                        actual_ingested,
                    )

                    # Use actual_ingested count as source of truth (more reliable than diff)
                    if actual_ingested > 0:
                        status_msg = f"✅ Successfully uploaded {len(files_to_ingest)} file(s). {actual_ingested} document(s) added to the knowledge base."

                        # Add large file warning to success message
                        if large_files:
                            status_msg += f" ⚠️ Large files detected: {', '.join(large_files[:2])}{'...' if len(large_files) > 2 else ''}"

                        logger.info(
                            "✅ [UPLOAD_FLOW] Upload successful: %d documents ingested",
                            actual_ingested,
                        )
                    else:
                        # Check if documents actually increased
                        new_docs_count = len(docs_after) - len(docs_before)
                        if new_docs_count > 0:
                            status_msg = f"✅ Successfully uploaded {len(files_to_ingest)} file(s). {new_docs_count} document(s) added."
                            logger.info(
                                "✅ [UPLOAD_FLOW] Upload successful via document count: %d new",
                                new_docs_count,
                            )
                        else:
                            status_msg = "⚠️ Upload completed but no new documents were added. Files may be duplicates or already exist in the knowledge base."
                            logger.warning(
                                "⚠️ [UPLOAD_FLOW] No new documents detected - possible duplicates"
                            )

                except Exception as e:
                    logger.error(
                        "❌ [UPLOAD_FLOW] Error verifying upload success: %s", e
                    )
                    # Don't show verification error to user if ingestion succeeded
                    if len(ingested_docs) > 0:
                        status_msg = f"✅ Upload completed: {len(ingested_docs)} documents processed."
                    else:
                        status_msg = f"⚠️ Upload may have succeeded but verification failed: {e!s}"

            except Exception as e:
                logger.error(
                    "❌ [UPLOAD_FLOW] Upload failed during ingestion: %s",
                    e,
                    exc_info=True,
                )

                # Provide specific error messages based on exception type
                error_msg = "❌ Upload failed: "
                if "permission" in str(e).lower():
                    error_msg += "Permission denied. Check file permissions."
                elif "memory" in str(e).lower() or "size" in str(e).lower():
                    error_msg += "File too large or insufficient memory."
                elif "format" in str(e).lower() or "parse" in str(e).lower():
                    error_msg += "Unsupported file format or corrupted file."
                else:
                    error_msg += f"Technical error - {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}"

                return (
                    self._doc_utility_builder.format_file_list(),
                    error_msg,
                    self._doc_library_builder.get_document_library_html(),
                )

            # Update UI components
            try:
                updated_file_list = self._doc_utility_builder.format_file_list()
                updated_document_library = (
                    self._doc_library_builder.get_document_library_html()
                )

                return (updated_file_list, status_msg, updated_document_library)

            except Exception as e:
                logger.error("❌ [UPLOAD_FLOW] Error updating UI components: %s", e)
                return (
                    self._doc_utility_builder.format_file_list(),
                    f"{status_msg} ⚠️ UI update warning: {e!s}",
                    self._doc_library_builder.get_document_library_html(),
                )

        except Exception as e:
            logger.error(
                "❌ [UPLOAD_FLOW] Critical error in upload process: %s",
                e,
                exc_info=True,
            )
            return (
                self._doc_utility_builder.format_file_list(),
                f"❌ Critical upload error: {e!s}",
                self._doc_library_builder.get_document_library_html(),
            )

    def _ingest_folder(self, folder_files: list[str]) -> tuple[list, str]:
        """Ingest an entire folder with progress tracking."""
        try:
            if not folder_files:
                return self._list_ingested_files(), "❌ No folder selected"

            # Get the folder path from the first file
            folder_path = Path(folder_files[0]).parent
            logger.info(f"Starting folder ingestion for: {folder_path}")

            if not folder_path.exists():
                return self._list_ingested_files(), "❌ Folder not found"

            # Import the LocalIngestWorker from the tools/data directory
            import os
            import sys

            sys.path.append(
                os.path.join(os.path.dirname(__file__), "..", "..", "tools", "data")
            )

            try:
                from ingest_folder import LocalIngestWorker

                from internal_assistant.settings.settings import settings
            except ImportError as e:
                logger.error(f"Failed to import LocalIngestWorker: {e}")
                return (
                    self._list_ingested_files(),
                    f"❌ Folder ingestion not available: {e!s}",
                )

            # Initialize worker with UI-friendly settings
            worker = LocalIngestWorker(
                self._ingest_service,
                settings(),
                max_attempts=2,
                checkpoint_file="ui_folder_ingestion_checkpoint.json",
            )

            # Start ingestion
            worker.ingest_folder(folder_path, ignored=[], resume=True)

            logger.info(f"Folder ingestion completed successfully: {folder_path}")
            return self._list_ingested_files(), "✅ Folder ingested successfully!"

        except Exception as e:
            logger.error(f"Folder ingestion failed: {e}", exc_info=True)
            return self._list_ingested_files(), f"❌ Ingestion failed: {e!s}"

    def _create_context_filter(self) -> ContextFilter | None:
        """Create a context filter using all available documents."""
        try:
            # Use all available documents
            all_doc_ids = []
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata:
                    all_doc_ids.append(ingested_document.doc_id)

            if all_doc_ids:
                logger.info(f"Searching in {len(all_doc_ids)} total documents")
                return ContextFilter(docs_ids=all_doc_ids)
            else:
                logger.warning("No documents available for search")
                return None
        except Exception as e:
            logger.error(f"Error creating context filter: {e}")
            return None

    def _set_explanatation_mode(self, explanation_mode: str) -> None:
        self._explanation_mode = explanation_mode

    @staticmethod
    def _get_system_prompt_template(template_name: str) -> str:
        """Get pre-configured system prompt templates for different use cases."""
        templates = {
            "Default Assistant": "You are a helpful AI assistant. Provide accurate, concise, and helpful responses based on the available context.",
            "Financial Analyst": "You are a financial analyst AI. Focus on financial metrics, trends, market analysis, and investment insights. Provide data-driven responses with clear explanations of financial concepts.",
            "Technical Expert": "You are a technical expert AI. Provide detailed technical explanations, focus on accuracy, include relevant technical specifications, and explain complex concepts clearly.",
            "Research Assistant": "You are a research assistant AI. Provide comprehensive analysis, cite sources when available, present multiple perspectives, and organize information logically for research purposes.",
            "Document Summarizer": "You are a document summarization AI. Extract key points, create concise summaries, highlight important findings, and organize information in a clear, structured format.",
            "Compliance Reviewer": "You are a compliance review AI. Focus on regulatory requirements, identify potential compliance issues, highlight risk factors, and provide recommendations for regulatory adherence.",
            "Custom": "",
        }
        return templates.get(template_name, templates["Default Assistant"])

    def _set_current_mode(self, mode: Modes) -> Any:
        self.mode = mode
        self._set_system_prompt(self._get_default_system_prompt(mode))
        interactive = self._system_prompt is not None
        return gr.update(placeholder=self._system_prompt, interactive=interactive)

    def _build_ui_blocks(self) -> gr.Blocks:
        logger.info("🚀 Starting UI block construction")
        logger.debug("Creating the accessible UI blocks")

        # CSS is now managed by CSSManager - no embedded CSS needed
        logger.info("📦 Creating gr.Blocks context")

        with gr.Blocks(
            title=UI_TAB_TITLE,
            theme=gr.themes.Base(),
            css=self._css_manager.load_styles(),
            head="<script>"
            + self._load_force_dark_js()
            + "</script>"
            + """<script>
            // Global file selection manager for document removal
            console.log('🔄 [JS] Initializing global file selection manager');

            // Initialize selected files set globally
            if (typeof window.selectedFiles === 'undefined') {
                window.selectedFiles = new Set();
                window.selectedFilesForRemoval = [];
                console.log('🔄 [JS] Created window.selectedFiles Set and window.selectedFilesForRemoval');
            }

            // Toggle file selection (called from onclick in file items)
            function toggleFileSelection(filename, fileId) {
                console.log('🔄 [JS] toggleFileSelection:', filename);
                const checkbox = document.querySelector('#' + fileId + ' .file-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    handleCheckboxClick(filename, checkbox.checked);
                }
            }

            // Handle checkbox click event
            function handleCheckboxClick(filename, isChecked) {
                console.log('🔄 [JS] handleCheckboxClick:', filename, isChecked);
                const fileElement = document.querySelector('[data-filename="' + filename + '"]');

                if (isChecked) {
                    window.selectedFiles.add(filename);
                    if (fileElement) {
                        fileElement.style.backgroundColor = '#004080';
                        fileElement.style.borderLeft = '4px solid #0077BE';
                    }
                } else {
                    window.selectedFiles.delete(filename);
                    if (fileElement) {
                        fileElement.style.backgroundColor = '';
                        fileElement.style.borderLeft = '';
                    }
                }

                // Update window storage for Gradio access
                window.selectedFilesForRemoval = Array.from(window.selectedFiles);
                console.log('🔄 [JS] Selected files:', window.selectedFilesForRemoval);

                // Update Gradio bridge component for Python communication
                const bridgeInput = document.getElementById('selected-files-bridge-input');
                if (bridgeInput) {
                    const jsonData = JSON.stringify(window.selectedFilesForRemoval);
                    bridgeInput.value = jsonData;
                    console.log('🔄 [JS] Updated bridge with:', jsonData);

                    // Dispatch change event to notify Gradio
                    const event = new Event('input', { bubbles: true });
                    bridgeInput.dispatchEvent(event);
                } else {
                    console.warn('⚠️ [JS] Bridge element not found');
                }

                // Update button state
                updateRemoveButtonState();
            }

            // Update remove button text and state
            function updateRemoveButtonState() {
                const removeButton = document.getElementById('remove-selected-docs');
                if (removeButton) {
                    if (window.selectedFiles.size > 0) {
                        removeButton.disabled = false;
                        removeButton.style.opacity = '1';
                        removeButton.innerHTML = '🗑️ Remove Selected (' + window.selectedFiles.size + ')';
                    } else {
                        removeButton.disabled = true;
                        removeButton.style.opacity = '0.5';
                        removeButton.innerHTML = '🗑️ Remove Selected';
                    }
                }
            }

            // Get selected files (used by Gradio _js parameter)
            function getSelectedFiles() {
                const files = Array.from(window.selectedFiles);
                console.log('🔄 [JS] getSelectedFiles called, returning:', files);
                return files;
            }

            // Clear all selections
            function clearSelectedFiles() {
                console.log('🔄 [JS] Clearing all file selections');
                window.selectedFiles.clear();
                window.selectedFilesForRemoval = [];
                document.querySelectorAll('.file-checkbox').forEach(function(checkbox) {
                    checkbox.checked = false;
                });
                document.querySelectorAll('.file-item').forEach(function(item) {
                    item.style.backgroundColor = '';
                    item.style.borderLeft = '';
                });
                updateRemoveButtonState();
            }

            // Handle operation success (auto-clear selections)
            function handleOperationSuccess() {
                console.log('🔄 [JS] Operation successful, clearing selections');
                clearSelectedFiles();
            }

            // Listen for success events
            document.addEventListener('documentOperationSuccess', handleOperationSuccess);

            // Remove Selected - Direct API call approach (Gradio 4.15.0 compatible)
            async function handleRemoveSelectedFiles() {
                console.log('🗑️ [REMOVE] handleRemoveSelectedFiles called');

                // Get selected files from the Set
                const selectedFilesArray = Array.from(window.selectedFiles);
                console.log('🗑️ [REMOVE] Selected files:', selectedFilesArray);

                if (selectedFilesArray.length === 0) {
                    console.warn('⚠️ [REMOVE] No files selected');
                    // Show warning message in UI
                    const statusElement = document.querySelector('.remove-status');
                    if (statusElement) {
                        statusElement.innerHTML = '<div style="color: #ff9800; padding: 10px;">⚠️ Please select files to remove</div>';
                        setTimeout(() => statusElement.innerHTML = '', 3000);
                    }
                    return;
                }

                try {
                    console.log('🗑️ [REMOVE] Calling API to delete files:', selectedFilesArray);

                    // Call the FastAPI endpoint directly
                    const response = await fetch('/v1/ingest/delete_by_filenames', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            file_names: selectedFilesArray
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const result = await response.json();
                    console.log('✅ [REMOVE] Deletion successful:', result);

                    // Show success message
                    const statusElement = document.querySelector('.remove-status');
                    if (statusElement) {
                        statusElement.innerHTML = `<div style="color: #4caf50; padding: 10px;">✅ Removed ${result.deleted} file(s)</div>`;
                        setTimeout(() => statusElement.innerHTML = '', 3000);
                    }

                    // Clear selections
                    clearSelectedFiles();

                    // Reload page to refresh UI
                    console.log('🔄 [REMOVE] Reloading page to refresh UI');
                    window.location.reload();

                } catch (error) {
                    console.error('❌ [REMOVE] Error deleting files:', error);

                    // Show error message
                    const statusElement = document.querySelector('.remove-status');
                    if (statusElement) {
                        statusElement.innerHTML = `<div style="color: #f44336; padding: 10px;">❌ Error: ${error.message}</div>`;
                        setTimeout(() => statusElement.innerHTML = '', 5000);
                    }
                }
            }

            // Wire up Remove Selected button to JavaScript handler
            function setupRemoveSelectedButton() {
                const removeButton = document.getElementById('remove-selected-docs');
                if (removeButton) {
                    // Remove any existing onclick handlers
                    removeButton.onclick = null;

                    // Add new handler
                    removeButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🗑️ [REMOVE] Button clicked via JavaScript');
                        handleRemoveSelectedFiles();
                    });

                    console.log('✅ [REMOVE] Button wired to JavaScript handler');
                } else {
                    console.error('❌ [REMOVE] Button not found');
                }
            }

            // Set up button after a short delay to ensure DOM is ready
            setTimeout(setupRemoveSelectedButton, 500);

            console.log('✅ [JS] File selection manager ready (Remove button uses direct API)');
            </script>""",
        ) as blocks:

            # Modern Header
            with gr.Row(elem_classes=["header-container"]):
                with gr.Column(scale=1, elem_classes=["header-logo"]):
                    gr.Image(
                        value=str(INTERNAL_LOGO),
                        label=None,
                        show_label=False,
                        container=False,
                        height=188,  # Original size
                        width=563,  # Original size
                        elem_classes=["internal-logo-img"],
                    )
                with gr.Column(scale=2):
                    # Load JavaScript modules via JSManager
                    gr.HTML(self._js_manager.get_script_tags())
                    # JavaScript is now loaded via JSManager above - all functionality moved to JavaScript modules

                    # (script block removed - functionality moved to JavaScript modules)

                    gr.HTML(
                        """
                        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; gap: 4px; margin: 0; padding: 0;'>
                            <h1 class='header-title' style='margin: 0; padding: 0;'>Risk & Compliance</h1>
                            <p class='header-subtitle' style='margin: 0; padding: 0;'>Private AI Assistant</p>
                        </div>
                    """
                    )
                with gr.Column(scale=1):
                    # Model Information and Document Count Display
                    model_status = self._doc_state_manager.get_model_status()

                    model_status_display = gr.HTML(
                        f"""
                        <div style='display: flex; flex-direction: column; gap: 12px;'>
                            <div>{model_status}</div>
                        </div>
                    """
                    )

            # Main Content Area - Sidebar and Chat
            with gr.Row(equal_height=True):
                # Left Sidebar - Document-Focused Design
                with gr.Column(scale=2, elem_classes=["sidebar-container"]):

                    # Configuration section - Admin removed, user content always visible

                    # User Configurations Content (existing functionality)
                    with gr.Group(visible=True) as user_content:

                        # Document Library Actions Section with Search and Filters
                        with gr.Accordion("📚 Document Library Actions", open=True):
                            # Interactive Search Box
                            doc_search_input = gr.Textbox(
                                placeholder="🔍 Search documents...",
                                label="",
                                show_label=False,
                                elem_classes=["doc-search-input"],
                                container=False,
                            )

                            # Smart Grouping: Two rows of filters
                            # Get document counts for button badges
                            doc_counts = self._get_document_counts()

                            gr.HTML(
                                "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>📚 QUICK ACTIONS</div>"
                            )
                            with gr.Row():
                                filter_all_btn = gr.Button(
                                    f"All ({doc_counts['all']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_recent_btn = gr.Button(
                                    f"Recent ({doc_counts['recent']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_updated_btn = gr.Button(
                                    f"Updated ({doc_counts['updated']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_analyzed_btn = gr.Button(
                                    f"Used in Chat ({doc_counts['analyzed']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )

                            gr.HTML(
                                "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 12px;'>📁 FILE TYPES</div>"
                            )
                            with gr.Row():
                                filter_pdf_btn = gr.Button(
                                    f"PDF ({doc_counts['pdf']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_excel_btn = gr.Button(
                                    f"Excel ({doc_counts['excel']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_word_btn = gr.Button(
                                    f"Word ({doc_counts['word']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )
                                filter_other_btn = gr.Button(
                                    f"Other ({doc_counts['other']})",
                                    elem_classes=["filter-btn"],
                                    size="sm",
                                    scale=1,
                                )

                            # Status message display
                            filter_status_msg = gr.HTML(
                                value="", elem_classes=["filter-status"]
                            )

                            # State-backed components for filters (synchronized with centralized state)
                            current_filter_type = gr.Textbox(
                                value=self._state_integration.get_state_value(
                                    "documents.filter.type", "all"
                                ),
                                visible=False,
                            )
                            current_search_query = gr.Textbox(
                                value=self._state_integration.get_state_value(
                                    "documents.filter.search_query", ""
                                ),
                                visible=False,
                            )

                        # Document Library Display Component
                        document_library_content = gr.HTML(
                            value=self._get_document_library_html(),
                            elem_classes=["document-library-display"],
                        )

                        # Recent Documents section removed - functionality moved to Recent filter button
                        # Quick Actions section removed completely

                        # AI Configuration Section (Simplified Two-Mode Selector)
                        with gr.Accordion("🤖 AI Mode Selection", open=True):
                            # Two-Mode Selection with Clear Descriptions
                            with gr.Group():
                                gr.HTML(
                                    """
                                <div style='color: #0077BE; font-weight: 600; margin-bottom: 12px; font-size: 16px;'>
                                    Select AI Assistant Mode
                                </div>
                                """
                                )

                                # Set General LLM as default for faster responses
                                default_mode = (
                                    Modes.GENERAL_ASSISTANT.value
                                )  # General LLM as default

                                # Add CSS for tooltips

                                # JavaScript functionality moved to mode_selector.js module

                                # Visual indicator for active mode
                                mode_indicator = gr.HTML(
                                    value=f"<div style='text-align: center; padding: 8px; background: #e3f2fd; border-radius: 4px; margin-top: 8px;'><strong>🎯 Active Mode:</strong> {default_mode}</div>",
                                    elem_id="mode-indicator",
                                )

                        # Hidden AI controls that will be moved to the AI Configuration section
                        with gr.Group(visible=False) as ai_controls:

                            # Advanced Settings - Comprehensive AI Controls
                            with gr.Accordion("🎯 Context & Quality", open=False):
                                similarity_threshold = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.7,
                                    step=0.1,
                                    label="Similarity Threshold",
                                    info="Higher values = more relevant results",
                                    elem_classes=["modern-slider"],
                                )
                                response_temperature = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.1,
                                    step=0.1,
                                    label="Response Temperature",
                                    info="0 = Accurate, 1 = Creative",
                                    elem_classes=["modern-slider"],
                                )

                            # Response Behavior Controls
                            with gr.Accordion("📝 Response Behavior", open=False):
                                citation_style = gr.Radio(
                                    choices=[
                                        "Include Sources",
                                        "Exclude Sources",
                                        "Minimal Citations",
                                    ],
                                    value="Include Sources",
                                    label="Citation Style",
                                )
                                response_length = gr.Radio(
                                    choices=["Brief", "Medium", "Detailed"],
                                    value="Medium",
                                    label="Response Length",
                                )
                                # Removed confidence indicators - system now uses deterministic mode selection

                            # System Prompt Templates
                            with gr.Accordion("🤖 AI Behavior & Prompts", open=True):
                                system_prompt_templates = gr.Dropdown(
                                    choices=[
                                        "Default Assistant",
                                        "Financial Analyst",
                                        "Technical Expert",
                                        "Research Assistant",
                                        "Document Summarizer",
                                        "Compliance Reviewer",
                                        "Custom",
                                    ],
                                    value="Default Assistant",
                                    label="Prompt Template",
                                    info="Choose AI behavior for both Document and General Assistant modes",
                                )
                                system_prompt_input = gr.Textbox(
                                    placeholder=self._system_prompt,
                                    label="Custom System Prompt",
                                    lines=4,
                                    interactive=True,
                                    info="Override default behavior",
                                    render=False,
                                )
                                system_prompt_input.render()

                                # Connect mode changes to system prompt
                                # mode.change(
                                #    self._set_current_mode,
                                #    inputs=mode,
                                #    outputs=[system_prompt_input],
                                # )

                            # Reset Controls
                            reset_settings_btn = gr.Button(
                                "🔄 Reset to Defaults",
                                size="sm",
                                elem_classes=["modern-button", "secondary-button"],
                            )

                        # Mode-Specific Features and Controls
                        with gr.Group() as mode_specific_controls:

                            # General Assistant Mode Controls
                            with gr.Group(visible=False) as general_controls:
                                with gr.Accordion(
                                    "⚡ General Assistant Tools", open=True
                                ):
                                    gr.HTML(
                                        """
                                    <div style='background: linear-gradient(135deg, #e8f5e8 0%, #f0f9ff 100%); padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #4CAF50;'>
                                        <div style='font-weight: 600; color: #4CAF50; margin-bottom: 8px;'>🚀 Quick Tools</div>
                                        <div style='font-size: 13px; color: #555;'>Optimized for instant answers and calculations</div>
                                    </div>
                                    """
                                    )

                                    # Quick calculation helper
                                    with gr.Row():
                                        calc_input = gr.Textbox(
                                            placeholder="e.g., 15% of $250,000 or 1024 * 8",
                                            label="🧮 Quick Calculator",
                                            lines=1,
                                            scale=3,
                                        )
                                        calc_btn = gr.Button(
                                            "Calculate",
                                            scale=1,
                                            elem_classes=["modern-button"],
                                        )

                                    # Definition lookup shortcuts
                                    with gr.Row():
                                        definition_shortcuts = gr.Radio(
                                            choices=[
                                                "🔒 Security Terms",
                                                "💰 Financial Terms",
                                                "⚖️ Compliance Terms",
                                                "🏗️ Tech Architecture",
                                            ],
                                            label="Definition Shortcuts",
                                            interactive=True,
                                        )

                                    # Quick response indicators
                                    general_status = gr.HTML(
                                        value="<div style='text-align: center; padding: 8px; background: #e8f5e8; border-radius: 4px; color: #4CAF50;'><strong>⚡ Ready for instant responses</strong></div>"
                                    )

                            # Document Assistant Mode Controls
                            with gr.Group(
                                visible=True
                            ) as document_controls:  # Default visible since Document Assistant is default
                                with gr.Accordion(
                                    "📚 Document Assistant Tools", open=True
                                ):

                                    # Document search status
                                    document_status = gr.HTML(
                                        value="<div style='text-align: center; padding: 8px; background: #e3f2fd; border-radius: 4px; color: #0077BE;'><strong>📊 Document search active</strong></div>"
                                    )

                            # Mode switching confirmation dialog (initially hidden)
                            with gr.Group(visible=False) as mode_confirm_dialog:
                                gr.HTML(
                                    """
                                <div style='background: #fff3cd; border: 1px solid #ffeaa7; padding: 16px; border-radius: 8px; margin: 12px 0;'>
                                    <div style='font-weight: 600; color: #856404; margin-bottom: 8px;'>⚠️ Mode Switch Confirmation</div>
                                    <div style='color: #856404; margin-bottom: 12px;'>You have active document analysis. Switching modes may change how your queries are processed.</div>
                                    <div style='display: flex; gap: 8px;'>
                                        <button id='confirm-mode-switch' style='background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;'>Continue Switch</button>
                                        <button id='cancel-mode-switch' style='background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;'>Cancel</button>
                                    </div>
                                </div>
                                """
                                )

                            # Enhanced AI Configuration Controls
                            with gr.Group(visible=True) as enhanced_ai_controls:
                                # Model Selection
                                model_selection = gr.Radio(
                                    choices=[
                                        "Foundation-Sec-8B (Local)",
                                        "GPT-3.5 Turbo (OpenAI)",
                                        "GPT-4 (OpenAI)",
                                        "Llama 2 (Ollama)",
                                        "Claude 3 Sonnet",
                                        "Claude 3 Haiku",
                                    ],
                                    value="Foundation-Sec-8B (Local)",
                                    label="AI Model",
                                    info="Select the AI model to use for responses",
                                    elem_classes=["model-selector"],
                                )

                                # Writing Style Selection
                                writing_style = gr.Radio(
                                    choices=[
                                        "Balanced",
                                        "Concise",
                                        "Explanatory",
                                        "Creative",
                                        "Professional",
                                        "Casual",
                                        "Technical",
                                    ],
                                    value="Balanced",
                                    label="Writing Style",
                                    info="Adjust how the AI communicates",
                                    elem_classes=["writing-style-selector"],
                                )

                                # Temperature Control (Enhanced)
                                temperature_control = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.1,
                                    step=0.05,
                                    label="Creativity Level",
                                    info="Lower = More focused, Higher = More creative",
                                    elem_classes=["temperature-control"],
                                )

                # Right Side - Chat and Document Management
                with gr.Column(scale=8, elem_classes=["main-content-column"]):
                    # Chat Area - Using Extracted Component
                    chat_components, chat_layout = create_chat_interface(default_mode)
                    chat_refs = get_chat_component_refs(chat_components)

                    # Extract component references for event handling
                    mode = chat_refs["mode_selector"]
                    chat_input = chat_refs["chat_input"]
                    send_btn = chat_refs["send_btn"]
                    retry_btn = chat_refs["retry_btn"]
                    undo_btn = chat_refs["undo_btn"]
                    clear_btn = chat_refs["clear_btn"]
                    chatbot = chat_refs["chatbot"]

                    # Document Upload Area - Using Extracted Component
                    document_components, document_layout = (
                        create_document_upload_interface(self._format_file_list)
                    )
                    document_refs = get_document_component_refs(document_components)

                    # Extract component references for event handling
                    upload_button = document_refs["upload_button"]
                    folder_upload_button = document_refs["folder_upload_button"]
                    remove_selected_button = document_refs["remove_selected_button"]
                    clear_all_button = document_refs["clear_all_button"]
                    upload_status_msg = document_refs["upload_status_msg"]
                    clear_status_msg = document_refs["clear_status_msg"]
                    remove_status_msg = document_refs["remove_status_msg"]
                    selected_files_state = document_refs["selected_files_state"]
                    selected_files_bridge = document_refs["selected_files_bridge"]
                    ingested_dataset = document_refs["ingested_dataset"]

                    # External Information & CVE Tracking - Using Extracted Component
                    external_components, external_layout = (
                        create_external_info_interface(
                            self._format_feeds_display, self._format_cve_display
                        )
                    )
                    external_refs = get_external_info_component_refs(
                        external_components
                    )

                    # Extract component references for event handling - Source Category Filtering
                    all_sources_btn = external_refs["all_sources_btn"]
                    banking_btn = external_refs["banking_btn"]
                    cybersec_btn = external_refs["cybersec_btn"]
                    aml_btn = external_refs["aml_btn"]
                    securities_btn = external_refs["securities_btn"]
                    consumer_btn = external_refs["consumer_btn"]
                    ai_security_btn = external_refs["ai_security_btn"]
                    international_btn = external_refs["international_btn"]
                    current_feed_category = external_refs["current_feed_category"]
                    current_days_filter = external_refs["current_days_filter"]
                    feed_status = external_refs["feed_status"]
                    feed_display = external_refs["feed_display"]
                    cve_time_range_display = external_refs["cve_time_range_display"]
                    cve_time_24h_btn = external_refs["cve_time_24h_btn"]
                    cve_time_7d_btn = external_refs["cve_time_7d_btn"]
                    cve_time_30d_btn = external_refs["cve_time_30d_btn"]
                    cve_time_90d_btn = external_refs["cve_time_90d_btn"]
                    cve_current_time_filter = external_refs["cve_current_time_filter"]
                    cve_status = external_refs["cve_status"]
                    cve_display = external_refs["cve_display"]

                    # Collect ALL components for state management binding
                    all_state_components = {
                        # Chat Components
                        "chat_input": chat_input,
                        "chatbot": chatbot,
                        "mode_selector": mode,
                        # Document Management Components
                        "upload_button": upload_button,
                        "folder_upload_button": folder_upload_button,
                        "upload_status_msg": upload_status_msg,
                        "clear_status_msg": clear_status_msg,
                        "doc_search_input": doc_search_input,
                        "current_filter_type": current_filter_type,
                        "current_search_query": current_search_query,
                        # Document Filter Buttons
                        "filter_all_btn": filter_all_btn,
                        "filter_recent_btn": filter_recent_btn,
                        "filter_updated_btn": filter_updated_btn,
                        "filter_analyzed_btn": filter_analyzed_btn,
                        "filter_pdf_btn": filter_pdf_btn,
                        "filter_excel_btn": filter_excel_btn,
                        "filter_word_btn": filter_word_btn,
                        "filter_other_btn": filter_other_btn,
                        # Settings Components
                        "similarity_threshold": similarity_threshold,
                        "response_temperature": response_temperature,
                        "citation_style": citation_style,
                        "response_length": response_length,
                        "system_prompt_templates": system_prompt_templates,
                        "system_prompt_input": system_prompt_input,
                        # Advanced Settings Components
                        "calc_input": calc_input,
                        "definition_shortcuts": definition_shortcuts,
                        "model_selection": model_selection,
                        "writing_style": writing_style,
                        "temperature_control": temperature_control,
                        # External Info Components
                        "current_feed_category": current_feed_category,
                        "current_days_filter": current_days_filter,
                    }

                    # Register all state-managed components
                    logger.info("🔗 Registering component state bindings...")
                    self._register_component_state_bindings(all_state_components)
                    logger.info("✅ Component state bindings registered")

                    # Register all components with MessageBus for cross-component communication
                    logger.info("📬 Registering components with MessageBus...")
                    self._register_components_with_message_bus(all_state_components)
                    logger.info("✅ MessageBus registration completed")

                    # Industry News and Updates Section
                    logger.info("📰 Building Industry News and Updates section...")
                    with gr.Group(elem_classes=["ai-security-feed-section"]):
                        gr.HTML(
                            "<div class='file-section-title'>📰 Industry News and Updates</div>"
                        )

                        # Filter Controls Row
                        with gr.Row():
                            # Time Filter Buttons
                            ai_feed_time_24h_btn = gr.Button(
                                "24h",
                                size="sm",
                                elem_classes=["filter-btn"],
                                scale=1,
                            )
                            ai_feed_time_7d_btn = gr.Button(
                                "7d",
                                size="sm",
                                elem_classes=["filter-btn"],
                                scale=1,
                            )
                            ai_feed_time_30d_btn = gr.Button(
                                "30d",
                                size="sm",
                                elem_classes=["filter-btn"],
                                scale=1,
                            )
                            ai_feed_time_90d_btn = gr.Button(
                                "90d",
                                size="sm",
                                elem_classes=["filter-btn"],
                                scale=1,
                            )

                            # Category Filter Dropdown
                            ai_feed_category_dropdown = gr.Dropdown(
                                choices=[
                                    "All",
                                    "AI Research",
                                    "AI Security",
                                    "Cybersecurity News",
                                    "Government Alerts",
                                    "Regulatory",
                                ],
                                value="All",
                                label=None,
                                elem_classes=["filter-dropdown"],
                                scale=2,
                            )

                        # Time Range Display (shows current filter)
                        ai_feed_time_range_display = gr.HTML(
                            "<div class='time-range-display'>📅 Last 7 days</div>",
                            elem_classes=["time-display"],
                        )

                        # Hidden state to track current time filter
                        ai_feed_current_time_filter = gr.State(value="7d")

                        # Status Display
                        ai_feed_status = gr.HTML(
                            "<div class='feed-status'>Loading AI & Security feeds...</div>",
                            elem_classes=["feed-status-display"],
                        )

                        # Feed Display - Initial empty state
                        try:
                            initial_ai_feed_html = self._format_ai_security_feeds(
                                "7d", "All"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to load initial AI feeds: {e}")
                            initial_ai_feed_html = """
                            <div class='feed-content'>
                                <div style='text-align: center; color: #666; padding: 20px;'>
                                    <div>🤖 AI & Security feeds loading...</div>
                                    <div style='font-size: 12px; margin-top: 8px;'>
                                        Click REFRESH to load latest feeds
                                    </div>
                                </div>
                            </div>"""

                        ai_feed_display = gr.HTML(
                            value=initial_ai_feed_html,
                            elem_classes=["file-list-container"],
                        )

                        # Add resize handle for AI feed panel
                        gr.HTML(
                            '<div class="feed-resize-handle" id="ai-feed-resize-handle"></div>'
                        )

            # Mode change handler for explanation update - now handled by SettingsEventHandler
            # Advanced Settings Event Handlers - now handled by SettingsEventHandler
            # Reset to defaults - now handled by SettingsEventHandler

            system_prompt_templates.change(
                self._settings_event_builder.create_system_prompt_template_handler(),
                inputs=[system_prompt_templates],
                outputs=[system_prompt_input],
            )

            reset_settings_btn.click(
                self._settings_event_builder.create_reset_settings_handler(),
                outputs=[
                    similarity_threshold,
                    response_temperature,
                    citation_style,
                    response_length,
                    system_prompt_templates,
                    system_prompt_input,
                ],
            )

            # System prompt handler
            system_prompt_input.blur(
                self._set_system_prompt,
                inputs=system_prompt_input,
            )

            # Mode-Specific Event Handlers

            # General Assistant Calculator - now handled by SettingsEventHandler

            calc_btn.click(
                self._settings_event_builder.create_calculation_handler(),
                inputs=[calc_input],
                outputs=[general_status],
            )

            # Definition shortcuts handler - now handled by SettingsEventHandler

            definition_shortcuts.change(
                self._settings_event_builder.create_definition_shortcut_handler(),
                inputs=[definition_shortcuts],
                outputs=[chat_input],
            )

            # File Upload Event Handlers - now handled by DocumentEventHandlerBuilder

            # File upload handler
            upload_button.upload(
                self._doc_event_builder.upload_and_refresh,
                inputs=upload_button,
                outputs=[
                    ingested_dataset,
                    upload_status_msg,
                    document_library_content,
                    model_status_display,  # CRITICAL FIX: Update header count after upload
                ],
            )

            # Folder upload handler - now uses Gradio UploadButton with enhanced error handling
            def handle_folder_upload(files):
                logger.info(
                    "🔄 [PYTHON] handle_folder_upload called with Gradio UploadButton"
                )
                logger.info(f"🔄 [PYTHON] files received: {files}")

                try:
                    if files and len(files) > 0:
                        logger.info(
                            f"🔄 [PYTHON] Processing {len(files)} files from folder upload"
                        )

                        # Use the enhanced upload file method for multiple files
                        updated_file_list, status_msg, updated_document_library = (
                            self._upload_file(files)
                        )

                        # Prefix folder upload status message
                        if "✅" in status_msg:
                            folder_status_msg = f"📁 Folder Upload: {status_msg}"
                        else:
                            folder_status_msg = f"📁 Folder Upload Failed: {status_msg}"

                        # Get updated model status
                        updated_model_status = (
                            self._doc_state_manager.get_model_status()
                        )

                        return (
                            updated_file_list,
                            folder_status_msg,
                            updated_document_library,
                            updated_model_status,
                        )
                    else:
                        return (
                            self._doc_utility_builder.format_file_list(),
                            "📁 ℹ️ No files received from folder upload",
                            self._doc_library_builder.get_document_library_html(),
                            self._doc_state_manager.get_model_status(),
                        )

                except Exception as e:
                    logger.error(
                        f"❌ [PYTHON] Error processing folder upload: {e}",
                        exc_info=True,
                    )
                    return (
                        self._doc_utility_builder.format_file_list(),
                        f"📁 ❌ Folder upload error: {e!s}",
                        self._doc_library_builder.get_document_library_html(),
                        self._doc_state_manager.get_model_status(),
                    )

            folder_upload_button.upload(
                fn=handle_folder_upload,
                inputs=[folder_upload_button],
                outputs=[
                    ingested_dataset,
                    upload_status_msg,
                    document_library_content,
                    model_status_display,
                ],
            )

            # JavaScript bridge for getting selected files
            def get_selected_files_js():
                """JavaScript function to retrieve selected files."""
                return """
                function() {
                    if (window.selectedFilesForRemoval && Array.isArray(window.selectedFilesForRemoval)) {
                        return window.selectedFilesForRemoval;
                    }
                    return [];
                }
                """

            # Create JavaScript component for selected files retrieval
            selected_files_js = gr.HTML(
                value=f"""
                <script>
                window.getSelectedFilesForPython = {get_selected_files_js()};
                </script>
                <div id="selected-files-bridge" style="display: none;"></div>
                """,
                visible=False,
            )

            # Diagnostic function for testing document management operations
            def test_document_operations():
                """Test all document management operations for debugging."""
                logger.info("🧪 [TEST] Starting document management operations test")

                try:
                    # Test 1: List current documents
                    current_docs = self._ingest_service.list_ingested()
                    logger.info(
                        f"🧪 [TEST] Current documents in system: {len(current_docs)}"
                    )

                    # Test 2: File list formatting
                    file_list_html = self._doc_utility_builder.format_file_list()
                    logger.info(
                        f"🧪 [TEST] File list HTML length: {len(file_list_html)}"
                    )

                    # Test 3: Document library formatting
                    library_html = self._doc_library_builder.get_document_library_html()
                    logger.info(f"🧪 [TEST] Library HTML length: {len(library_html)}")

                    # Test 4: Component references
                    test_components = {
                        "upload_button": upload_button,
                        "folder_upload_button": folder_upload_button,
                        "remove_selected_button": remove_selected_button,
                        "clear_all_button": clear_all_button,
                        "upload_status_msg": upload_status_msg,
                        "selected_files_bridge": selected_files_bridge,
                        "selected_files_state": selected_files_state,
                    }

                    for name, component in test_components.items():
                        logger.info(
                            f"🧪 [TEST] Component {name}: {type(component).__name__}"
                        )

                    # Test 5: JavaScript bridge verification
                    current_bridge_value = (
                        selected_files_bridge.value
                        if hasattr(selected_files_bridge, "value")
                        else "N/A"
                    )
                    logger.info(
                        f"🧪 [TEST] Current bridge value: {current_bridge_value}"
                    )

                    logger.info(
                        "✅ [TEST] Document management operations test completed successfully"
                    )
                    return "✅ Diagnostic test completed - check logs for details"

                except Exception as e:
                    logger.error(
                        f"❌ [TEST] Document management test failed: {e}", exc_info=True
                    )
                    return f"❌ Diagnostic test failed: {e!s}"

            # Add diagnostic button (hidden by default, can be shown for debugging)
            with gr.Row(visible=False) as diagnostic_row:
                diagnostic_btn = gr.Button(
                    "🧪 Test Document Operations", elem_classes=["modern-button"]
                )
                diagnostic_output = gr.HTML()

            diagnostic_btn.click(
                fn=test_document_operations, outputs=[diagnostic_output]
            )

            # Integration verification on startup
            logger.info(
                "🔧 [INTEGRATION] Starting document management integration verification..."
            )

            # Verify all critical components exist
            critical_components = {
                "upload_button": upload_button,
                "folder_upload_button": folder_upload_button,
                "remove_selected_button": remove_selected_button,
                "clear_all_button": clear_all_button,
                "upload_status_msg": upload_status_msg,
                "clear_status_msg": clear_status_msg,
                "remove_status_msg": remove_status_msg,
                "selected_files_bridge": selected_files_bridge,
                "selected_files_state": selected_files_state,
                "ingested_dataset": ingested_dataset,
                "document_library_content": document_library_content,
            }

            missing_components = []
            for name, component in critical_components.items():
                if component is None:
                    missing_components.append(name)
                else:
                    logger.info(
                        f"✅ [INTEGRATION] Component {name}: {type(component).__name__}"
                    )

            if missing_components:
                logger.error(
                    f"❌ [INTEGRATION] Missing critical components: {missing_components}"
                )
            else:
                logger.info("✅ [INTEGRATION] All critical components verified")

            # Verify event handlers are registered
            logger.info("🔧 [INTEGRATION] Verifying event handlers...")
            logger.info("✅ [INTEGRATION] Upload button handler: upload_and_refresh")
            logger.info("✅ [INTEGRATION] Folder upload handler: handle_folder_upload")
            logger.info(
                "✅ [INTEGRATION] Remove button handler: handle_remove_selected (JavaScript API)"
            )
            logger.info("✅ [INTEGRATION] Clear all handler: clear_all_documents")

            # Verify service dependencies
            logger.info("🔧 [INTEGRATION] Verifying service dependencies...")
            try:
                services_status = {
                    "ingest_service": self._ingest_service is not None,
                    "doc_event_builder": self._doc_event_builder is not None,
                    "doc_utility_builder": self._doc_utility_builder is not None,
                    "doc_library_builder": self._doc_library_builder is not None,
                }

                for service, status in services_status.items():
                    if status:
                        logger.info(f"✅ [INTEGRATION] Service {service}: Available")
                    else:
                        logger.error(f"❌ [INTEGRATION] Service {service}: Missing")

                logger.info(
                    "🎉 [INTEGRATION] Document management system integration verification completed!"
                )
                logger.info("🚀 [INTEGRATION] System ready for document operations")

            except Exception as e:
                logger.error(f"❌ [INTEGRATION] Integration verification failed: {e}")

            # Log enhanced debugging instructions for users
            logger.info("📝 [INTEGRATION] Debugging instructions:")
            logger.info(
                "📝 [INTEGRATION] 1. Open browser console to see JavaScript debug messages"
            )
            logger.info(
                "📝 [INTEGRATION] 2. Use window.testBridge(['file1.txt']) in console to test bridge"
            )
            logger.info(
                "📝 [INTEGRATION] 3. Add ?debug=true to URL for periodic bridge status checks"
            )
            logger.info(
                "📝 [INTEGRATION] 4. Check application logs for detailed Python debugging"
            )

            # Remove Selected button - JavaScript-based approach
            # NOTE: Gradio 4.15.0 doesn't support _js parameter or bridge updates from JavaScript
            # Solution: JavaScript directly calls /v1/ingest/delete_by_filenames API endpoint
            # Then reloads the page to refresh UI (see JavaScript below)

            # Clear all documents handler (confirmation handled in Python)
            # Primary deletion operation
            clear_all_button.click(
                self._doc_event_builder.clear_all_documents,
                outputs=[
                    ingested_dataset,
                    clear_status_msg,
                    document_library_content,
                    model_status_display,
                ],
                show_progress=True,
            ).then(
                # Force complete UI refresh after deletion
                lambda: ("", ""),  # Clear search query and filter type
                outputs=[doc_search_input, current_filter_type],
            ).then(
                # Force refresh all filter counts and document displays
                lambda: self._doc_event_builder.refresh_file_list(),
                outputs=[ingested_dataset],
            )

            # Auto-refresh file list periodically - now handled by DocumentEventHandlerBuilder
            # Document Library Search and Filter Event Handlers - now handled by DocumentEventHandlerBuilder

            # Search input event handler with state synchronization
            def handle_search_with_state_sync(query):
                # Update state first
                self._state_integration.set_state_value(
                    "documents.filter.search_query", query
                )
                # Then handle the search
                return self._doc_event_builder.handle_search(query)

            doc_search_input.change(
                handle_search_with_state_sync,
                inputs=[doc_search_input],
                outputs=[document_library_content],
            )

            # Helper function for filter operations with scrolling - now handled by DocumentEventHandlerBuilder

            # Admin toggle functionality removed - user content is always visible

            # Filter button event handlers with scrolling support
            filter_all_btn.click(
                self._doc_event_builder.create_filter_all_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_pdf_btn.click(
                self._doc_event_builder.create_filter_pdf_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_excel_btn.click(
                self._doc_event_builder.create_filter_excel_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_word_btn.click(
                self._doc_event_builder.create_filter_word_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_recent_btn.click(
                self._doc_event_builder.create_filter_recent_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_analyzed_btn.click(
                self._doc_event_builder.create_filter_analyzed_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_updated_btn.click(
                self._doc_event_builder.create_filter_updated_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            filter_other_btn.click(
                self._doc_event_builder.create_filter_other_handler(),
                inputs=[doc_search_input, current_filter_type],
                outputs=[
                    document_library_content,
                    filter_status_msg,
                    current_filter_type,
                    current_search_query,
                ],
            )

            # Quick Actions event handlers removed

            # Integrate sidebar with existing document management - now handled by DocumentEventHandlerBuilder
            # Update sidebar when main upload functionality is used

            # Note: HTML components don't need change handlers for auto-refresh
            # The file list will update when upload/folder events trigger

            # === Custom Chat Event Handlers ===
            # Wire up the new custom chat interface components

            # Send button handler
            send_btn.click(
                fn=self._chat_event_builder.create_chat_wrapper_handler(),
                inputs=[
                    chat_input,
                    chatbot,
                    mode,
                    system_prompt_input,
                    similarity_threshold,
                    response_temperature,
                    citation_style,
                    response_length,
                ],
                outputs=[chatbot, chat_input],
                show_progress=True,
            )

            # Enter key handler for chat input
            chat_input.submit(
                fn=self._chat_event_builder.create_chat_wrapper_handler(),
                inputs=[
                    chat_input,
                    chatbot,
                    mode,
                    system_prompt_input,
                    similarity_threshold,
                    response_temperature,
                    citation_style,
                    response_length,
                ],
                outputs=[chatbot, chat_input],
                show_progress=True,
            )

            # Connect mode change to indicator update - using PrivateGPT pattern
            def handle_mode_change_simple(new_mode):
                # Update centralized state only
                self._state_integration.set_state_value("chat.mode", new_mode)
                logger.info(f"Mode changed to: {new_mode}")

                # Return empty gr.update() - this is FAST and non-blocking like PrivateGPT
                # No complex operations, no component reads, no threading issues
                return None

            mode.change(
                fn=handle_mode_change_simple,
                inputs=[mode],
                outputs=None,  # PrivateGPT pattern: simple and fast
            )

            # Clear chat button handler
            clear_btn.click(
                fn=self._chat_event_builder.create_clear_chat_handler(),
                inputs=[],
                outputs=[chatbot, chat_input],
            )

            # Retry button handler
            retry_btn.click(
                fn=self._chat_event_builder.create_retry_handler(),
                inputs=[chatbot],
                outputs=[chatbot, chat_input],
            )

            # Undo button handler (removes last exchange)
            undo_btn.click(
                fn=self._chat_event_builder.create_undo_handler(),
                inputs=[chatbot],
                outputs=[chatbot],
            )

            # RSS Feed Event Handlers - now handled by FeedsEventHandler

            # Feed filtering function - now handled by FeedsEventHandler

            # Wire up RSS feed handlers - category-based filtering with 30-day window

            # Category filter buttons filter feeds by source type

            all_sources_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "All Sources"
                ),
                outputs=[feed_display],
            )

            banking_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "Banking Regulation"
                ),
                outputs=[feed_display],
            )

            cybersec_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "Cybersecurity"
                ),
                outputs=[feed_display],
            )

            aml_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "AML/BSA"
                ),
                outputs=[feed_display],
            )

            securities_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "Securities"
                ),
                outputs=[feed_display],
            )

            consumer_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "Consumer Protection"
                ),
                outputs=[feed_display],
            )

            ai_security_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "AI Security"
                ),
                outputs=[feed_display],
            )

            international_btn.click(
                fn=self._feeds_event_builder.create_category_filter_handler(
                    "International"
                ),
                outputs=[feed_display],
            )

            # CVE Tracking Event Handlers - now handled by FeedsEventHandler

            # MITRE ATT&CK Event Handlers - now handled by FeedsEventHandler

            # Simple Forum Directory Event Handlers - now handled by FeedsEventHandler

            # Wire up CVE Tracking handlers - time filters auto-refresh

            # CVE Time filter buttons automatically refresh and filter CVE data
            cve_time_24h_btn.click(
                fn=self._feeds_event_builder.create_refresh_and_filter_cve_handler(
                    "24h"
                ),
                outputs=[
                    cve_status,
                    cve_time_range_display,
                    cve_current_time_filter,
                    cve_display,
                ],
            )

            cve_time_7d_btn.click(
                fn=self._feeds_event_builder.create_refresh_and_filter_cve_handler(
                    "7d"
                ),
                outputs=[
                    cve_status,
                    cve_time_range_display,
                    cve_current_time_filter,
                    cve_display,
                ],
            )

            cve_time_30d_btn.click(
                fn=self._feeds_event_builder.create_refresh_and_filter_cve_handler(
                    "30d"
                ),
                outputs=[
                    cve_status,
                    cve_time_range_display,
                    cve_current_time_filter,
                    cve_display,
                ],
            )

            cve_time_90d_btn.click(
                fn=self._feeds_event_builder.create_refresh_and_filter_cve_handler(
                    "90d"
                ),
                outputs=[
                    cve_status,
                    cve_time_range_display,
                    cve_current_time_filter,
                    cve_display,
                ],
            )

            # Wire up AI & Security Feed handlers
            def create_ai_feed_handler(time_filter: str):
                """Create handler for AI feed time filter buttons."""

                async def handler(category_filter):
                    # Refresh feeds
                    try:
                        await self._feeds_service.refresh_feeds()
                    except Exception as e:
                        logger.warning(f"Failed to refresh feeds: {e}")

                    # Update display
                    feeds_html = self._format_ai_security_feeds(
                        time_filter, category_filter
                    )
                    status_html = f"<div class='feed-status success'>✅ Showing AI & Security feeds from last {time_filter}</div>"
                    time_display_html = (
                        f"<div class='time-range-display'>📅 Last {time_filter}</div>"
                    )

                    return status_html, time_display_html, time_filter, feeds_html

                return handler

            # Time filter buttons
            ai_feed_time_24h_btn.click(
                fn=create_ai_feed_handler("24h"),
                inputs=[ai_feed_category_dropdown],
                outputs=[
                    ai_feed_status,
                    ai_feed_time_range_display,
                    ai_feed_current_time_filter,
                    ai_feed_display,
                ],
            )

            ai_feed_time_7d_btn.click(
                fn=create_ai_feed_handler("7d"),
                inputs=[ai_feed_category_dropdown],
                outputs=[
                    ai_feed_status,
                    ai_feed_time_range_display,
                    ai_feed_current_time_filter,
                    ai_feed_display,
                ],
            )

            ai_feed_time_30d_btn.click(
                fn=create_ai_feed_handler("30d"),
                inputs=[ai_feed_category_dropdown],
                outputs=[
                    ai_feed_status,
                    ai_feed_time_range_display,
                    ai_feed_current_time_filter,
                    ai_feed_display,
                ],
            )

            ai_feed_time_90d_btn.click(
                fn=create_ai_feed_handler("90d"),
                inputs=[ai_feed_category_dropdown],
                outputs=[
                    ai_feed_status,
                    ai_feed_time_range_display,
                    ai_feed_current_time_filter,
                    ai_feed_display,
                ],
            )

            # Category dropdown handler
            def ai_feed_category_handler(category_filter, current_time_filter):
                """Handle category filter changes."""
                feeds_html = self._format_ai_security_feeds(
                    current_time_filter, category_filter
                )
                status_html = f"<div class='feed-status success'>✅ Filtered by: {category_filter}</div>"
                return status_html, feeds_html

            ai_feed_category_dropdown.change(
                fn=ai_feed_category_handler,
                inputs=[ai_feed_category_dropdown, ai_feed_current_time_filter],
                outputs=[ai_feed_status, ai_feed_display],
            )

            # Auto-refresh all panels on UI startup (no cached data)
            blocks.load(
                fn=self._auto_refresh_all_panels_on_startup,
                outputs=[
                    feed_status,
                    feed_display,
                    cve_status,
                    cve_display,
                    ai_feed_status,
                    ai_feed_display,
                ],
            )

            # CRITICAL FIX: Refresh document count on page load
            # Without this, page refresh shows stale count from server startup
            def refresh_document_status_on_page_load():
                """Refresh document count and library when page loads.

                This ensures the header shows the current document count
                even after page refresh (F5), by querying the database
                instead of using the cached value from server startup.
                """
                logger.info("🔄 [PAGE_LOAD] Page loaded, refreshing document status...")
                updated_model_status = self._doc_state_manager.get_model_status()
                updated_file_list = self._doc_utility_builder.format_file_list()
                updated_document_library = (
                    self._doc_library_builder.get_document_library_html()
                )
                logger.info("✅ [PAGE_LOAD] Document status refreshed")

                return (
                    updated_model_status,
                    updated_file_list,
                    updated_document_library,
                )

            # Register page load event for document status refresh
            blocks.load(
                fn=refresh_document_status_on_page_load,
                outputs=[
                    model_status_display,
                    ingested_dataset,
                    document_library_content,
                ],
            )

        return blocks

    def get_ui_blocks(self) -> gr.Blocks:
        logger.info("🔍 get_ui_blocks called")
        if self._ui_block is None:
            logger.info("📝 Building UI blocks for the first time")
            self._ui_block = self._build_ui_blocks_protected()
            logger.info("✅ UI blocks built successfully")
        else:
            logger.info("♻️ Returning cached UI blocks")
        return self._ui_block

    def _build_ui_blocks_protected(self) -> gr.Blocks:
        """Protected UI building with global error boundary."""

        @self.global_error_boundary.wrap_function
        def _protected_ui_build():
            return self._build_ui_blocks()

        try:
            return _protected_ui_build()
        except Exception as e:
            logger.critical(f"Critical error during UI initialization: {e}")
            # Report critical error to error reporting system
            self._report_critical_error(e)
            # Create emergency fallback UI
            return self._create_emergency_fallback_ui()

    def mount_in_app(self, app: FastAPI, path: str) -> None:
        blocks = self.get_ui_blocks()

        logger.info("Mounting the modern gradio UI, at path=%s", path)
        gr.mount_gradio_app(app, blocks, path=path)

    def _create_emergency_fallback_ui(self) -> gr.Blocks:
        """Create emergency fallback UI when main UI fails to initialize."""
        logger.info("Creating emergency fallback UI")

        # Get error dashboard information
        error_dashboard = error_reporter.get_error_dashboard()

        with gr.Blocks(
            title="Internal Assistant - Emergency Mode",
            theme=gr.themes.Default(),
            css="""
                .emergency-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }
                .error-details {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: left;
                }
            """,
        ) as emergency_blocks:
            with gr.Column(elem_classes=["emergency-container"]):
                gr.HTML(
                    """
                    <div style='color: #dc3545; margin: 20px 0;'>
                        <h1>🚨 Internal Assistant - Emergency Mode</h1>
                        <h3>The application encountered a critical error during initialization</h3>
                    </div>
                """
                )

                gr.HTML(
                    f"""
                    <div class='error-details'>
                        <h4>🔧 What You Can Try:</h4>
                        <ul>
                            <li><strong>Refresh the page</strong> - Try reloading the application</li>
                            <li><strong>Check system resources</strong> - Ensure sufficient memory and disk space</li>
                            <li><strong>Restart the service</strong> - Stop and restart the Internal Assistant service</li>
                            <li><strong>Check logs</strong> - Review application logs for specific error details</li>
                            <li><strong>Contact support</strong> - If the issue persists, report it to the administrators</li>
                        </ul>

                        <h4>📊 System Status:</h4>
                        <ul>
                            <li><strong>Total Errors:</strong> {error_dashboard.get('total_errors', 0)}</li>
                            <li><strong>Recent Errors:</strong> {error_dashboard.get('recent_errors', 0)}</li>
                            <li><strong>Components in Fallback:</strong> {len(error_dashboard.get('components_in_fallback', []))}</li>
                        </ul>

                        <h4>⚠️ Emergency Mode Active</h4>
                        <p>The application is running in emergency mode with limited functionality.
                        This fallback interface ensures the system remains accessible while issues are resolved.</p>
                    </div>
                """
                )

                with gr.Row():
                    refresh_btn = gr.Button(
                        "🔄 Refresh Application", variant="primary", size="lg"
                    )
                    status_btn = gr.Button(
                        "📊 View Error Dashboard", variant="secondary", size="lg"
                    )

                status_output = gr.HTML()

                def refresh_application():
                    return "🔄 Please refresh your browser page to restart the application."

                def show_error_dashboard():
                    dashboard_html = self._format_error_dashboard_html(
                        error_reporter.get_error_dashboard()
                    )
                    return dashboard_html

                refresh_btn.click(refresh_application, outputs=status_output)
                status_btn.click(show_error_dashboard, outputs=status_output)

        return emergency_blocks

    def _format_error_dashboard_html(self, dashboard: dict[str, Any]) -> str:
        """Format error dashboard data as HTML."""
        html_parts = ["<div class='error-details'><h4>📊 Detailed Error Dashboard</h4>"]

        # Component summaries
        if "component_summaries" in dashboard:
            html_parts.append("<h5>Component Status:</h5><ul>")
            for component_name, summary in dashboard["component_summaries"].items():
                status = (
                    "🔴 Fallback"
                    if summary.get("is_in_fallback_mode", False)
                    else "🟢 Normal"
                )
                error_count = summary.get("total_errors", 0)
                html_parts.append(
                    f"<li><strong>{component_name}</strong>: {status} ({error_count} errors)</li>"
                )
            html_parts.append("</ul>")

        # Error categories
        if "error_by_category" in dashboard:
            html_parts.append("<h5>Error Categories:</h5><ul>")
            for category, count in dashboard["error_by_category"].items():
                if count > 0:
                    html_parts.append(
                        f"<li><strong>{category.title()}</strong>: {count} errors</li>"
                    )
            html_parts.append("</ul>")

        html_parts.append("</div>")
        return "".join(html_parts)

    def _report_critical_error(self, error: Exception) -> None:
        """Report critical application error to centralized error reporting system."""
        from internal_assistant.ui.core.error_boundaries import (
            ErrorCategory,
            ErrorInfo,
            ErrorSeverity,
        )

        # Create comprehensive error info
        error_info = ErrorInfo(
            timestamp=time.time(),
            component_name="internal_assistant_app",
            error_type=type(error).__name__,
            error_message=str(error),
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            traceback=str(error),
            user_message="Critical application error occurred during startup",
            recovery_suggestions=[
                "Refresh the browser page",
                "Restart the Internal Assistant service",
                "Check system resources and logs",
                "Contact system administrator if issue persists",
            ],
            context={
                "initialization_phase": "ui_building",
                "timestamp": datetime.now().isoformat(),
                "user_agent": "Internal Assistant UI",
            },
            is_recoverable=True,
        )

        # Report to centralized error system
        error_reporter.report_error(error_info)

        # Log critical error with details
        logger.critical(
            f"CRITICAL APPLICATION ERROR: {error_info.error_type} - {error_info.error_message}"
        )
        logger.critical(
            f"Recovery suggestions: {', '.join(error_info.recovery_suggestions)}"
        )


if __name__ == "__main__":
    ui = global_injector.get(InternalAssistantUI)
    _blocks = ui.get_ui_blocks()
    # Disable queue system to avoid Pydantic schema errors with FastAPI
    # The queue system causes compatibility issues with FastAPI's dependency injection
    logger.info("Queue system disabled to avoid Pydantic schema errors")
    _blocks.launch(debug=False, show_api=False)
