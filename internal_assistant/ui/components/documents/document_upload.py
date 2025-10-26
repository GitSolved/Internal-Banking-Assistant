"""Document Upload Component

This module contains the extracted document upload interface from ui.py.
It handles file uploads, folder processing, document management, and status displays.

Extracted from ui.py lines 7371-7438 during Phase 1A.2 refactoring.

Author: Internal Assistant Team
Version: 0.6.2
"""

import logging
from collections.abc import Callable
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)


class DocumentUploadBuilder:
    """Builder class for document upload and management components.

    This class handles the creation and layout of all document-related UI elements
    including file uploads, folder processing, document library display, and status management.
    Extracted from the monolithic ui.py to improve code organization.
    """

    def __init__(self, format_file_list_fn: Callable[[], str] = None):
        """Initialize the document upload builder.

        Args:
            format_file_list_fn: Function to format the current file list for display
        """
        self.format_file_list_fn = format_file_list_fn or (lambda: "No documents")
        logger.debug("DocumentUploadBuilder initialized")

    def build_document_upload_interface(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Build the complete document upload and management interface.

        This method creates the full document management layout including:
        - File upload buttons and folder processing
        - Document library display and status
        - Clear/delete functionality
        - Status messages and progress indicators

        Returns:
            Tuple containing:
            - components: Dictionary of all Gradio components
            - layout_config: Configuration for layout integration
        """
        logger.debug("Building document upload interface")

        components = {}
        layout_config = {}

        # Internal Information Section - Full Width (Matching Chat Layout)
        with gr.Group(elem_classes=["file-management-section"]):

            # Section Header
            section_header = gr.HTML(
                "<div class='file-section-title'>📁 Document Repository</div>"
            )
            components["section_header"] = section_header

            # Upload Buttons Row
            with gr.Row():
                # Files Upload Button
                upload_button = gr.components.UploadButton(
                    "📄 Upload Files",
                    type="filepath",
                    file_count="multiple",
                    size="lg",
                    elem_classes=["modern-button", "upload-button"],
                    elem_id="upload-files",
                    scale=1,
                )
                components["upload_button"] = upload_button

                # Folder Upload Button - Gradio Native Implementation
                folder_upload_button = gr.components.UploadButton(
                    "📁 Upload Folders",
                    type="filepath",
                    file_count="multiple",
                    size="lg",
                    elem_classes=["modern-button", "folder-button"],
                    elem_id="upload-folders",
                    scale=1,
                )
                components["folder_upload_button"] = folder_upload_button

            # Second Row: Document Management Buttons
            with gr.Row():
                remove_selected_button = gr.Button(
                    "🗑️ Remove Selected",
                    size="sm",
                    elem_classes=["modern-button", "warning-button"],
                    scale=1,
                    elem_id="remove-selected-docs",
                )
                components["remove_selected_button"] = remove_selected_button

                clear_all_button = gr.Button(
                    "🗑️ Clear All Documents",
                    size="sm",
                    elem_classes=["modern-button", "danger-button"],
                    scale=1,
                    elem_id="clear-all-docs",
                )
                components["clear_all_button"] = clear_all_button

            # Status message for upload operations
            upload_status_msg = gr.HTML(value="", elem_classes=["upload-status"])
            components["upload_status_msg"] = upload_status_msg

            # Status message for clear operations
            clear_status_msg = gr.HTML(value="", elem_classes=["clear-status"])
            components["clear_status_msg"] = clear_status_msg

            # Status message for remove operations
            remove_status_msg = gr.HTML(value="", elem_classes=["remove-status"])
            components["remove_status_msg"] = remove_status_msg

            # Hidden component to track selected files
            selected_files_state = gr.State([])
            components["selected_files_state"] = selected_files_state

            # Hidden textbox for JavaScript-to-Python bridge
            selected_files_bridge = gr.Textbox(
                value="[]",
                visible=False,
                elem_id="selected-files-bridge-input",
                interactive=True,
            )
            components["selected_files_bridge"] = selected_files_bridge

            # File List Display
            file_list_header = gr.HTML(
                "<div class='file-list-header'>📋 Unique Documents:</div>"
            )
            components["file_list_header"] = file_list_header

            ingested_dataset = gr.HTML(
                value=self.format_file_list_fn(), elem_classes=["file-list-display"]
            )
            components["ingested_dataset"] = ingested_dataset

            # Add resize handle for Internal Information
            resize_handle = gr.HTML(
                '<div class="internal-resize-handle" id="internal-resize-handle"></div>'
            )
            components["resize_handle"] = resize_handle

        # Store layout configuration
        layout_config["file_management_section"] = True
        layout_config["upload_enabled"] = True
        layout_config["folder_processing"] = True

        logger.debug(
            f"Document upload interface created with {len(components)} components"
        )
        return components, layout_config

    def get_component_references(self, components: dict[str, Any]) -> dict[str, Any]:
        """Extract component references for external event handling.

        Args:
            components: Dictionary of all created components

        Returns:
            Dictionary mapping component names to Gradio component references
        """
        return {
            "upload_button": components.get("upload_button"),
            "folder_upload_button": components.get("folder_upload_button"),
            "remove_selected_button": components.get("remove_selected_button"),
            "clear_all_button": components.get("clear_all_button"),
            "upload_status_msg": components.get("upload_status_msg"),
            "clear_status_msg": components.get("clear_status_msg"),
            "remove_status_msg": components.get("remove_status_msg"),
            "selected_files_state": components.get("selected_files_state"),
            "selected_files_bridge": components.get("selected_files_bridge"),
            "ingested_dataset": components.get("ingested_dataset"),
            "section_header": components.get("section_header"),
            "file_list_header": components.get("file_list_header"),
            "resize_handle": components.get("resize_handle"),
        }

    def get_layout_configuration(self) -> dict[str, Any]:
        """Get layout configuration for integration with main UI.

        Returns:
            Dictionary containing layout configuration options
        """
        return {
            "section_classes": ["file-management-section"],
            "upload_button_classes": ["modern-button", "upload-button"],
            "folder_button_classes": ["modern-button", "folder-button"],
            "clear_button_classes": ["modern-button", "danger-button"],
            "status_classes": ["upload-status", "clear-status"],
            "file_list_classes": ["file-list-display"],
        }


def create_document_upload_interface(
    format_file_list_fn: Callable[[], str] = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Factory function to create a document upload interface.

    Args:
        format_file_list_fn: Function to format the current file list for display

    Returns:
        Tuple containing components dictionary and layout configuration
    """
    builder = DocumentUploadBuilder(format_file_list_fn)
    return builder.build_document_upload_interface()


def get_document_component_refs(components: dict[str, Any]) -> dict[str, Any]:
    """Extract component references for event handling integration.

    Args:
        components: Dictionary of created components

    Returns:
        Dictionary of component references for external use
    """
    builder = DocumentUploadBuilder()
    return builder.get_component_references(components)
