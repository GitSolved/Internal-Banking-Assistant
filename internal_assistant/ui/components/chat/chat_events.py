"""
Chat Event Handlers

This module contains all event handlers for the chat interface components.
Extracted from ui.py as part of Phase 1 refactoring to decouple event handling
from UI construction.
"""

import logging
import re
import time
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Tuple, Union

import gradio as gr
from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.types import TokenGen

from internal_assistant.server.chat.chat_service import ChatService, CompletionGen
from internal_assistant.server.chunks.chunks_service import Chunk, ChunksService
from internal_assistant.ui.core.error_boundaries import (
    create_error_boundary,
    with_error_boundary,
)
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.recipes.summarize.summarize_service import (
    SummarizeService,
)
from internal_assistant.ui.core.event_router import EventHandler
from internal_assistant.ui.models.source import Source
from internal_assistant.open_ai.extensions.context_filter import ContextFilter

logger = logging.getLogger(__name__)


# Import the Modes enum - this should match the ui.py implementation
from enum import Enum


class Modes(str, Enum):
    DOCUMENT_ASSISTANT = "RAG Mode"
    GENERAL_ASSISTANT = "General LLM"


# Constants
SOURCES_SEPARATOR = "<hr>Sources: \n"


def normalize_mode(mode: str) -> str:
    """Normalize mode for backward compatibility."""
    legacy_mapping = {
        "Document Assistant": Modes.DOCUMENT_ASSISTANT.value,
        "General Assistant": Modes.GENERAL_ASSISTANT.value,
        "RAG": Modes.DOCUMENT_ASSISTANT.value,
        "DIRECT": Modes.GENERAL_ASSISTANT.value,
    }

    if mode in legacy_mapping:
        return legacy_mapping[mode]
    return mode


class ChatEventHandler:
    """
    Handles all chat-related events including message sending, clearing,
    retrying, and mode changes.
    """

    def __init__(
        self,
        chat_service: ChatService,
        chunks_service: ChunksService,
        ingest_service: IngestService,
        summarize_service: SummarizeService,
        list_ingested_files_func,
        create_context_filter_func,
        system_prompt_getter,
    ):
        """
        Initialize chat event handler with required services.

        Args:
            chat_service: Service for chat operations
            chunks_service: Service for document chunks
            ingest_service: Service for document ingestion
            summarize_service: Service for document summarization
            list_ingested_files_func: Function to list ingested files
            create_context_filter_func: Function to create context filter
            system_prompt_getter: Function to get system prompt
        """
        self.chat_service = chat_service
        self.chunks_service = chunks_service
        self.ingest_service = ingest_service
        self.summarize_service = summarize_service
        self.list_ingested_files = list_ingested_files_func
        self.create_context_filter = create_context_filter_func
        self.get_system_prompt = system_prompt_getter

        # Initialize error boundary for chat operations
        self.chat_error_boundary = create_error_boundary(
            "chat_interface", "chat", "Chat service temporarily unavailable"
        )

    def chat_wrapper(
        self,
        message: str,
        history: List[List[str]],
        mode: str,
        system_prompt_input: str,
        similarity_threshold: float,
        response_temperature: float,
        citation_style: str,
        response_length: str,
    ) -> Tuple[List[List[str]], str]:
        """
        Main chat processing function extracted from ui.py lines 5680-5812.

        This matches the exact signature and behavior of the original chat_wrapper.
        Protected by error boundary for graceful failure handling.

        Args:
            message: User input message
            history: Chat history as list of [user, assistant] pairs
            mode: Chat mode
            system_prompt_input: System prompt
            similarity_threshold: Similarity threshold for document search
            response_temperature: Temperature for LLM
            citation_style: Citation style preference
            response_length: Response length preference

        Returns:
            Tuple of (updated_history, empty_input)
        """
        return self._chat_wrapper_protected(
            message,
            history,
            mode,
            system_prompt_input,
            similarity_threshold,
            response_temperature,
            citation_style,
            response_length,
        )

    def _chat_wrapper_protected(
        self,
        message: str,
        history: List[List[str]],
        mode: str,
        system_prompt_input: str,
        similarity_threshold: float,
        response_temperature: float,
        citation_style: str,
        response_length: str,
    ) -> Tuple[List[List[str]], str]:
        """
        Protected version of chat wrapper with error boundary handling.
        """

        @self.chat_error_boundary.wrap_function
        def _protected_chat_logic():
            return self._execute_chat_logic(
                message,
                history,
                mode,
                system_prompt_input,
                similarity_threshold,
                response_temperature,
                citation_style,
                response_length,
            )

        try:
            return _protected_chat_logic()
        except Exception:
            # If error boundary triggers, return safe fallback
            error_message = (
                "⚠️ Chat service temporarily unavailable. Please try again in a moment."
            )
            if message.strip():
                # Add user message and error response to history
                updated_history = history + [[message, error_message]]
                return updated_history, ""
            return history, ""

    def _execute_chat_logic(
        self,
        message: str,
        history: List[List[str]],
        mode: str,
        system_prompt_input: str,
        similarity_threshold: float,
        response_temperature: float,
        citation_style: str,
        response_length: str,
    ) -> Tuple[List[List[str]], str]:
        """
        Core chat processing logic separated for error boundary protection.
        """
        # Add user message to history
        if message.strip():
            history = history + [[message, None]]

            # Get the streaming response
            try:
                # Log the query processing
                logger.info(f"Using {mode} mode")

                # Use the selected mode and prompt
                response_generator = self._chat(
                    message,
                    history[
                        :-1
                    ],  # Pass history without the current incomplete exchange
                    mode,  # Use user's selected mode directly - DETERMINISTIC
                    system_prompt_input,  # Use user's prompt directly
                    similarity_threshold,
                    response_temperature,
                    citation_style,
                    response_length,
                )

                # Collect streaming response properly (fix for repetitive output bug)
                full_response = ""
                chunk_count = 0
                max_chunks = 5000  # Significantly increased limit for very large files
                previous_length = 0
                last_tokens = []  # Track recent tokens to detect loops

                for chunk in response_generator:
                    chunk_count += 1
                    if chunk_count > max_chunks:
                        break

                    if chunk and isinstance(chunk, str):
                        # Handle cumulative streaming responses correctly
                        if len(chunk) > previous_length:
                            # Extract only NEW content (delta) from cumulative response
                            new_content = chunk[previous_length:]

                            # Apply repetition detection to new content only
                            words = new_content.split()
                            skip_chunk = False
                            for word in words:
                                if len(last_tokens) > 10:
                                    if last_tokens[-5:].count(word) >= 2:
                                        skip_chunk = True
                                        break
                                last_tokens.append(word)
                                if len(last_tokens) > 20:
                                    last_tokens.pop(0)

                            if skip_chunk:
                                continue

                            # Check for phrase repetition in new content
                            if (
                                len(new_content) > 5
                                and new_content in full_response[-200:]
                            ):
                                continue

                            full_response += new_content
                            previous_length = len(chunk)

                            # Significantly increased character limit for very large files
                            if len(full_response) > 32000:
                                break
                        elif len(chunk) <= previous_length:
                            # Chunk is same length or shorter, use it as final response
                            full_response = chunk
                            break

            except Exception as e:
                # Handle specific token-related errors with user-friendly messages
                error_str = str(e).lower()
                if any(
                    token_err in error_str
                    for token_err in [
                        "token",
                        "context length",
                        "max length",
                        "input too long",
                        "sequence length",
                    ]
                ):
                    if mode == Modes.DOCUMENT_ASSISTANT.value:
                        full_response = "⚠️ **Document Assistant - Large File Detected**\n\nYour file is very large. The system has been optimized for larger files, but you may need to:\n\n• **Ask specific questions**: Instead of 'explain everything', ask about specific sections\n• **Use document filters**: Filter to show only specific files\n• **Break it down**: Ask about specific sections separately\n• **Try General Assistant**: For general information without analyzing your specific file\n• **Split the file**: Consider breaking very large files into smaller sections"
                    else:
                        full_response = "⚠️ **General Assistant - Request Too Large**\n\nYour message is too long. Please try:\n\n• **Shorter message**: Use fewer words or break into smaller questions\n• **Simpler query**: Focus on one topic at a time\n• **Multiple questions**: Ask follow-up questions instead of one long message"
                elif "rate limit" in error_str or "quota" in error_str:
                    mode_name = (
                        "Document Assistant"
                        if mode == Modes.DOCUMENT_ASSISTANT.value
                        else "General Assistant"
                    )
                    full_response = f"⚠️ **{mode_name} - Rate Limit Reached**\n\nToo many requests have been made. Please:\n\n• **Wait a moment**: Try again in 30-60 seconds\n• **Slower pace**: Space out your questions more\n• **Check usage**: You may have reached your daily limit"
                elif "connection" in error_str or "timeout" in error_str:
                    mode_name = (
                        "Document Assistant"
                        if mode == Modes.DOCUMENT_ASSISTANT.value
                        else "General Assistant"
                    )
                    full_response = f"⚠️ **{mode_name} - Connection Issue**\n\nUnable to reach the AI service. Please:\n\n• **Check internet**: Verify your network connection\n• **Refresh page**: Reload and try again\n• **Try again**: Wait a moment and retry your request\n• **Contact support**: If the issue persists"
                else:
                    mode_name = (
                        "Document Assistant"
                        if mode == Modes.DOCUMENT_ASSISTANT.value
                        else "General Assistant"
                    )
                    full_response = f"⚠️ **{mode_name} - Unexpected Error**\n\nSomething went wrong while generating your response.\n\n**Error details**: {str(e)}\n\n**What you can try:**\n• **Rephrase**: Try asking your question differently\n• **Switch modes**: Try the other assistant mode\n• **Simpler query**: Break complex questions into parts\n• **Contact support**: If this keeps happening"

            # Basic cleanup of spacing and formatting
            if full_response:
                # Only keep essential cleanup - remove excessive spacing and punctuation
                full_response = re.sub(
                    r"([.!?])\1{2,}", r"\1", full_response
                )  # Remove excessive punctuation
                full_response = re.sub(
                    r"\s{3,}", " ", full_response
                )  # Clean up excessive spacing
                full_response = full_response.strip()

                # ADD SOURCE ATTRIBUTION: Show which mode was actually used
                # Determine the actual mode based on whether documents were found and used
                has_document_sources = SOURCES_SEPARATOR in full_response

                # If we tried to use documents but found no sources, it's effectively general knowledge
                actual_mode_used = mode
                if mode == Modes.DOCUMENT_ASSISTANT.value:
                    if not has_document_sources:
                        # No documents were actually used, so it's general knowledge
                        actual_mode_used = Modes.GENERAL_ASSISTANT.value

                mode_indicators = {
                    Modes.GENERAL_ASSISTANT.value: "[AI] *General knowledge*",
                    Modes.DOCUMENT_ASSISTANT.value: "[DOC] *From your documents*",
                }

                # Add mode indicator based on what was actually used
                if actual_mode_used in mode_indicators and not has_document_sources:
                    indicator = mode_indicators[actual_mode_used]
                    # Only add indicator for modes that don't already have sources shown
                    if actual_mode_used != Modes.DOCUMENT_ASSISTANT.value:
                        full_response += f"\n\n{indicator}"

            # Update the last message with the complete response
            # Provide mode-specific fallback message if no response generated
            if not full_response.strip():
                if mode == Modes.DOCUMENT_ASSISTANT.value:
                    fallback_msg = "📄 **Document Assistant - No Response Generated**\n\nI couldn't find relevant information in your documents or generate a response. Try:\n\n• **Rephrase question**: Use different keywords\n• **Check documents**: Ensure relevant files are uploaded\n• **General Assistant**: Switch modes for general knowledge questions\n• **Be specific**: Ask about particular documents or topics"
                else:
                    fallback_msg = "🤖 **General Assistant - No Response Generated**\n\nI couldn't generate a response to your question. Try:\n\n• **Rephrase question**: Use different words or simpler language\n• **Break it down**: Ask smaller, more specific questions\n• **Document Assistant**: Switch modes if you need information from uploaded files\n• **Try again**: Sometimes rephrasing helps me understand better"
            else:
                fallback_msg = full_response

            history[-1][1] = fallback_msg

        return history, ""  # Return updated history and clear the input

    def _chat(
        self,
        message: str,
        history: List[List[str]],
        mode: str,
        system_prompt_input: str,
        similarity_threshold: float = 0.7,
        response_temperature: float = 0.1,
        citation_style: str = "Include Sources",
        response_length: str = "Medium",
        *_: Any,
    ) -> Iterable[str]:
        """
        Internal chat method that matches the original ui.py implementation.
        This method is extracted from lines 238-356 of ui.py.
        """
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

        def build_history() -> List[ChatMessage]:
            history_messages: List[ChatMessage] = []

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
        system_prompt = self.get_system_prompt() or ""

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

        if normalized_mode == Modes.DOCUMENT_ASSISTANT.value:
            # Document Assistant mode - search documents for contextual answers
            try:
                available_files = self.list_ingested_files()
                if not available_files or len(available_files) == 0:
                    yield "📄 **Document Assistant Mode - No Documents Available**\n\nI'm in Document Assistant mode but couldn't find any uploaded documents to search. Here's what you can do:\n\n• **📁 Upload Files**: Use the Upload tab to add documents\n• **📂 Upload Folders**: Use the Folder tab to ingest directories\n• **🤖 Switch Mode**: Use General Assistant for questions that don't require documents\n\n**Supported formats**: PDF, Word, Excel, PowerPoint, Text, Markdown, and more\n\nOnce documents are uploaded, I'll search through them to provide contextual answers."
                    return
            except Exception as e:
                yield f"⚠️ **Document Assistant Mode - Error**\n\nI couldn't access your document library. This might be a temporary issue.\n\n**Try these solutions:**\n• Refresh the page and try again\n• Switch to General Assistant mode for non-document questions\n• Check if your documents are still uploading\n\nIf the problem persists, please contact support."
                return

            context_filter = self.create_context_filter()

            query_stream = self.chat_service.stream_chat(
                messages=all_messages,
                use_context=True,
                context_filter=context_filter,
            )
            yield from yield_deltas(query_stream)

        elif normalized_mode == Modes.GENERAL_ASSISTANT.value:
            # General Assistant mode - direct LLM without document search
            query_stream = self.chat_service.stream_chat(
                messages=all_messages,
                use_context=False,  # No document context
                context_filter=None,
            )
            yield from yield_deltas(query_stream)

    def _get_mode_indicator_html(self, mode: str) -> str:
        """
        Generate HTML indicator for the current chat mode.
        Extracted from ui.py on_mode_change function.
        """
        if mode == Modes.DOCUMENT_ASSISTANT.value:
            mode_display = "📚 Document Assistant"
            mode_description = "Searching your documents for answers"
            bg_color = "#e3f2fd"
        else:
            mode_display = "🤖 General Assistant"
            mode_description = "Using AI knowledge without documents"
            bg_color = "#f1f8e9"

        indicator_html = f"""
        <div style='text-align: center; padding: 8px; background: {bg_color}; border-radius: 4px; margin-top: 8px;'>
            <strong>🎯 Active Mode:</strong> {mode_display}<br>
            <small style='color: #666;'>{mode_description}</small>
        </div>
        """
        return indicator_html

    def clear_chat(self) -> Tuple[List, str]:
        """
        Clear the chat history.

        Returns:
            Tuple of (empty_history, empty_mode_indicator)
        """
        logger.info("Chat cleared by user")
        return [], ""

    def retry_last_message(
        self, history: List[List[str]]
    ) -> Tuple[List[List[str]], str]:
        """
        Retry the last message. Extracted from ui.py lines 5868-5875.

        Args:
            history: Current chat history

        Returns:
            Tuple of (updated_history, last_user_message)
        """
        if not history:
            return history, ""
        # Remove last bot response and return user message for retry
        if len(history) > 0:
            last_user_message = history[-1][0] if len(history[-1]) > 0 else ""
            return history[:-1], last_user_message
        return history, ""

    def undo_last_message(
        self, history: List[List[str]]
    ) -> Tuple[List[List[str]], str]:
        """
        Remove the last message pair from chat history.

        Args:
            history: Current chat history

        Returns:
            Tuple of (updated_history, empty_mode_indicator)
        """
        if history:
            history = history[:-1]
            logger.info("Last message undone by user")
        return history, ""

    def on_mode_change(self, selected_mode: str) -> str:
        """
        Handle mode changes. Extracted from ui.py lines 5831-5848.

        Args:
            selected_mode: The selected mode

        Returns:
            HTML indicator for the mode
        """
        return self._get_mode_indicator_html(selected_mode)


class ChatEventHandlerBuilder:
    """
    Builder class for creating chat event handlers with dependency injection.
    """

    def __init__(
        self,
        chat_service: ChatService,
        chunks_service: ChunksService,
        ingest_service: IngestService,
        summarize_service: SummarizeService,
        list_ingested_files_func,
        create_context_filter_func,
        system_prompt_getter,
    ):
        """
        Initialize the builder with required services.

        Args:
            chat_service: Service for chat operations
            chunks_service: Service for document chunks
            ingest_service: Service for document ingestion
            summarize_service: Service for document summarization
            list_ingested_files_func: Function to list ingested files
            create_context_filter_func: Function to create context filter
            system_prompt_getter: Function to get system prompt
        """
        self.chat_service = chat_service
        self.chunks_service = chunks_service
        self.ingest_service = ingest_service
        self.summarize_service = summarize_service
        self.list_ingested_files = list_ingested_files_func
        self.create_context_filter = create_context_filter_func
        self.system_prompt_getter = system_prompt_getter
        self._handler = None

    def get_handler(self) -> ChatEventHandler:
        """
        Get or create the chat event handler instance.

        Returns:
            ChatEventHandler instance
        """
        if self._handler is None:
            self._handler = ChatEventHandler(
                self.chat_service,
                self.chunks_service,
                self.ingest_service,
                self.summarize_service,
                self.list_ingested_files,
                self.create_context_filter,
                self.system_prompt_getter,
            )
        return self._handler

    def get_handler(self) -> ChatEventHandler:
        """
        Get or create the chat event handler instance.

        Returns:
            ChatEventHandler instance
        """
        if self._handler is None:
            self._handler = ChatEventHandler(
                self.chat_service,
                self.chunks_service,
                self.ingest_service,
                self.summarize_service,
                self.list_ingested_files,
                self.create_context_filter,
                self.system_prompt_getter,
            )
        return self._handler

    def create_chat_wrapper_handler(self):
        """Create handler for main chat submission."""
        return self.get_handler().chat_wrapper

    def create_clear_chat_handler(self):
        """Create handler for clearing chat."""
        return self.get_handler().clear_chat

    def create_retry_handler(self):
        """Create handler for retrying last message."""
        return self.get_handler().retry_last_message

    def create_undo_handler(self):
        """Create handler for undoing last message."""
        return self.get_handler().undo_last_message

    def create_mode_change_handler(self):
        """Create handler for mode changes."""
        return self.get_handler().on_mode_change
