"""Chat Interface Component

This module contains the extracted chat interface components from ui.py.
It handles the creation and layout of chat UI elements including the chatbot,
message input, action buttons, and mode selector.

Extracted from ui.py lines 7355-7418 during Phase 1A.1 refactoring.

Author: Internal Assistant Team
Version: 0.6.2
"""

import logging
from typing import Any

import gradio as gr

from internal_assistant.ui.models.modes import Modes

logger = logging.getLogger(__name__)

CHAT_HEADER = "🛡️ Internal Security Assistant"


class ChatInterfaceBuilder:
    """Builder class for chat interface components.

    This class handles the creation and layout of all chat-related UI elements
    including the chatbot display, message input, action buttons, and mode selector.
    Extracted from the monolithic ui.py to improve code organization.
    """

    def __init__(self, default_mode: str = Modes.DOCUMENT_ASSISTANT.value):
        """Initialize the chat interface builder.

        Args:
            default_mode: Default chat mode (RAG or General LLM)
        """
        self.default_mode = default_mode
        logger.debug("ChatInterfaceBuilder initialized")

    def build_chat_interface(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Build the complete chat interface.

        This method creates the full chat interface layout including:
        - Chat header with mode selector
        - Message input box and action buttons
        - Chatbot display area
        - API integration placeholder

        Returns:
            Tuple containing:
            - Dictionary of Gradio components mapped by name
            - Dictionary of layout configuration
        """
        logger.debug("Building chat interface components")

        components = {}
        layout_config = {}

        # Chat Area Container - Expanded
        with gr.Group(elem_classes=["chat-container"]):

            # Chat Header with Mode Selector
            with gr.Group(elem_classes=["enhanced-chat-header"]):
                with gr.Row():
                    # Chat Title (Left)
                    with gr.Column(scale=3):
                        chat_title = gr.HTML(
                            f"<h3 style='margin: 0; color: #0077BE; font-size: 20px;'>{CHAT_HEADER}</h3>"
                        )
                        components["chat_title"] = chat_title

                    # Mode Selector (Right)
                    with gr.Column(scale=2):
                        mode_selector = gr.Radio(
                            choices=[
                                ("🤖 General LLM", Modes.GENERAL_ASSISTANT.value),
                                ("📚 RAG Mode", Modes.DOCUMENT_ASSISTANT.value),
                            ],
                            value=self.default_mode,
                            label="",
                            elem_classes=["chat-mode-selector"],
                            interactive=True,
                        )
                        components["mode_selector"] = mode_selector

            # Message Input Section - Top Layout
            with gr.Group(elem_classes=["chat-input-top"]):

                # Message Input Box - At TOP
                with gr.Row():
                    chat_input = gr.Textbox(
                        placeholder="💡 Try: 'What CVEs affect our Exchange servers?' or 'Show me our incident response policy'",
                        label="",
                        show_label=False,
                        lines=3,
                        max_lines=5,
                        elem_classes=["chat-input-textbox"],
                        scale=5,
                    )
                    components["chat_input"] = chat_input

                # Action Buttons - With input at top
                with gr.Row():
                    send_btn = gr.Button(
                        "SEND MESSAGE",
                        elem_classes=["modern-button", "send-button"],
                        scale=1,
                    )
                    components["send_btn"] = send_btn

                    retry_btn = gr.Button(
                        "RETRY", elem_classes=["modern-button", "retry-button"], scale=1
                    )
                    components["retry_btn"] = retry_btn

                    undo_btn = gr.Button(
                        "UNDO", elem_classes=["modern-button", "undo-button"], scale=1
                    )
                    components["undo_btn"] = undo_btn

                    clear_btn = gr.Button(
                        "CLEAR CHAT",
                        elem_classes=["modern-button", "clear-button"],
                        scale=1,
                    )
                    components["clear_btn"] = clear_btn

            # Chat Messages Display Area - Middle
            with gr.Group(elem_classes=["chat-messages"]):
                chatbot = gr.Chatbot(
                    label="",
                    show_copy_button=True,
                    elem_id="chatbot",
                    height=None,  # Flexible height - no hardcoded value
                    elem_classes=["main-chatbot"],
                )
                components["chatbot"] = chatbot

            # API Integration Placeholder - Bottom
            with gr.Group(elem_classes=["chat-bottom-area"]):
                fake_api_btn = gr.Button(
                    "Use via API (Hidden for now)",
                    elem_classes=["fake-api-button"],
                    visible=False,  # Hidden but preserving space
                )
                components["fake_api_btn"] = fake_api_btn

                api_info_html = gr.HTML(
                    '<div style="text-align: center; color: #555; font-size: 12px; padding: 5px;">API Integration Area</div>'
                )
                components["api_info_html"] = api_info_html

        # Layout configuration
        layout_config = {
            "container_classes": ["chat-container"],
            "header_classes": ["enhanced-chat-header"],
            "input_classes": ["chat-input-top"],
            "messages_classes": ["chat-messages"],
            "bottom_classes": ["chat-bottom-area"],
            "chat_title": CHAT_HEADER,
            "default_mode": self.default_mode,
        }

        logger.info(f"Chat interface built with {len(components)} components")
        return components, layout_config

    def get_component_references(self, components: dict[str, Any]) -> dict[str, Any]:
        """Get references to key chat components for event binding.

        Args:
            components: Dictionary of all chat components

        Returns:
            Dictionary of key components for event handlers
        """
        key_components = {
            "chatbot": components.get("chatbot"),
            "chat_input": components.get("chat_input"),
            "send_btn": components.get("send_btn"),
            "retry_btn": components.get("retry_btn"),
            "undo_btn": components.get("undo_btn"),
            "clear_btn": components.get("clear_btn"),
            "mode_selector": components.get("mode_selector"),
        }

        logger.debug(f"Retrieved {len(key_components)} key component references")
        return key_components

    def get_layout_configuration(self) -> dict[str, Any]:
        """Get the layout configuration for the chat interface.

        Returns:
            Dictionary containing layout configuration
        """
        return {
            "header_text": CHAT_HEADER,
            "default_mode": self.default_mode,
            "input_placeholder": "💡 Try: 'What CVEs affect our Exchange servers?' or 'Show me our incident response policy'",
            "button_labels": {
                "send": "SEND MESSAGE",
                "retry": "RETRY",
                "undo": "UNDO",
                "clear": "CLEAR CHAT",
            },
            "css_classes": {
                "container": ["chat-container"],
                "header": ["enhanced-chat-header"],
                "input": ["chat-input-top"],
                "messages": ["chat-messages"],
                "bottom": ["chat-bottom-area"],
            },
        }


def create_chat_interface(
    default_mode: str = Modes.DOCUMENT_ASSISTANT.value,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Factory function to create a chat interface.

    Args:
        default_mode: Default chat mode

    Returns:
        Tuple of (components dict, layout config dict)
    """
    builder = ChatInterfaceBuilder(default_mode)
    return builder.build_chat_interface()


def get_chat_component_refs(components: dict[str, Any]) -> dict[str, Any]:
    """Factory function to get key component references for event binding.

    Args:
        components: Dictionary of all chat components

    Returns:
        Dictionary of key components for event handlers
    """
    builder = ChatInterfaceBuilder()
    return builder.get_component_references(components)
