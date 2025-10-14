"""Document Management Component Builder.

This module contains the DocumentComponentBuilder class that handles
document library interface construction, upload management, and file browser
components for the Internal Assistant UI system.

Author: Internal Assistant Team
Version: 0.6.2
"""

import logging
import gradio as gr
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DocumentComponentBuilder:
    """
    Builder class for document management interface components.

    This class provides methods to build various document-related UI elements
    including upload areas, document libraries, and analysis displays.
    """

    def __init__(self, services: Dict[str, Any]):
        """
        Initialize the document builder.

        Args:
            services: Dictionary of available services
        """
        self.services = services
        self.ingest_service = services.get("ingest")
        self.chunks_service = services.get("chunks")

    def build_upload_interface(self) -> tuple:
        """
        Build document upload interface components.

        Returns:
            Tuple of Gradio components for document upload
        """
        with gr.Column():
            upload_file = gr.File(
                label="Upload Documents",
                file_count="multiple",
                file_types=[".pdf", ".txt", ".docx", ".md", ".csv", ".xlsx", ".pptx"],
                elem_id="doc-upload-area",
            )

            upload_btn = gr.Button(
                "Process Documents", variant="primary", elem_id="process-docs-btn"
            )

            upload_status = gr.HTML(
                value="<p>Ready to upload documents</p>", elem_id="upload-status"
            )

        return upload_file, upload_btn, upload_status

    def build_library_interface(self) -> tuple:
        """
        Build document library display components.

        Returns:
            Tuple of Gradio components for document library
        """
        with gr.Column():
            # Library header with filters
            with gr.Row():
                search_box = gr.Textbox(
                    label="Search Documents",
                    placeholder="Search by filename or content...",
                    elem_id="doc-search",
                )

                filter_dropdown = gr.Dropdown(
                    label="Filter by Type",
                    choices=["All", "PDF", "Word", "Excel", "Text", "Other"],
                    value="All",
                    elem_id="doc-filter",
                )

            # Document display area
            document_display = gr.HTML(
                value=self._get_default_library_html(), elem_id="document-library"
            )

            # Action buttons
            with gr.Row():
                refresh_btn = gr.Button("Refresh", variant="secondary")
                delete_selected_btn = gr.Button("Delete Selected", variant="stop")
                analyze_btn = gr.Button("Analyze All", variant="primary")

        return (
            search_box,
            filter_dropdown,
            document_display,
            refresh_btn,
            delete_selected_btn,
            analyze_btn,
        )

    def list_ingested_files(self) -> List[str]:
        """
        List all ingested files from the ingest service.

        Returns:
            List of file names
        """
        if self.ingest_service:
            try:
                # This would call the actual service method
                # return self.ingest_service.list_files()
                return []  # Placeholder
            except Exception as e:
                logger.error(f"Failed to list files: {e}")
                return []
        return []

    def format_file_list(self, files: List[str]) -> str:
        """
        Format file list as HTML for display.

        Args:
            files: List of file names

        Returns:
            HTML string with formatted file list
        """
        if not files:
            return self._get_default_library_html()

        html = '<div class="document-list">'
        for file in files:
            html += f"""
            <div class="doc-item">
                <span class="doc-name">{file}</span>
                <div class="doc-actions">
                    <button class="view-btn">View</button>
                    <button class="delete-btn">Delete</button>
                </div>
            </div>
            """
        html += "</div>"
        return html

    def get_document_library_html(
        self, search_term: str = "", file_filter: str = "All"
    ) -> str:
        """
        Generate complete document library HTML with search and filtering.

        Args:
            search_term: Search filter
            file_filter: File type filter

        Returns:
            HTML string for document library display
        """
        files = self.list_ingested_files()

        # Apply filters
        if search_term:
            files = [f for f in files if search_term.lower() in f.lower()]

        if file_filter != "All":
            # Apply file type filter
            extensions = {
                "PDF": [".pdf"],
                "Word": [".doc", ".docx"],
                "Excel": [".xls", ".xlsx"],
                "Text": [".txt", ".md"],
            }
            if file_filter in extensions:
                files = [
                    f
                    for f in files
                    if any(f.endswith(ext) for ext in extensions[file_filter])
                ]

        return self.format_file_list(files)

    def _get_default_library_html(self) -> str:
        """Get default HTML for empty document library."""
        return """
        <div class="document-library-empty">
            <div class="empty-state">
                <h3>📁 Document Library</h3>
                <p>No documents uploaded yet.</p>
                <p>Upload documents using the file input above to get started.</p>
                <ul>
                    <li>📄 Supported: PDF, Word, Excel, PowerPoint, Text, Markdown</li>
                    <li>🔍 Documents will be indexed for search</li>
                    <li>💾 Files are processed and stored securely</li>
                </ul>
            </div>
        </div>
        """
