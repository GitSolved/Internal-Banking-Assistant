"""
Chat Component

Extracted from the monolithic ui.py file to handle chat interface functionality.
This component focuses solely on chat-related features.
"""

import logging
import time
from collections.abc import Iterable
from typing import Any, List

import gradio as gr
from injector import inject, singleton
from llama_index.core.llms import ChatResponse
from llama_index.core.types import TokenGen

from internal_assistant.server.chat.chat_service import ChatService, CompletionGen
from internal_assistant.ui.models.ui_models import Source
from internal_assistant.ui.constants import SOURCES_SEPARATOR
from internal_assistant.ui.components.chat.chat_interface import ChatInterfaceBuilder

logger = logging.getLogger(__name__)


@singleton
class ChatComponent:
    """Handles chat interface functionality"""

    @inject
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service
        self.interface_builder = ChatInterfaceBuilder()
        self._setup_handlers()

    def create_chat_interface(self) -> gr.Chatbot:
        """Creates the chat interface component"""
        logger.debug("Creating chat interface component")

        # Create the main chatbot interface
        chatbot = gr.Chatbot(
            label="Internal Assistant Chat",
            elem_id="chatbot",
            height=600,
            show_copy_button=True,
            show_share_button=False,
            avatar_images=None,
            sanitize_html=False,
            render_markdown=True,
            likeable=False,
            bubble_full_width=True,
        )

        logger.info("Chat interface component created successfully")
        return chatbot

    def create_complete_chat_interface(self, default_mode: str = None):
        """
        Creates the complete chat interface using the extracted ChatInterfaceBuilder.

        Args:
            default_mode: Default chat mode to set

        Returns:
            Tuple of (components dict, layout config dict)
        """
        logger.debug("Creating complete chat interface using ChatInterfaceBuilder")

        if default_mode:
            self.interface_builder = ChatInterfaceBuilder(default_mode)

        components, layout_config = self.interface_builder.build_chat_interface()

        logger.info(
            f"Complete chat interface created with {len(components)} components"
        )
        return components, layout_config

    def get_chat_component_refs(self, components: dict):
        """
        Get key component references for event binding.

        Args:
            components: Dictionary of all chat components

        Returns:
            Dictionary of key components for event handlers
        """
        return self.interface_builder.get_component_references(components)

    def _setup_handlers(self):
        """Sets up chat event handlers"""
        logger.debug("Setting up chat event handlers")

        # Initialize event handlers for chat functionality
        self._handlers = {
            "message_submit": self._handle_chat_message,
            "clear_chat": self._handle_clear_chat,
            "regenerate": self._handle_regenerate_response,
        }

        logger.debug("Chat event handlers configured")

    def _handle_clear_chat(self) -> List[List[str]]:
        """Handle clearing the chat history"""
        logger.info("Chat history cleared by user")
        return []

    def _handle_regenerate_response(self, history: List[List[str]]) -> List[List[str]]:
        """Handle regenerating the last response"""
        if history and len(history) > 0:
            logger.info("Regenerating last response")
            # Remove the last assistant response and regenerate
            last_message = history[-1][0] if history[-1][0] else ""
            if last_message:
                # This would trigger a new response generation
                return history[:-1]

        return history

    def _handle_chat_message(
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
    ) -> Any:
        """
        Handles individual chat messages

        Extracted from the _chat method in ui.py
        """
        # Validate input
        if not message or message.strip() == "" or message is None:
            yield "Please enter a valid message."
            return

        logger.info(f"Processing chat message in {mode} mode")

        try:
            # Normalize the mode
            from internal_assistant.ui.models.modes import normalize_mode

            normalized_mode = normalize_mode(mode)

            # Add user message to history
            history = history or []
            history.append([message, None])

            # Process the message based on mode
            if normalized_mode == "RAG Mode":
                # RAG mode with document context
                logger.debug("Processing in RAG mode with document context")
                response_generator = self.chat_service.chat_with_documents(
                    message=message,
                    system_prompt=system_prompt_input,
                    similarity_threshold=similarity_threshold,
                    temperature=response_temperature,
                    max_length=self._get_max_length(response_length),
                )
            else:
                # General LLM mode
                logger.debug("Processing in General LLM mode")
                response_generator = self.chat_service.chat_direct(
                    message=message,
                    system_prompt=system_prompt_input,
                    temperature=response_temperature,
                    max_length=self._get_max_length(response_length),
                )

            # Stream the response
            full_response = ""
            for delta in response_generator:
                if hasattr(delta, "choices") and delta.choices:
                    # Handle completion-style response
                    content = delta.choices[0].delta.content or ""
                    full_response += content
                    history[-1][1] = full_response
                    yield history
                else:
                    # Handle token-style response
                    full_response += str(delta)
                    history[-1][1] = full_response
                    yield history

            # Add sources if in RAG mode and citation style requires it
            if normalized_mode == "RAG Mode" and citation_style != "No Sources":
                sources = getattr(response_generator, "sources", [])
                if sources:
                    formatted_sources = self._format_sources(sources, citation_style)
                    history[-1][1] += "\n\n" + formatted_sources
                    yield history

            logger.info("Chat message processed successfully")

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            history[-1][1] = error_msg
            yield history

    def _get_max_length(self, response_length: str) -> int:
        """Convert response length setting to token count"""
        length_map = {"Short": 150, "Medium": 500, "Long": 1000, "Very Long": 2000}
        return length_map.get(response_length, 500)

    def _yield_deltas(
        self, completion_gen: CompletionGen, citation_style: str
    ) -> Iterable[str]:
        """Handles streaming response deltas"""
        logger.debug("Starting delta streaming")

        full_response = ""
        sources = []

        try:
            for completion in completion_gen:
                if hasattr(completion, "choices") and completion.choices:
                    choice = completion.choices[0]

                    # Extract content delta
                    if hasattr(choice, "delta") and choice.delta.content:
                        content = choice.delta.content
                        full_response += content
                        yield content

                    # Extract sources if available
                    if hasattr(completion, "sources"):
                        sources.extend(completion.sources)

            # Yield formatted sources at the end if needed
            if sources and citation_style != "No Sources":
                formatted_sources = self._format_sources(sources, citation_style)
                yield "\n\n" + formatted_sources

        except Exception as e:
            logger.error(f"Error in delta streaming: {e}")
            yield f"\n\n[Error in response streaming: {str(e)}]"

    def _yield_tokens(self, token_gen: TokenGen) -> Iterable[str]:
        """Handles token streaming"""
        logger.debug("Starting token streaming")

        try:
            for token in token_gen:
                if token is not None:
                    yield str(token)

        except Exception as e:
            logger.error(f"Error in token streaming: {e}")
            yield f"\n\n[Error in token streaming: {str(e)}]"

    def _format_sources(self, sources: List[Source], citation_style: str) -> str:
        """Formats document sources for display"""
        if not sources:
            return ""

        logger.debug(f"Formatting {len(sources)} sources with style: {citation_style}")

        if citation_style == "No Sources":
            return ""

        elif citation_style == "Inline Citations":
            # Format as inline citations
            citations = []
            for i, source in enumerate(sources[:5], 1):  # Limit to 5 sources
                doc_name = getattr(source, "document", "Unknown Document")
                page = getattr(source, "page", None)
                if page:
                    citations.append(f"[{i}. {doc_name}, p.{page}]")
                else:
                    citations.append(f"[{i}. {doc_name}]")
            return " ".join(citations)

        else:  # "Include Sources" (default)
            # Format as a sources section
            formatted = "\n\n**Sources:**\n"
            for i, source in enumerate(sources[:5], 1):  # Limit to 5 sources
                doc_name = getattr(source, "document", "Unknown Document")
                page = getattr(source, "page", None)
                content_preview = getattr(source, "content", "")[:100]

                if page:
                    formatted += f"{i}. **{doc_name}** (Page {page})\n"
                else:
                    formatted += f"{i}. **{doc_name}**\n"

                if content_preview:
                    formatted += f"   _{content_preview}..._\n\n"
                else:
                    formatted += "\n"

            return formatted.rstrip()
