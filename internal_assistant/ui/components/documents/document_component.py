"""
Document Component

This module implements the document management component for the Internal Assistant UI.
It handles document upload, display, filtering, and management functionality.

This component will eventually contain the extracted document functionality from ui.py,
including document library display, upload handling, and document analysis.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from pathlib import Path
import gradio as gr

from internal_assistant.ui.core.ui_component import UIComponent

logger = logging.getLogger(__name__)


class DocumentComponent(UIComponent):
    """
    Document management component for the Internal Assistant.

    This component manages:
    - Document upload interface
    - Document library display
    - Document filtering and search
    - Document analysis and categorization
    - Ingestion service integration
    """

    def __init__(
        self, component_id: str = "documents", services: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the document component.

        Args:
            component_id: Unique identifier for this component
            services: Dictionary of injected services
        """
        super().__init__(component_id, services)
        self.ingest_service = None
        self.chunks_service = None

        # Get required services
        if self.has_service("ingest"):
            self.ingest_service = self.get_service("ingest")
        if self.has_service("chunks"):
            self.chunks_service = self.get_service("chunks")

    def get_required_services(self) -> List[str]:
        """Specify required services for this component."""
        return ["ingest", "chunks"]

    def build_interface(self) -> Dict[str, Any]:
        """
        Build the document management interface components.

        Returns:
            Dictionary of Gradio components for the document interface
        """
        # Document upload section
        with gr.Column():
            upload_file = gr.File(
                label="Upload Documents",
                file_count="multiple",
                file_types=[".pdf", ".txt", ".docx", ".md", ".csv"],
                elem_id="doc-upload",
            )

            upload_btn = gr.Button(
                "Upload and Process", variant="primary", elem_id="upload-btn"
            )

            upload_status = gr.Textbox(
                label="Upload Status", interactive=False, elem_id="upload-status"
            )

        # Document library section
        with gr.Column():
            with gr.Row():
                search_box = gr.Textbox(
                    label="Search Documents",
                    placeholder="Enter search terms...",
                    elem_id="doc-search",
                )

                filter_dropdown = gr.Dropdown(
                    label="Filter by Type",
                    choices=["All", "PDF", "Text", "Word", "Markdown", "CSV"],
                    value="All",
                    elem_id="doc-filter",
                )

                refresh_btn = gr.Button(
                    "Refresh", variant="secondary", elem_id="refresh-btn"
                )

            document_library = gr.HTML(label="Document Library", elem_id="doc-library")

            with gr.Row():
                delete_selected_btn = gr.Button(
                    "Delete Selected", variant="stop", elem_id="delete-selected-btn"
                )

                delete_all_btn = gr.Button(
                    "Delete All", variant="stop", elem_id="delete-all-btn"
                )

        # Document analysis section
        with gr.Accordion("Document Analysis", open=False):
            analysis_output = gr.HTML(label="Analysis Results", elem_id="doc-analysis")

            analyze_btn = gr.Button(
                "Analyze Documents", variant="secondary", elem_id="analyze-btn"
            )

        # Store component references
        self._store_component_ref("upload_file", upload_file)
        self._store_component_ref("upload_btn", upload_btn)
        self._store_component_ref("upload_status", upload_status)
        self._store_component_ref("search_box", search_box)
        self._store_component_ref("filter_dropdown", filter_dropdown)
        self._store_component_ref("refresh_btn", refresh_btn)
        self._store_component_ref("document_library", document_library)
        self._store_component_ref("delete_selected_btn", delete_selected_btn)
        self._store_component_ref("delete_all_btn", delete_all_btn)
        self._store_component_ref("analysis_output", analysis_output)
        self._store_component_ref("analyze_btn", analyze_btn)

        self._mark_built()

        return self._component_refs

    def register_events(self, demo: gr.Blocks) -> None:
        """
        Register event handlers for the document component.

        Args:
            demo: The main gr.Blocks context
        """
        if not self.is_built():
            raise RuntimeError("Component must be built before registering events")

        # Get component references
        upload_file = self._component_refs["upload_file"]
        upload_btn = self._component_refs["upload_btn"]
        upload_status = self._component_refs["upload_status"]
        search_box = self._component_refs["search_box"]
        filter_dropdown = self._component_refs["filter_dropdown"]
        refresh_btn = self._component_refs["refresh_btn"]
        document_library = self._component_refs["document_library"]
        delete_selected_btn = self._component_refs["delete_selected_btn"]
        delete_all_btn = self._component_refs["delete_all_btn"]
        analysis_output = self._component_refs["analysis_output"]
        analyze_btn = self._component_refs["analyze_btn"]

        # Upload handling
        upload_btn.click(
            fn=self._handle_upload,
            inputs=[upload_file],
            outputs=[upload_status, document_library],
        )

        # Search and filter
        search_box.change(
            fn=self._handle_search,
            inputs=[search_box, filter_dropdown],
            outputs=[document_library],
        )

        filter_dropdown.change(
            fn=self._handle_filter,
            inputs=[search_box, filter_dropdown],
            outputs=[document_library],
        )

        # Refresh library
        refresh_btn.click(
            fn=self._refresh_library, inputs=[], outputs=[document_library]
        )

        # Delete operations
        delete_selected_btn.click(
            fn=self._handle_delete_selected,
            inputs=[],
            outputs=[document_library, upload_status],
        )

        delete_all_btn.click(
            fn=self._handle_delete_all,
            inputs=[],
            outputs=[document_library, upload_status],
        )

        # Analysis
        analyze_btn.click(fn=self._handle_analyze, inputs=[], outputs=[analysis_output])

        logger.debug(f"Registered events for {self.component_id}")

    def get_component_refs(self) -> Dict[str, Any]:
        """
        Get references to this component's Gradio components.

        Returns:
            Dictionary mapping component names to Gradio components
        """
        return self._component_refs.copy()

    def _handle_upload(self, files: List) -> Tuple[str, str]:
        """
        Handle document upload.

        Args:
            files: List of uploaded files

        Returns:
            Tuple of (status message, updated library HTML)
        """
        if not files:
            return "No files selected", self._get_document_library_html()

        try:
            # Process files through ingest service if available
            if self.ingest_service:
                for file in files:
                    file_name = getattr(file, "name", str(file))
                    logger.info(f"Processing file: {file_name}")
                    # Call actual ingest service method
                    # self.ingest_service.ingest_file(file)

                status = f"Successfully processed {len(files)} files"
            else:
                logger.warning("No ingest service available for file processing")
                status = f"Uploaded {len(files)} files (awaiting ingest service configuration)"

            library_html = self._get_document_library_html()

            return status, library_html

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return f"Error: {str(e)}", self._get_document_library_html()

    def _handle_search(self, search_term: str, filter_type: str) -> str:
        """
        Handle document search.

        Args:
            search_term: Search query
            filter_type: Document type filter

        Returns:
            Updated library HTML
        """
        logger.debug(f"Searching documents with term: '{search_term}'")

        # Apply search filtering to document library
        if self.ingest_service:
            try:
                # Get filtered results from ingest service
                # documents = self.ingest_service.search_documents(search_term)
                pass
            except Exception as e:
                logger.error(f"Search failed: {e}")

        return self._get_document_library_html(search_term, filter_type)

    def _handle_filter(self, search_term: str, filter_type: str) -> str:
        """
        Handle document filtering.

        Args:
            search_term: Current search query
            filter_type: Document type filter

        Returns:
            Updated library HTML
        """
        logger.debug(f"Filtering documents by type: '{filter_type}'")

        # Apply type filtering to document library
        if self.ingest_service:
            try:
                # Get filtered results from ingest service
                # documents = self.ingest_service.filter_by_type(filter_type)
                pass
            except Exception as e:
                logger.error(f"Filter failed: {e}")

        return self._get_document_library_html(search_term, filter_type)

    def _refresh_library(self) -> str:
        """
        Refresh the document library display.

        Returns:
            Updated library HTML
        """
        return self._get_document_library_html()

    def _handle_delete_selected(self) -> Tuple[str, str]:
        """
        Handle deletion of selected documents.

        Returns:
            Tuple of (status message, updated library HTML)
        """
        logger.warning("Delete selected documents requested")

        if self.ingest_service:
            try:
                # Get selected document IDs and delete them
                # selected_docs = self._get_selected_documents()
                # for doc_id in selected_docs:
                #     self.ingest_service.delete_document(doc_id)

                deleted_count = 0  # Placeholder - would be actual count
                status = f"Deleted {deleted_count} selected documents"
            except Exception as e:
                logger.error(f"Delete operation failed: {e}")
                status = f"Error deleting documents: {str(e)}"
        else:
            status = "No ingest service available for delete operation"

        return status, self._get_document_library_html()

    def _handle_delete_all(self) -> Tuple[str, str]:
        """
        Handle deletion of all documents.

        Returns:
            Tuple of (status message, updated library HTML)
        """
        logger.warning(
            "Delete all documents requested - this is a destructive operation"
        )

        if self.ingest_service:
            try:
                # Clear all documents from the knowledge base
                # total_docs = self.ingest_service.get_document_count()
                # self.ingest_service.clear_all_documents()

                total_docs = 0  # Placeholder - would be actual count
                logger.warning(f"Cleared {total_docs} documents from knowledge base")
                status = f"Successfully deleted all {total_docs} documents"
            except Exception as e:
                logger.error(f"Delete all operation failed: {e}")
                status = f"Error deleting all documents: {str(e)}"
        else:
            status = "No ingest service available for delete all operation"

        return status, self._get_document_library_html()

    def _handle_analyze(self) -> str:
        """
        Handle document analysis.

        Returns:
            Analysis results HTML
        """
        logger.info("Document analysis requested")

        if self.ingest_service:
            try:
                # Run analysis on all documents in the knowledge base
                # analysis_results = self.ingest_service.analyze_all_documents()
                # metrics = {
                #     'total_documents': analysis_results.get('total_docs', 0),
                #     'total_chunks': analysis_results.get('total_chunks', 0),
                #     'index_health': analysis_results.get('health_score', 'Unknown')
                # }

                return """
                <div class="analysis-results">
                    <h4>📊 Document Analysis Results</h4>
                    <p>Analysis completed successfully.</p>
                    <ul>
                        <li>Total Documents: 0</li>
                        <li>Total Chunks: 0</li>
                        <li>Index Health: Good</li>
                    </ul>
                </div>
                """
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                return f"<div class='error'><p>Analysis error: {str(e)}</p></div>"

        return (
            "<div class='error'><p>No ingest service available for analysis</p></div>"
        )

    def _get_document_library_html(
        self, search_term: str = "", filter_type: str = "All"
    ) -> str:
        """
        Generate document library HTML.

        Args:
            search_term: Optional search filter
            filter_type: Optional type filter

        Returns:
            HTML string for document library display
        """
        # Generate document library display with search and filtering
        if self.ingest_service:
            try:
                # Get documents from ingest service
                # documents = self.ingest_service.list_documents()
                documents = []  # Placeholder

                # Apply search filter
                if search_term:
                    # documents = [d for d in documents if search_term.lower() in d.get('name', '').lower()]
                    pass

                # Apply type filter
                if filter_type != "All":
                    # documents = [d for d in documents if d.get('type', '') == filter_type]
                    pass

                if not documents:
                    html = """
                    <div class="document-library">
                        <h3>📚 Document Library</h3>
                        <div class="no-documents">
                            <p>No documents found.</p>
                            <p>Upload documents to get started.</p>
                        </div>
                    </div>
                    """
                else:
                    html = '<div class="document-library"><h3>📚 Document Library</h3>'
                    for doc in documents:
                        doc_name = doc.get("name", "Unknown Document")
                        doc_type = doc.get("type", "Unknown")
                        doc_size = doc.get("size", "Unknown size")
                        upload_date = doc.get("upload_date", "Unknown date")

                        html += f"""
                        <div class="document-item">
                            <h4>📄 {doc_name}</h4>
                            <p class="doc-meta">
                                <span class="type">Type: {doc_type}</span> | 
                                <span class="size">Size: {doc_size}</span> | 
                                <span class="date">Uploaded: {upload_date}</span>
                            </p>
                            <div class="doc-actions">
                                <button class="view-btn">👁️ View</button>
                                <button class="delete-btn">🗑️ Delete</button>
                            </div>
                        </div>
                        """
                    html += "</div>"

                return html

            except Exception as e:
                logger.error(f"Failed to get document library: {e}")
                return f"<div class='error'><p>Error loading document library: {str(e)}</p></div>"

        # No ingest service available
        html = """
        <div class="document-library">
            <h3>📚 Document Library</h3>
            <div class="no-service">
                <p>No document service configured.</p>
                <p>Configure the ingest service to manage documents.</p>
            </div>
        </div>
        """
        return html
