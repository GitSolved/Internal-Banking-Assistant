"""
Chat Component Implementation

This module contains the actual implementation for the chat component,
extracted and refactored from the monolithic ui.py file.
"""

import logging
import time
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Tuple
import gradio as gr

from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.types import TokenGen

from internal_assistant.ui.core.ui_component import UIComponent
from internal_assistant.ui.models.modes import Modes, normalize_mode
from internal_assistant.ui.models.source import Source
from internal_assistant.server.chat.chat_service import CompletionGen

logger = logging.getLogger(__name__)

# Constants
SOURCES_SEPARATOR = "<hr>Sources: \n"


class ChatComponentImpl(UIComponent):
    """
    Actual implementation of the chat interface component.

    This component provides the real chat functionality extracted from ui.py,
    replacing the placeholder implementation.
    """

    def __init__(
        self, component_id: str = "chat", services: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the chat component with actual services.

        Args:
            component_id: Unique identifier for this component
            services: Dictionary of injected services
        """
        super().__init__(component_id, services)
        self.chat_service = None
        self.ingest_service = None
        self._system_prompt = ""

        # Get required services
        if self.has_service("chat"):
            self.chat_service = self.get_service("chat")
        if self.has_service("ingest"):
            self.ingest_service = self.get_service("ingest")

    def get_required_services(self) -> List[str]:
        """Specify required services for this component."""
        return ["chat", "ingest"]

    def build_interface(self) -> Dict[str, Any]:
        """
        Build the chat interface components with full functionality.

        Returns:
            Dictionary of Gradio components for the chat interface
        """
        # Create main chat interface
        with gr.Column():
            # Chat display
            chatbot = gr.Chatbot(
                label="Chat History",
                elem_id="chatbot",
                height=500,
                show_copy_button=True,
                likeable=True,
                bubble_full_width=False,
            )

            # Message input area
            with gr.Row():
                msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Type your message here... (Press Enter to send)",
                    lines=3,
                    max_lines=10,
                    elem_id="msg-input",
                    scale=4,
                )

            # Action buttons
            with gr.Row():
                submit_btn = gr.Button(
                    "Send", variant="primary", elem_id="submit-btn", scale=1
                )

                clear_btn = gr.Button(
                    "Clear Chat", variant="secondary", elem_id="clear-btn", scale=1
                )

                retry_btn = gr.Button(
                    "Retry Last", variant="secondary", elem_id="retry-btn", scale=1
                )

                stop_btn = gr.Button(
                    "Stop", variant="stop", elem_id="stop-btn", scale=1, visible=False
                )

            # Advanced settings (hidden by default)
            with gr.Accordion("Advanced Settings", open=False):
                with gr.Row():
                    mode_selector = gr.Radio(
                        label="Chat Mode",
                        choices=[mode.value for mode in Modes],
                        value=Modes.DOCUMENT_ASSISTANT.value,
                        elem_id="chat-mode",
                    )

                system_prompt = gr.Textbox(
                    label="System Prompt",
                    placeholder="Enter custom system prompt (optional)",
                    lines=3,
                    elem_id="system-prompt",
                )

                with gr.Row():
                    temperature = gr.Slider(
                        minimum=0,
                        maximum=1,
                        value=0.1,
                        step=0.1,
                        label="Temperature",
                        elem_id="temperature",
                    )

                    similarity_threshold = gr.Slider(
                        minimum=0.1,
                        maximum=1.0,
                        value=0.7,
                        step=0.1,
                        label="Similarity Threshold",
                        elem_id="similarity-threshold",
                    )

                with gr.Row():
                    citation_style = gr.Radio(
                        label="Citation Style",
                        choices=[
                            "Include Sources",
                            "Minimal Citations",
                            "Exclude Sources",
                        ],
                        value="Include Sources",
                        elem_id="citation-style",
                    )

                    response_length = gr.Radio(
                        label="Response Length",
                        choices=["Short", "Medium", "Long", "Very Long"],
                        value="Medium",
                        elem_id="response-length",
                    )

        # Store component references
        self._store_component_ref("chatbot", chatbot)
        self._store_component_ref("msg_input", msg_input)
        self._store_component_ref("submit_btn", submit_btn)
        self._store_component_ref("clear_btn", clear_btn)
        self._store_component_ref("retry_btn", retry_btn)
        self._store_component_ref("stop_btn", stop_btn)
        self._store_component_ref("mode_selector", mode_selector)
        self._store_component_ref("system_prompt", system_prompt)
        self._store_component_ref("temperature", temperature)
        self._store_component_ref("similarity_threshold", similarity_threshold)
        self._store_component_ref("citation_style", citation_style)
        self._store_component_ref("response_length", response_length)

        self._mark_built()

        return self._component_refs

    def register_events(self, demo: gr.Blocks) -> None:
        """
        Register event handlers for the chat component.

        Args:
            demo: The main gr.Blocks context
        """
        if not self.is_built():
            raise RuntimeError("Component must be built before registering events")

        # Get component references
        chatbot = self._component_refs["chatbot"]
        msg_input = self._component_refs["msg_input"]
        submit_btn = self._component_refs["submit_btn"]
        clear_btn = self._component_refs["clear_btn"]
        retry_btn = self._component_refs["retry_btn"]
        stop_btn = self._component_refs["stop_btn"]
        mode_selector = self._component_refs["mode_selector"]
        system_prompt = self._component_refs["system_prompt"]
        temperature = self._component_refs["temperature"]
        similarity_threshold = self._component_refs["similarity_threshold"]
        citation_style = self._component_refs["citation_style"]
        response_length = self._component_refs["response_length"]

        # Submit message handlers
        submit_event = submit_btn.click(
            fn=self._chat,
            inputs=[
                msg_input,
                chatbot,
                mode_selector,
                system_prompt,
                similarity_threshold,
                temperature,
                citation_style,
                response_length,
            ],
            outputs=[chatbot],
            show_progress=True,
        )

        enter_event = msg_input.submit(
            fn=self._chat,
            inputs=[
                msg_input,
                chatbot,
                mode_selector,
                system_prompt,
                similarity_threshold,
                temperature,
                citation_style,
                response_length,
            ],
            outputs=[chatbot],
            show_progress=True,
        )

        # Clear message input after submission
        submit_btn.click(fn=lambda: "", outputs=[msg_input])

        msg_input.submit(fn=lambda: "", outputs=[msg_input])

        # Clear chat history
        clear_btn.click(fn=self._clear_chat, outputs=[chatbot])

        # Retry last message
        retry_btn.click(
            fn=self._retry_last,
            inputs=[
                chatbot,
                mode_selector,
                system_prompt,
                similarity_threshold,
                temperature,
                citation_style,
                response_length,
            ],
            outputs=[chatbot],
        )

        # Stop generation (placeholder for now)
        stop_btn.click(fn=None, cancels=[submit_event, enter_event])

        # Mode change handler
        mode_selector.change(
            fn=self._on_mode_change, inputs=[mode_selector], outputs=[system_prompt]
        )

        logger.debug(f"Registered events for {self.component_id}")

    def get_component_refs(self) -> Dict[str, Any]:
        """Get references to this component's Gradio components."""
        return self._component_refs.copy()

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
    ) -> Any:
        """
        Handle chat message processing.

        This is the core chat functionality extracted from ui.py.
        """
        # Validate input
        if not message or message.strip() == "":
            yield history
            return

        # Add user message to history
        history = history or []
        history.append([message, None])

        # Build chat history
        all_messages = self._build_history(history)
        new_message = ChatMessage(content=message, role=MessageRole.USER)
        all_messages.append(new_message)

        # Add system prompt if provided
        system_prompt = system_prompt_input or self._system_prompt or ""
        if system_prompt:
            all_messages.insert(
                0, ChatMessage(content=system_prompt, role=MessageRole.SYSTEM)
            )

        # Normalize mode for backward compatibility
        normalized_mode = normalize_mode(mode)
        logger.info(f"Processing query in {normalized_mode} mode")

        # Process based on mode
        if normalized_mode == Modes.DOCUMENT_ASSISTANT.value:
            # Document Assistant mode - use context
            if not self._check_documents_available():
                response = (
                    "📄 **Document Assistant Mode - No Documents Available**\n\n"
                    "I'm in Document Assistant mode but couldn't find any uploaded documents. "
                    "Please upload documents or switch to General Assistant mode."
                )
                history[-1][1] = response
                yield history
                return

            # Stream chat with context
            if self.chat_service:
                try:
                    query_stream = self.chat_service.stream_chat(
                        messages=all_messages,
                        use_context=True,
                        context_filter=None,  # Simplified for now
                    )

                    full_response = ""
                    for delta in self._yield_deltas(query_stream, citation_style):
                        full_response = delta
                        history[-1][1] = full_response
                        yield history

                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    history[-1][1] = f"Error: {str(e)}"
                    yield history
            else:
                history[-1][1] = "Chat service not available"
                yield history

        else:
            # General Assistant mode - no context
            if self.chat_service:
                try:
                    query_stream = self.chat_service.stream_chat(
                        messages=all_messages, use_context=False, context_filter=None
                    )

                    full_response = ""
                    for delta in self._yield_deltas(query_stream, citation_style):
                        full_response = delta
                        history[-1][1] = full_response
                        yield history

                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    history[-1][1] = f"Error: {str(e)}"
                    yield history
            else:
                # Fallback if no service
                history[-1][1] = f"Echo (no service): {message}"
                yield history

    def _yield_deltas(
        self, completion_gen: CompletionGen, citation_style: str
    ) -> Iterable[str]:
        """
        Handle streaming response deltas.

        Extracted from ui.py _chat method.
        """
        full_response = ""
        stream = completion_gen.response

        for delta in stream:
            if isinstance(delta, str):
                full_response += str(delta)
            elif isinstance(delta, ChatResponse):
                full_response += delta.delta or ""
            yield full_response
            time.sleep(0.02)

        # Add sources if available and requested
        if completion_gen.sources and citation_style != "Exclude Sources":
            full_response += SOURCES_SEPARATOR
            sources_text = "\n\n**📄 Document Sources:**\n\n"
            used_files = set()

            for index, source in enumerate(completion_gen.sources, start=1):
                source_key = f"{source.file}-{source.page}"
                if source_key not in used_files:
                    if citation_style == "Minimal Citations":
                        sources_text += f"{index}. {source.file}\n"
                    else:  # Include Sources
                        sources_text += (
                            f"{index}. {source.file} (page {source.page})\n\n"
                        )
                    used_files.add(source_key)

            sources_text += "*Document sources from knowledge base*\n<hr>\n\n"
            full_response += sources_text

        yield full_response

    def _build_history(self, history: List[List[str]]) -> List[ChatMessage]:
        """
        Build chat message history.

        Extracted from ui.py _chat method.
        """
        history_messages = []

        for interaction in history[:-1]:  # Exclude current message
            if interaction[0]:
                history_messages.append(
                    ChatMessage(content=interaction[0], role=MessageRole.USER)
                )
            if len(interaction) > 1 and interaction[1]:
                # Remove sources from history
                content = interaction[1].split(SOURCES_SEPARATOR)[0]
                history_messages.append(
                    ChatMessage(content=content, role=MessageRole.ASSISTANT)
                )

        # Limit to 20 messages to avoid context overflow
        return history_messages[-20:]

    def _clear_chat(self) -> List:
        """Clear the chat history."""
        logger.debug("Chat history cleared")
        return []

    def _retry_last(
        self,
        history: List[List[str]],
        mode: str,
        system_prompt: str,
        similarity_threshold: float,
        temperature: float,
        citation_style: str,
        response_length: str,
    ) -> Any:
        """Retry the last message."""
        if not history:
            yield history
            return

        # Get last user message
        last_message = history[-1][0]

        # Remove last exchange
        history = history[:-1]

        # Resubmit the message
        yield from self._chat(
            last_message,
            history,
            mode,
            system_prompt,
            similarity_threshold,
            temperature,
            citation_style,
            response_length,
        )

    def _on_mode_change(self, mode: str) -> str:
        """Handle mode change and update system prompt."""
        normalized = normalize_mode(mode)

        if normalized == Modes.DOCUMENT_ASSISTANT.value:
            return "Use document context to answer questions."
        else:
            return "Answer questions directly and concisely."

    def _check_documents_available(self) -> bool:
        """Check if documents are available for RAG mode."""
        if self.ingest_service:
            try:
                # This would call the actual service method
                # For now, return True as placeholder
                return True
            except:
                return False
        return False
