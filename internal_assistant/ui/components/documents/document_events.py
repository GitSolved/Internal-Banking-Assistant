"""Document Event Handler Builder Component

This module contains document-related event handlers extracted from ui.py
during Phase 1B.3 of the UI refactoring project.

Extracted from ui.py lines:
- upload_and_refresh() (lines 6999-7017)
- ingest_server_folder() (lines 7023-7109)
- clear_all_documents() (lines 7111-7164)
- refresh_file_list() (lines 7214-7215)
- handle_search() (lines 7218-7221)
- handle_filter() (lines 7223-7226)
- handle_filter_with_scroll() (lines 7236-7250)
- sync_sidebar_with_main() (lines 7308-7310)

Author: UI Refactoring Team
Date: 2024-01-18
Phase: 1B.3 - Document Event Handlers Extraction
"""

import logging
import os
import sys
from pathlib import Path

from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.ui.components.documents.document_library import (
    DocumentLibraryBuilder,
)
from internal_assistant.ui.components.documents.document_utility import (
    DocumentUtilityBuilder,
)
from internal_assistant.ui.core.error_boundaries import create_error_boundary

logger = logging.getLogger(__name__)


class DocumentEventHandlerBuilder:
    """Builder class for document-related event handlers.
    Handles file uploads, folder ingestion, document clearing, and search/filter events.
    """

    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService | None,
        utility_builder: DocumentUtilityBuilder,
        library_builder: DocumentLibraryBuilder,
        upload_file_method,
        get_model_status_method,
        document_service_facade=None,
    ):
        """Initialize the DocumentEventHandlerBuilder.

        Args:
            ingest_service: Service for managing document ingestion
            chat_service: Service for chat-related functionality
            utility_builder: DocumentUtilityBuilder from Phase 1B.1
            library_builder: DocumentLibraryBuilder from Phase 1B.2
            upload_file_method: Reference to _upload_file method from ui.py
            get_model_status_method: Reference to get_model_status method
            document_service_facade: Optional DocumentServiceFacade for cache management
        """
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._utility_builder = utility_builder
        self._library_builder = library_builder
        self._upload_file = upload_file_method
        self._get_model_status = get_model_status_method
        self._document_facade = document_service_facade

        # Initialize error boundaries for document operations
        self.upload_error_boundary = create_error_boundary(
            "document_upload", "document", "File upload temporarily unavailable"
        )
        self.ingest_error_boundary = create_error_boundary(
            "document_ingest", "document", "Document processing temporarily unavailable"
        )
        self.list_error_boundary = create_error_boundary(
            "document_list", "document", "Document listing temporarily unavailable"
        )

    def upload_and_refresh(self, files) -> tuple[str, str, str, str]:
        """Handle file upload and refresh UI components with error boundary protection.

        Args:
            files: List of uploaded files

        Returns:
            Tuple of (file_list, status_message, document_library, model_status)
        """
        try:
            return self._execute_upload_and_refresh(files)
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error in upload_and_refresh: {e}")

            # Return safe fallback UI state
            error_msg = "⚠️ File upload failed. Please try again or contact support if the issue persists."
            fallback_status = f"""
                <div style='display: flex; flex-direction: column; gap: 12px;'>
                    <div class='status-indicator' style='color: red;'>{error_msg}</div>
                </div>
            """
            # Get current model status even on error
            fallback_model_status = self._get_model_status()

            return (
                "📄 Document listing temporarily unavailable",
                fallback_status,
                "📚 Document library temporarily unavailable",
                fallback_model_status,
            )

    def _execute_upload_and_refresh(self, files) -> tuple[str, str, str, str]:
        """Protected upload and refresh logic with enhanced status reporting."""
        upload_status = "📄 Ready for uploads"

        if files:
            try:
                # Use enhanced upload method that returns detailed status
                updated_file_list, upload_status, updated_document_library = (
                    self._upload_file(files)
                )

                # Prefix status for file upload
                if "✅" in upload_status:
                    final_status = f"📄 File Upload: {upload_status}"
                else:
                    final_status = f"📄 File Upload Failed: {upload_status}"

                # Get updated model status (includes updated document count)
                updated_model_status = self._get_model_status()

                return (
                    updated_file_list,
                    final_status,
                    updated_document_library,
                    updated_model_status,
                )

            except Exception as e:
                logger.error(f"Error in enhanced upload process: {e}")
                upload_status = f"📄 ❌ File upload error: {e!s}"

        # Fallback: Return updated file list and default status
        updated_document_library = self._library_builder.get_document_library_html()
        updated_model_status = self._get_model_status()

        return (
            self._utility_builder.format_file_list(),
            upload_status,
            updated_document_library,
            updated_model_status,
        )

    def ingest_server_folder(self, folder_path: str) -> tuple[str, str, str, str]:
        """Ingest a server-side folder using the ingest_folder script functionality.

        Args:
            folder_path: Path to the folder to ingest

        Returns:
            Tuple of (file_list, status_message, document_library, model_status)
        """
        if not folder_path or folder_path.strip() == "":
            return (
                self._utility_builder.format_file_list(),
                "❌ Please enter a folder path",
                self._library_builder.get_document_library_html(),
                self._get_model_status(),
            )

        try:
            folder_path_obj = Path(folder_path.strip())

            if not folder_path_obj.exists():
                return (
                    self._utility_builder.format_file_list(),
                    "❌ Folder path does not exist",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            if not folder_path_obj.is_dir():
                return (
                    self._utility_builder.format_file_list(),
                    "❌ Path is not a directory",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            # Use LocalIngestWorker directly for folder ingestion
            sys.path.append(
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "..", "tools", "data"
                )
            )

            try:
                from ingest_folder import LocalIngestWorker

                from internal_assistant.settings.settings import settings

                # Initialize worker
                worker = LocalIngestWorker(
                    self._ingest_service,
                    settings(),
                    max_attempts=2,
                    checkpoint_file="ui_folder_ingestion_checkpoint.json",
                )

                # Process the folder
                worker.ingest_folder(folder_path_obj, ignored=[], resume=True)
                status = "✅ Folder ingested successfully!"

            except ImportError as e:
                logger.error(f"Failed to import LocalIngestWorker: {e}")
                return (
                    self._utility_builder.format_file_list(),
                    f"❌ Folder ingestion not available: {e!s}",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )
            except Exception as e:
                logger.error(f"Folder ingestion failed: {e}")
                return (
                    self._utility_builder.format_file_list(),
                    f"❌ Ingestion failed: {e!s}",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            # Update UI components
            updated_model_status = self._get_model_status()
            updated_document_library = self._library_builder.get_document_library_html()

            return (
                self._utility_builder.format_file_list(),
                status,  # Success/error message from _ingest_folder
                updated_document_library,
                updated_model_status,
            )

        except Exception as e:
            logger.error(f"Folder ingestion error: {e}")
            return (
                self._utility_builder.format_file_list(),
                f"❌ Error: {e!s}",
                self._library_builder.get_document_library_html(),
                self._get_model_status(),
            )

    def clear_all_documents(self) -> tuple[str, str, str, str]:
        """Clear all ingested documents with comprehensive verification.

        Returns:
            Tuple of (file_list, status_message, document_library, model_status)
        """
        logger.info("🗑️ [CLEAR_ALL] clear_all_documents called")

        try:
            # Get all ingested documents
            logger.info("🗑️ [CLEAR_ALL] Getting list of all ingested documents...")
            ingested_docs = self._ingest_service.list_ingested()
            logger.info(f"🗑️ [CLEAR_ALL] Found {len(ingested_docs)} documents to clear")

            if not ingested_docs:
                logger.info("🗑️ [CLEAR_ALL] No documents found to clear")
                return (
                    self._utility_builder.format_file_list(),
                    "ℹ️ No documents to clear",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            doc_count = len(ingested_docs)
            logger.info(f"🗑️ [CLEAR_ALL] Starting deletion of {doc_count} documents")

            # Log document details before deletion
            for i, doc in enumerate(ingested_docs):
                file_name = (
                    doc.doc_metadata.get("file_name", "Unknown")
                    if doc.doc_metadata
                    else "Unknown"
                )
                logger.info(
                    f"🗑️ [CLEAR_ALL] Document {i+1}: {file_name} (ID: {doc.doc_id})"
                )

            # Delete all documents
            failed_deletions = []
            successful_deletions = []

            for i, doc in enumerate(ingested_docs):
                try:
                    file_name = (
                        doc.doc_metadata.get("file_name", doc.doc_id)
                        if doc.doc_metadata
                        else doc.doc_id
                    )
                    logger.info(
                        f"🗑️ [CLEAR_ALL] [{i+1}/{doc_count}] Deleting document: {file_name}"
                    )

                    self._ingest_service.delete(doc.doc_id)
                    successful_deletions.append(file_name)
                    logger.info(
                        f"🗑️ [CLEAR_ALL] [{i+1}/{doc_count}] ✅ Successfully deleted: {file_name}"
                    )

                except Exception as e:
                    file_name = (
                        doc.doc_metadata.get("file_name", doc.doc_id)
                        if doc.doc_metadata
                        else doc.doc_id
                    )
                    failed_deletions.append(file_name)
                    logger.error(
                        f"🗑️ [CLEAR_ALL] [{i+1}/{doc_count}] ❌ Failed to delete {file_name}: {e}"
                    )

            logger.info(
                f"🗑️ [CLEAR_ALL] Deletion complete. Success: {len(successful_deletions)}, Failed: {len(failed_deletions)}"
            )

            # Verify clearance by checking remaining documents
            try:
                remaining_docs = self._ingest_service.list_ingested()
                logger.info(
                    f"🗑️ [CLEAR_ALL] After clearance: {len(remaining_docs)} documents remain"
                )

                if remaining_docs:
                    logger.error(
                        f"❌ [CLEAR_ALL] CLEARANCE FAILED: {len(remaining_docs)} documents still present after clear operation!"
                    )

                    # Log which documents are still there
                    for doc in remaining_docs:
                        file_name = (
                            doc.doc_metadata.get("file_name", "Unknown")
                            if doc.doc_metadata
                            else "Unknown"
                        )
                        logger.error(
                            f"❌ [CLEAR_ALL] Still present: {file_name} (ID: {doc.doc_id})"
                        )
                else:
                    logger.info(
                        "✅ [CLEAR_ALL] Clearance verification successful: No documents remain"
                    )

            except Exception as e:
                logger.warning(f"🗑️ [CLEAR_ALL] Error verifying clearance: {e}")

            # Prepare status message
            if failed_deletions:
                success_count = len(successful_deletions)
                status_msg = f"⚠️ Cleared {success_count}/{doc_count} documents. Failed to delete: {', '.join(failed_deletions)}"
            else:
                status_msg = f"✅ Successfully cleared all {doc_count} documents"

            # Verify deletion was successful (with brief delay for persistence)
            import time

            time.sleep(0.3)

            try:
                final_check = self._ingest_service.list_ingested()
                if final_check:
                    logger.error(
                        f"❌ [CLEAR_ALL] Deletion verification failed: {len(final_check)} documents still remain"
                    )
                    status_msg += f" ⚠️ Warning: {len(final_check)} documents were not deleted successfully."
                else:
                    logger.info(
                        "✅ [CLEAR_ALL] Deletion verified: All documents successfully removed"
                    )
            except Exception as e:
                logger.warning(f"⚠️ [CLEAR_ALL] Could not verify deletion: {e}")

            # Update UI components
            logger.info("🗑️ [CLEAR_ALL] Updating UI components...")
            updated_model_status = self._get_model_status()
            updated_header_html = f"""
                <div style='display: flex; flex-direction: column; gap: 12px;'>
                    <div class='status-indicator'>{updated_model_status}</div>
                </div>
            """

            updated_document_library = self._library_builder.get_document_library_html()
            updated_file_list = self._utility_builder.format_file_list()

            # Add JavaScript to trigger success event and force complete UI refresh
            success_script = """
            <script>
            setTimeout(() => {
                console.log('🔄 [JS] Triggering documentOperationSuccess event for clear all');
                const event = new CustomEvent('documentOperationSuccess');
                document.dispatchEvent(event);

                // Clear any file selections
                if (typeof selectedFiles !== 'undefined') {
                    selectedFiles.clear();
                    console.log('🔄 [JS] Cleared file selections after clear all');
                }

                // Force UI refresh by triggering Gradio's internal refresh
                console.log('🔄 [JS] Forcing complete UI refresh after clear all');

                // Clear document library display
                const docLibrary = document.querySelector('.document-library-display');
                if (docLibrary) {
                    docLibrary.innerHTML = '<div style="text-align: center; color: #666; padding: 20px;">📁 No documents yet</div>';
                    console.log('🔄 [JS] Cleared document library display');
                }

                // Reset all filter buttons to inactive state
                document.querySelectorAll('[id^="filter-"]').forEach(btn => {
                    btn.classList.remove('active');
                });
                console.log('🔄 [JS] Reset filter button states');
            }, 100);
            </script>
            """

            final_status_msg = status_msg + success_script

            # Get updated model status after clearing
            updated_model_status = self._get_model_status()

            logger.info("🗑️ [CLEAR_ALL] clear_all_documents completed")
            return (
                updated_file_list,
                final_status_msg,
                updated_document_library,
                updated_model_status,
            )

        except Exception as e:
            logger.error(f"❌ [CLEAR_ALL] Error clearing documents: {e}", exc_info=True)
            return (
                self._utility_builder.format_file_list(),
                f"❌ Error clearing documents: {e!s}",
                self._library_builder.get_document_library_html(),
                self._get_model_status(),
            )

    def refresh_file_list(self) -> str:
        """Refresh the file list display.

        Returns:
            Formatted file list HTML
        """
        return self._utility_builder.format_file_list()

    def handle_search(self, search_query: str) -> str:
        """Handle document search functionality.

        Args:
            search_query: Search query string

        Returns:
            Filtered content HTML
        """
        filtered_content, status_msg = self._library_builder.filter_documents(
            search_query, "all"
        )
        return filtered_content

    def handle_filter(self, filter_type: str, search_query: str = "") -> str:
        """Handle document filtering functionality.

        Args:
            filter_type: Type of filter to apply
            search_query: Optional search query

        Returns:
            Filtered content HTML
        """
        filtered_content, status_msg = self._library_builder.filter_documents(
            search_query, filter_type.lower()
        )
        return filtered_content

    def handle_filter_with_scroll(
        self, search_query: str, filter_type: str, current_filter: str
    ) -> tuple[str, str, str, str]:
        """Handle filtering with scrolling support and toggle-off functionality.

        Args:
            search_query: Search query string
            filter_type: Type of filter to apply
            current_filter: Currently active filter

        Returns:
            Tuple of (content, status_message, new_filter_type, search_query)
        """
        if filter_type == current_filter:
            # Same button clicked - toggle OFF (clear the display)
            empty_content = """<div style='text-align: center; color: #666; padding: 20px;'>
                <div>📁 No documents currently displayed</div>
                <div style='font-size: 12px; margin-top: 8px; color: #888;'>
                    To view documents: Ensure "📚 Document Library Actions" section in the sidebar is expanded, then click a filter button (All, PDF, Excel, etc.)
                </div>
            </div>"""
            return empty_content, "", "", search_query  # Clear filter state
        else:
            # Different button - normal filter behavior
            content, status_msg = self._library_builder.filter_documents(
                search_query, filter_type
            )
            return content, status_msg, filter_type, search_query

    def sync_sidebar_with_main(self) -> str:
        """Synchronize sidebar with main document management.

        Returns:
            Updated document library HTML
        """
        return self._library_builder.get_document_library_html()

    def show_folder_path_input(self):
        """Show folder path input for server-side folder ingestion.

        Returns:
            Gradio update objects
        """
        import gradio as gr

        return gr.update(visible=True), gr.update(visible=True)

    # Filter button factory methods for event binding
    def create_filter_all_handler(self):
        """Create filter handler for 'all' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "all", current_filter
        )

    def create_filter_pdf_handler(self):
        """Create filter handler for 'pdf' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "pdf", current_filter
        )

    def create_filter_excel_handler(self):
        """Create filter handler for 'excel' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "excel", current_filter
        )

    def create_filter_word_handler(self):
        """Create filter handler for 'word' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "word", current_filter
        )

    def create_filter_recent_handler(self):
        """Create filter handler for 'recent' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "recent", current_filter
        )

    def create_filter_analyzed_handler(self):
        """Create filter handler for 'analyzed' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "analyzed", current_filter
        )

    def create_filter_updated_handler(self):
        """Create filter handler for 'updated' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "updated", current_filter
        )

    def create_filter_other_handler(self):
        """Create filter handler for 'other' filter."""
        return lambda search_query, current_filter: self.handle_filter_with_scroll(
            search_query, "other", current_filter
        )

    def remove_selected_documents(
        self, selected_files: list
    ) -> tuple[str, str, str, str]:
        """Remove selected documents with confirmation and error handling.

        Args:
            selected_files: List of selected file names to remove

        Returns:
            Tuple of (file_list, status_message, document_library, model_status)
        """
        logger.info(
            f"🗑️ [BACKEND] remove_selected_documents called with {len(selected_files)} files"
        )
        logger.info(f"🗑️ [BACKEND] Selected files: {selected_files}")

        try:
            if not selected_files:
                logger.warning("🗑️ [BACKEND] No files selected for removal")
                return (
                    self._utility_builder.format_file_list(),
                    "ℹ️ No files selected for removal",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            # Get all ingested documents
            ingested_docs = self._ingest_service.list_ingested()
            logger.info(
                f"🗑️ [BACKEND] Found {len(ingested_docs)} total ingested documents"
            )

            if not ingested_docs:
                logger.warning("🗑️ [BACKEND] No documents available to remove")
                return (
                    self._utility_builder.format_file_list(),
                    "ℹ️ No documents available to remove",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            # Find documents that match selected file names
            docs_to_delete = []
            logger.info(
                "🗑️ [BACKEND] Searching for documents matching selected files..."
            )

            for doc in ingested_docs:
                if doc.doc_metadata and doc.doc_metadata.get("file_name"):
                    file_name = doc.doc_metadata.get("file_name")
                    if file_name in selected_files:
                        docs_to_delete.append(doc)
                        logger.info(
                            f"🗑️ [BACKEND] Found document to delete: {file_name} (ID: {doc.doc_id})"
                        )
                else:
                    logger.debug(
                        f"🗑️ [BACKEND] Skipping document {doc.doc_id} - no metadata or file_name"
                    )

            logger.info(f"🗑️ [BACKEND] Found {len(docs_to_delete)} documents to delete")

            if not docs_to_delete:
                logger.warning(
                    "🗑️ [BACKEND] None of the selected files found in database"
                )
                return (
                    self._utility_builder.format_file_list(),
                    f"⚠️ None of the selected files found in database: {', '.join(selected_files)}",
                    self._library_builder.get_document_library_html(),
                    self._get_model_status(),
                )

            # Delete selected documents
            failed_deletions = []
            successful_deletions = []

            logger.info("🗑️ [BACKEND] Starting deletion process...")
            for doc in docs_to_delete:
                try:
                    logger.info(
                        f"🗑️ [BACKEND] Attempting to delete document ID: {doc.doc_id}"
                    )

                    # Use facade if available to ensure cache is cleared
                    if self._document_facade:
                        logger.debug(
                            "🗑️ [BACKEND] Using document facade for deletion (with cache clear)"
                        )
                        self._document_facade.delete_document(doc.doc_id)
                    else:
                        logger.debug(
                            "🗑️ [BACKEND] Using direct ingest service (no cache clear)"
                        )
                        self._ingest_service.delete(doc.doc_id)

                    file_name = doc.doc_metadata.get("file_name", doc.doc_id)
                    successful_deletions.append(file_name)
                    logger.info(
                        f"✅ [BACKEND] Successfully deleted document: {file_name}"
                    )
                except Exception as e:
                    file_name = (
                        doc.doc_metadata.get("file_name", doc.doc_id)
                        if doc.doc_metadata
                        else doc.doc_id
                    )
                    failed_deletions.append(file_name)
                    logger.error(
                        f"❌ [BACKEND] Failed to delete document {file_name}: {e}"
                    )

            logger.info(
                f"🗑️ [BACKEND] Deletion complete. Success: {len(successful_deletions)}, Failed: {len(failed_deletions)}"
            )

            # Verify deletion by checking remaining documents
            remaining_docs = self._ingest_service.list_ingested()
            logger.info(
                f"🗑️ [BACKEND] After deletion: {len(remaining_docs)} documents remain"
            )

            # Check if any of the supposedly deleted files are still present
            remaining_files = []
            for doc in remaining_docs:
                if doc.doc_metadata and doc.doc_metadata.get("file_name"):
                    file_name = doc.doc_metadata.get("file_name")
                    if file_name in selected_files:
                        remaining_files.append(file_name)
                        logger.warning(
                            f"⚠️ [BACKEND] File still present after deletion: {file_name}"
                        )

            if remaining_files:
                logger.error(
                    f"❌ [BACKEND] PERSISTENCE ISSUE: {len(remaining_files)} files still present: {remaining_files}"
                )

            # Prepare status message
            if failed_deletions:
                status_msg = f"⚠️ Removed {len(successful_deletions)} files. Failed to remove: {', '.join(failed_deletions)}"
            else:
                status_msg = f"✅ Successfully removed {len(successful_deletions)} selected files"

            # Only show warning if files actually remain after deletion (real persistence issue)
            if remaining_files and not failed_deletions:
                status_msg += f" ⚠️ Warning: {len(remaining_files)} files were not deleted successfully."
                logger.error(f"❌ [BACKEND] Real persistence issue: {remaining_files}")

            # Update UI components
            logger.info("🗑️ [BACKEND] Updating UI components...")
            updated_model_status = self._get_model_status()
            updated_header_html = f"""
                <div style='display: flex; flex-direction: column; gap: 12px;'>
                    <div class='status-indicator'>{updated_model_status}</div>
                </div>
            """

            updated_document_library = self._library_builder.get_document_library_html()
            updated_file_list = self._utility_builder.format_file_list()

            logger.info("🗑️ [BACKEND] remove_selected_documents completed successfully")

            # Add JavaScript to trigger success event and clear selections
            success_script = """
            <script>
            setTimeout(() => {
                console.log('🔄 [JS] Triggering documentOperationSuccess event');
                const event = new CustomEvent('documentOperationSuccess');
                document.dispatchEvent(event);
            }, 100);
            </script>
            """

            # Inject success script into status message for UI cleanup
            final_status_msg = status_msg + success_script

            # Get updated model status after removal
            updated_model_status = self._get_model_status()

            return (
                updated_file_list,
                final_status_msg,
                updated_document_library,
                updated_model_status,
            )

        except Exception as e:
            logger.error(
                f"❌ [BACKEND] Error removing selected documents: {e}", exc_info=True
            )
            return (
                self._utility_builder.format_file_list(),
                f"❌ Error removing documents: {e!s}",
                self._library_builder.get_document_library_html(),
                self._get_model_status(),
            )

    def get_selected_files_from_js(self) -> list:
        """Placeholder for getting selected files from JavaScript.
        This will be replaced with actual integration.

        Returns:
            List of selected file names
        """
        # This will be handled by the JavaScript bridge
        return []

    def process_folder_data(self, folder_data: list) -> tuple[str, str, str]:
        """Process folder data from webkitdirectory selection.

        Args:
            folder_data: List of file data objects from JavaScript

        Returns:
            Tuple of (file_list, status_message, document_library)
        """
        logger.info(
            f"📁 [BACKEND] process_folder_data called with {len(folder_data)} files"
        )

        try:
            if not folder_data:
                return (
                    self._utility_builder.format_file_list(),
                    "ℹ️ No folder data provided",
                    self._library_builder.get_document_library_html(),
                )

            # Extract folder name and file information
            folder_name = (
                folder_data[0]["path"].split("/")[0] if folder_data else "Unknown"
            )
            file_count = len(folder_data)

            logger.info(
                f"📁 [BACKEND] Processing folder: {folder_name} with {file_count} files"
            )

            # For now, we can't directly process File objects from JavaScript in Gradio
            # This would require a more complex file transfer mechanism
            # Instead, provide useful feedback and suggest alternative approaches

            status_msg = f"""
            ✅ Folder '{folder_name}' selected with {file_count} files.

            📝 Current limitation: Direct browser folder upload requires additional implementation.
            💡 Alternative: Use the file upload button to select all files in the folder manually,
               or use the server-side folder ingestion if files are already on the server.
            """

            logger.info(
                f"📁 [BACKEND] Folder selection processed: {folder_name} ({file_count} files)"
            )

            return (
                self._utility_builder.format_file_list(),
                status_msg,
                self._library_builder.get_document_library_html(),
            )

        except Exception as e:
            logger.error(
                f"❌ [BACKEND] Error processing folder data: {e}", exc_info=True
            )
            return (
                self._utility_builder.format_file_list(),
                f"❌ Error processing folder selection: {e!s}",
                self._library_builder.get_document_library_html(),
            )

    def _get_chunk_metadata(self, doc_id: str) -> dict:
        """Get chunk metadata for a specific document.

        Args:
            doc_id: Document ID to get metadata for

        Returns:
            Dictionary with chunk metadata including count, quality, and previews
        """
        try:
            logger.info(f"📊 [CHUNK_META] Getting metadata for doc_id: {doc_id}")

            # Get quality info from ingest service
            quality_info = self._ingest_service.assess_document_quality(doc_id)

            # Get chunk previews from docstore
            chunks_preview = []
            try:
                ref_doc_info = self._ingest_service.storage_context.docstore.get_ref_doc_info(doc_id)
                if ref_doc_info and hasattr(ref_doc_info, 'node_ids'):
                    # Get first 3 chunks for preview
                    for i, node_id in enumerate(ref_doc_info.node_ids[:3]):
                        try:
                            node = self._ingest_service.storage_context.docstore.get_node(node_id)
                            if node and hasattr(node, 'text'):
                                chunks_preview.append({
                                    "index": i + 1,
                                    "id": node_id[:16] + "...",
                                    "text": node.text[:200] + "..." if len(node.text) > 200 else node.text
                                })
                        except Exception as e:
                            logger.warning(f"Could not get node {node_id}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Could not get chunk previews: {e}")

            metadata = {
                "chunk_count": quality_info.get("chunk_count", 0),
                "quality_score": quality_info.get("quality_score", 0),
                "processing_status": quality_info.get("processing_status", "unknown"),
                "error_message": quality_info.get("error_message"),
                "chunks_preview": chunks_preview
            }

            logger.info(f"✅ [CHUNK_META] Retrieved metadata: {metadata['chunk_count']} chunks, quality={metadata['quality_score']}")
            return metadata

        except Exception as e:
            logger.error(f"❌ [CHUNK_META] Error getting chunk metadata: {e}")
            return {
                "chunk_count": 0,
                "quality_score": 0,
                "processing_status": "error",
                "error_message": str(e),
                "chunks_preview": []
            }

    def create_summarize_handler(self):
        """Create handler for document summarization button.

        Returns:
            Handler function that generates document summary
        """
        def summarize_document(doc_id: str) -> str:
            """Generate AI summary for a document.

            Args:
                doc_id: Document ID to summarize

            Returns:
                Summary text to display in chat
            """
            try:
                logger.info(f"📝 [SUMMARIZE] Generating summary for doc_id: {doc_id}")

                if not doc_id:
                    return "⚠️ No document selected for summarization"

                # Get document metadata
                ingested_docs = self._ingest_service.list_ingested()
                doc = next((d for d in ingested_docs if d.doc_id == doc_id), None)

                if not doc:
                    return f"❌ Document not found: {doc_id}"

                filename = doc.doc_metadata.get("file_name", "Unknown") if doc.doc_metadata else "Unknown"

                # Get chunk metadata
                metadata = self._get_chunk_metadata(doc_id)

                if metadata["chunk_count"] == 0:
                    return f"⚠️ Cannot summarize '{filename}': No indexed content found"

                # Generate summary prompt
                summary_prompt = f"""Please provide a comprehensive summary of the document '{filename}' that covers:

1. **Main Topics**: Key themes and subjects discussed
2. **Key Points**: Most important information and findings
3. **Structure**: How the document is organized
4. **Notable Details**: Any significant data, dates, or references

Document has {metadata['chunk_count']} indexed sections. Focus on providing an actionable overview."""

                logger.info(f"✅ [SUMMARIZE] Summary request prepared for '{filename}'")
                return summary_prompt

            except Exception as e:
                logger.error(f"❌ [SUMMARIZE] Error generating summary: {e}")
                return f"❌ Error generating summary: {e!s}"

        return summarize_document

    def create_ask_about_handler(self):
        """Create handler for 'Ask About' document button.

        Returns:
            Handler function that pre-fills chat input
        """
        def ask_about_document(filename: str) -> str:
            """Pre-fill chat input with question about document.

            Args:
                filename: Document filename to ask about

            Returns:
                Pre-filled chat input text
            """
            try:
                logger.info(f"💬 [ASK_ABOUT] Preparing question for: {filename}")

                if not filename:
                    return ""

                # Generate contextual question
                question = f"Tell me about the document '{filename}'. What are the key points and main topics covered?"

                logger.info(f"✅ [ASK_ABOUT] Question prepared for '{filename}'")
                return question

            except Exception as e:
                logger.error(f"❌ [ASK_ABOUT] Error preparing question: {e}")
                return ""

        return ask_about_document

    def create_view_chunks_handler(self):
        """Create handler for 'View Chunks' button.

        Returns:
            Handler function that displays chunk metadata modal
        """
        def view_chunks(doc_id: str) -> str:
            """Display chunk metadata in a modal.

            Args:
                doc_id: Document ID to view chunks for

            Returns:
                HTML modal with chunk metadata
            """
            try:
                logger.info(f"🔍 [VIEW_CHUNKS] Displaying chunks for doc_id: {doc_id}")

                if not doc_id:
                    return "<div style='color: #ff6b6b;'>No document selected</div>"

                # Get document info
                ingested_docs = self._ingest_service.list_ingested()
                doc = next((d for d in ingested_docs if d.doc_id == doc_id), None)

                if not doc:
                    return f"<div style='color: #ff6b6b;'>Document not found: {doc_id}</div>"

                filename = doc.doc_metadata.get("file_name", "Unknown") if doc.doc_metadata else "Unknown"

                # Get chunk metadata
                metadata = self._get_chunk_metadata(doc_id)

                # Build modal HTML
                status_colors = {
                    "indexed": "#10b981",
                    "processing": "#f59e0b",
                    "failed": "#ef4444",
                    "low_quality": "#f97316",
                    "error": "#ef4444"
                }
                status_color = status_colors.get(metadata["processing_status"], "#6b7280")

                modal_html = f"""
                <div style='background: #1e1e2e; border: 2px solid #333; border-radius: 12px; padding: 24px; max-width: 700px; margin: 20px auto;'>
                    <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;'>
                        <h3 style='margin: 0; color: #e0e0e0; font-size: 18px;'>📊 Document Indexing Details</h3>
                    </div>

                    <div style='background: #2a2a3a; border-radius: 8px; padding: 16px; margin-bottom: 20px;'>
                        <div style='color: #888; font-size: 12px; margin-bottom: 4px;'>DOCUMENT</div>
                        <div style='color: #e0e0e0; font-weight: 500;'>{filename}</div>
                    </div>

                    <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;'>
                        <div style='background: #2a2a3a; border-radius: 8px; padding: 12px;'>
                            <div style='color: #888; font-size: 11px; margin-bottom: 4px;'>CHUNKS</div>
                            <div style='color: #e0e0e0; font-size: 20px; font-weight: 600;'>{metadata['chunk_count']}</div>
                        </div>
                        <div style='background: #2a2a3a; border-radius: 8px; padding: 12px;'>
                            <div style='color: #888; font-size: 11px; margin-bottom: 4px;'>QUALITY</div>
                            <div style='color: #e0e0e0; font-size: 20px; font-weight: 600;'>{metadata['quality_score']}%</div>
                        </div>
                        <div style='background: #2a2a3a; border-radius: 8px; padding: 12px;'>
                            <div style='color: #888; font-size: 11px; margin-bottom: 4px;'>STATUS</div>
                            <div style='color: {status_color}; font-size: 14px; font-weight: 600; text-transform: uppercase;'>{metadata['processing_status']}</div>
                        </div>
                    </div>
                """

                # Add error message if present
                if metadata.get("error_message"):
                    modal_html += f"""
                    <div style='background: #3a2a2a; border-left: 4px solid #ef4444; border-radius: 6px; padding: 12px; margin-bottom: 20px;'>
                        <div style='color: #ff6b6b; font-weight: 500; margin-bottom: 4px;'>⚠️ Error</div>
                        <div style='color: #ccc; font-size: 13px;'>{metadata['error_message']}</div>
                    </div>
                    """

                # Add chunk previews
                if metadata["chunks_preview"]:
                    modal_html += """
                    <div style='margin-top: 20px;'>
                        <div style='color: #888; font-size: 12px; margin-bottom: 12px; font-weight: 500;'>CHUNK PREVIEWS</div>
                    """
                    for chunk in metadata["chunks_preview"]:
                        modal_html += f"""
                        <div style='background: #2a2a3a; border-radius: 6px; padding: 12px; margin-bottom: 8px;'>
                            <div style='color: #888; font-size: 11px; margin-bottom: 6px;'>Chunk #{chunk['index']} • ID: {chunk['id']}</div>
                            <div style='color: #ccc; font-size: 13px; line-height: 1.5;'>{chunk['text']}</div>
                        </div>
                        """
                    modal_html += "</div>"

                modal_html += "</div>"

                logger.info(f"✅ [VIEW_CHUNKS] Modal generated for '{filename}'")
                return modal_html

            except Exception as e:
                logger.error(f"❌ [VIEW_CHUNKS] Error displaying chunks: {e}")
                return f"<div style='color: #ff6b6b;'>Error displaying chunks: {e!s}</div>"

        return view_chunks
