"""Sidebar Component

This module implements the sidebar component for the Internal Assistant UI.
It handles mode selection, document upload controls, and advanced settings.

This component will eventually contain the extracted sidebar functionality from ui.py,
including mode selection, upload controls, and settings management.
"""

import logging
from typing import Any

import gradio as gr

from internal_assistant.ui.core.ui_component import UIComponent

logger = logging.getLogger(__name__)


class SidebarComponent(UIComponent):
    """Sidebar component for the Internal Assistant.

    This component manages:
    - Mode selection (RAG/General LLM)
    - Document upload controls
    - Advanced settings and configurations
    - System information display
    - Quick actions and shortcuts
    """

    def __init__(
        self, component_id: str = "sidebar", services: dict[str, Any] | None = None
    ):
        """Initialize the sidebar component.

        Args:
            component_id: Unique identifier for this component
            services: Dictionary of injected services
        """
        super().__init__(component_id, services)
        self.ingest_service = None

        # Get required services
        if self.has_service("ingest"):
            self.ingest_service = self.get_service("ingest")

    def get_required_services(self) -> list[str]:
        """Specify required services for this component."""
        return []  # Sidebar doesn't strictly require services

    def build_interface(self) -> dict[str, Any]:
        """Build the sidebar interface components.

        Returns:
            Dictionary of Gradio components for the sidebar interface
        """
        # Mode selection
        with gr.Group():
            mode_selector = gr.Radio(
                label="Assistant Mode",
                choices=["RAG Mode", "General LLM"],
                value="RAG Mode",
                elem_id="mode-selector",
            )

            mode_description = gr.Markdown(
                "**RAG Mode**: Use your uploaded documents for context-aware responses.\n\n"
                "**General LLM**: Direct LLM interaction without document context.",
                elem_id="mode-description",
            )

        # Document upload section
        with gr.Group():
            gr.Markdown("### Document Upload")

            upload_file = gr.File(
                label="Quick Upload",
                file_count="multiple",
                file_types=[".pdf", ".txt", ".docx", ".md", ".csv"],
                elem_id="sidebar-upload",
            )

            upload_btn = gr.Button(
                "Upload", variant="primary", size="sm", elem_id="sidebar-upload-btn"
            )

            doc_count = gr.Textbox(
                label="Documents in Library",
                value="0 documents",
                interactive=False,
                elem_id="doc-count",
            )

        # Advanced settings
        with gr.Accordion("Advanced Settings", open=False):
            system_prompt = gr.Textbox(
                label="System Prompt",
                placeholder="Optional system prompt...",
                lines=3,
                elem_id="sidebar-system-prompt",
            )

            similarity_threshold = gr.Slider(
                minimum=0.1,
                maximum=1.0,
                value=0.7,
                step=0.1,
                label="Similarity Threshold",
                elem_id="similarity-threshold",
            )

            response_temperature = gr.Slider(
                minimum=0,
                maximum=1,
                value=0.1,
                step=0.1,
                label="Response Temperature",
                elem_id="response-temperature",
            )

            citation_style = gr.Radio(
                label="Citation Style",
                choices=["Include Sources", "No Sources", "Inline Citations"],
                value="Include Sources",
                elem_id="citation-style",
            )

            response_length = gr.Radio(
                label="Response Length",
                choices=["Short", "Medium", "Long", "Very Long"],
                value="Short",
                elem_id="response-length",
            )

        # System information
        with gr.Accordion("System Info", open=False):
            system_info = gr.HTML(value=self._get_system_info(), elem_id="system-info")

            refresh_info_btn = gr.Button(
                "Refresh", size="sm", elem_id="refresh-info-btn"
            )

        # Quick actions
        with gr.Group():
            gr.Markdown("### Quick Actions")

            clear_all_btn = gr.Button(
                "Clear All Data", variant="stop", size="sm", elem_id="clear-all-btn"
            )

            export_btn = gr.Button(
                "Export Chat", variant="secondary", size="sm", elem_id="export-btn"
            )

            help_btn = gr.Button(
                "Help", variant="secondary", size="sm", elem_id="help-btn"
            )

        # Store component references
        self._store_component_ref("mode_selector", mode_selector)
        self._store_component_ref("mode_description", mode_description)
        self._store_component_ref("upload_file", upload_file)
        self._store_component_ref("upload_btn", upload_btn)
        self._store_component_ref("doc_count", doc_count)
        self._store_component_ref("system_prompt", system_prompt)
        self._store_component_ref("similarity_threshold", similarity_threshold)
        self._store_component_ref("response_temperature", response_temperature)
        self._store_component_ref("citation_style", citation_style)
        self._store_component_ref("response_length", response_length)
        self._store_component_ref("system_info", system_info)
        self._store_component_ref("refresh_info_btn", refresh_info_btn)
        self._store_component_ref("clear_all_btn", clear_all_btn)
        self._store_component_ref("export_btn", export_btn)
        self._store_component_ref("help_btn", help_btn)

        self._mark_built()

        return self._component_refs

    def register_events(self, demo: gr.Blocks) -> None:
        """Register event handlers for the sidebar component.

        Args:
            demo: The main gr.Blocks context
        """
        if not self.is_built():
            raise RuntimeError("Component must be built before registering events")

        # Get component references
        mode_selector = self._component_refs["mode_selector"]
        upload_file = self._component_refs["upload_file"]
        upload_btn = self._component_refs["upload_btn"]
        doc_count = self._component_refs["doc_count"]
        refresh_info_btn = self._component_refs["refresh_info_btn"]
        system_info = self._component_refs["system_info"]
        clear_all_btn = self._component_refs["clear_all_btn"]
        export_btn = self._component_refs["export_btn"]
        help_btn = self._component_refs["help_btn"]

        # Mode selection
        mode_selector.change(
            fn=self._handle_mode_change, inputs=[mode_selector], outputs=[]
        )

        # Upload handling
        upload_btn.click(
            fn=self._handle_quick_upload, inputs=[upload_file], outputs=[doc_count]
        )

        # System info refresh
        refresh_info_btn.click(
            fn=self._refresh_system_info, inputs=[], outputs=[system_info]
        )

        # Quick actions
        clear_all_btn.click(fn=self._handle_clear_all, inputs=[], outputs=[doc_count])

        export_btn.click(fn=self._handle_export, inputs=[], outputs=[])

        help_btn.click(fn=self._handle_help, inputs=[], outputs=[])

        logger.debug(f"Registered events for {self.component_id}")

    def get_component_refs(self) -> dict[str, Any]:
        """Get references to this component's Gradio components.

        Returns:
            Dictionary mapping component names to Gradio components
        """
        return self._component_refs.copy()

    def _handle_mode_change(self, mode: str) -> None:
        """Handle mode selection change.

        Args:
            mode: Selected mode
        """
        from internal_assistant.ui.models.modes import normalize_mode

        normalized = normalize_mode(mode)
        logger.info(f"Mode changed to: {normalized}")

        # Update any mode-dependent UI state
        if normalized == "RAG Mode":
            logger.debug("Switched to Document Assistant mode")
        else:
            logger.debug("Switched to General LLM mode")

    def _handle_quick_upload(self, files: list) -> str:
        """Handle quick file upload from sidebar.

        Args:
            files: List of uploaded files

        Returns:
            Updated document count
        """
        if not files:
            return self._get_document_count()

        try:
            if self.ingest_service:
                # Process files through ingest service
                for file in files:
                    logger.info(
                        f"Processing file: {file.name if hasattr(file, 'name') else str(file)}"
                    )

                # Return updated count
                total_docs = self._get_document_count()
                count = f"{total_docs} documents"
            else:
                count = f"{len(files)} documents uploaded (no ingest service)"

            return count

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return "Error uploading files"

    def _refresh_system_info(self) -> str:
        """Refresh system information display.

        Returns:
            Updated system info HTML
        """
        return self._get_system_info()

    def _handle_clear_all(self) -> str:
        """Handle clear all data action.

        Returns:
            Updated document count
        """
        if self.ingest_service:
            try:
                # This would clear all ingested documents
                logger.warning("Clearing all documents from knowledge base")
                # In a real implementation, this would call:
                # self.ingest_service.clear_all_documents()
                return "All documents cleared"
            except Exception as e:
                logger.error(f"Failed to clear documents: {e}")
                return f"Error clearing documents: {e!s}"
        else:
            logger.warning("Clear all data requested (no ingest service)")
            return "No ingest service available"

    def _handle_export(self) -> None:
        """Handle export chat action."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_export_{timestamp}.txt"

        logger.info(f"Export chat requested: {filename}")
        # In a real implementation, this would:
        # 1. Get chat history from session state
        # 2. Format it as text/JSON/HTML
        # 3. Provide download link
        logger.info("Export functionality would save chat history to file")

    def _handle_help(self) -> None:
        """Handle help action."""
        logger.info("Help requested")
        # In a real implementation, this would:
        # 1. Open help modal or documentation
        # 2. Display quick tips overlay
        # 3. Navigate to help page
        help_message = (
            "Internal Assistant Help:\n"
            "- Upload documents for RAG mode\n"
            "- Use General LLM for direct questions\n"
            "- Adjust settings in Advanced panel\n"
            "- Export chat history when needed"
        )
        logger.info(help_message)

    def _get_document_count(self) -> str:
        """Get current document count.

        Returns:
            Document count string
        """
        if self.ingest_service:
            try:
                # This would get actual count from service
                # count = self.ingest_service.get_document_count()
                # For now, return placeholder
                return "0 documents"
            except Exception as e:
                logger.error(f"Failed to get document count: {e}")
                return "Error getting count"
        return "0 documents"

    def _get_system_info(self) -> str:
        """Generate system information HTML.

        Returns:
            HTML string with system information
        """
        import platform
        from datetime import datetime

        import psutil

        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Get current time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return f"""
            <div class="system-info">
                <p><b>Version:</b> 0.6.2</p>
                <p><b>Model:</b> Llama 3.1 70B</p>
                <p><b>Vector DB:</b> Qdrant</p>
                <p><b>Platform:</b> {platform.system()} {platform.release()}</p>
                <p><b>CPU Usage:</b> {cpu_percent}%</p>
                <p><b>Memory:</b> {memory.percent}% used</p>
                <p><b>Disk:</b> {disk.percent}% used</p>
                <p><b>Last Update:</b> {current_time}</p>
                <p><b>Status:</b> <span style="color: green;">Ready</span></p>
            </div>
            """
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return """
            <div class="system-info">
                <p><b>Version:</b> 0.6.2</p>
                <p><b>Model:</b> Llama 3.1 70B</p>
                <p><b>Vector DB:</b> Qdrant</p>
                <p><b>Status:</b> <span style="color: green;">Ready</span></p>
                <p><b>Error:</b> Could not get system metrics</p>
            </div>
            """
