"""
Document Utility Builder Component

This module contains utility functions for document management extracted from ui.py
during Phase 1B.1 of the UI refactoring project.

Extracted from ui.py lines:
- _list_ingested_files() (lines 415-455)
- _format_file_list() (lines 457-530)
- _get_file_type() (lines 675-678)
- _get_file_type_icon() (lines 680-683)
- _format_file_size() (lines 685-688)
- _analyze_document_types() (lines 696-700)

Author: UI Refactoring Team
Date: 2024-01-18
Phase: 1B.1 - Document Utility Functions Extraction
"""

import logging
from typing import Any, Optional

from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.ui.utils import (
    get_file_type,
    get_file_type_icon,
    format_file_size,
    analyze_document_types,
    get_category_counts,
)

logger = logging.getLogger(__name__)


class DocumentUtilityBuilder:
    """
    Builder class for document utility functions.
    Provides helper methods for document listing, formatting, and analysis.
    """

    def __init__(
        self, ingest_service: IngestService, chat_service: Optional[ChatService] = None
    ):
        """
        Initialize the DocumentUtilityBuilder.

        Args:
            ingest_service: Service for managing document ingestion
            chat_service: Optional service for chat-related functionality
        """
        self._ingest_service = ingest_service
        self._chat_service = chat_service

    def list_ingested_files(self) -> list[list[str]]:
        """
        List all ingested files with improved error handling and logging.

        This method ensures we're reading from persistent storage, not cache.

        Returns:
            List of file names in format expected by Gradio List component
        """
        logger.info("🔄 [UI_REFRESH] Starting file list refresh from persistent storage")

        files = set()
        total_documents = 0
        skipped_documents = 0

        try:
            # Force fresh read from persistent storage
            logger.info("🔄 [UI_REFRESH] Calling ingest_service.list_ingested() for fresh data")
            ingested_documents = self._ingest_service.list_ingested()
            total_documents = len(ingested_documents)
            logger.info("🔄 [UI_REFRESH] Retrieved %d documents from persistent storage", total_documents)

            for ingested_document in ingested_documents:
                if ingested_document.doc_metadata is None:
                    # Skipping documents without metadata
                    skipped_documents += 1
                    logger.warning(
                        f"Skipping document {ingested_document.doc_id} - no metadata"
                    )
                    continue

                file_name = ingested_document.doc_metadata.get(
                    "file_name", "[FILE NAME MISSING]"
                )

                if file_name == "[FILE NAME MISSING]":
                    logger.warning(
                        f"Document {ingested_document.doc_id} has missing file name"
                    )
                    skipped_documents += 1
                    continue

                files.add(file_name)

            # Log summary for debugging
            unique_files = len(files)
            logger.info(
                f"File listing: {unique_files} unique files from {total_documents} total documents (skipped: {skipped_documents})"
            )

            # Convert to list format expected by Gradio List component
            file_list = [[file_name] for file_name in sorted(files)]
            logger.debug(
                f"Returning file list with {len(file_list)} items for UI display"
            )

            return file_list

        except Exception as e:
            logger.error(f"Error listing ingested files: {e}", exc_info=True)
            return [["[ERROR: Could not load files]"]]

    def format_file_list(self) -> str:
        """
        Format file list as HTML for better display.

        Returns:
            HTML string containing formatted file list
        """
        logger.info("🔄 [UI_REFRESH] Starting format_file_list - reading from persistent storage")

        try:
            files = self.list_ingested_files()
            if not files:
                logger.info("🔄 [UI_REFRESH] No files found in persistent storage")
                return "<div class='file-list-container'><div style='text-align: center; color: #888; padding: 20px;'>No documents uploaded yet</div></div>"

            logger.info("🔄 [UI_REFRESH] Found %d unique files, getting metadata...", len(files))

            # Get metadata for enhanced display - ensure fresh read
            doc_metadata = {}
            ingested_documents = self._ingest_service.list_ingested()
            logger.info("🔄 [UI_REFRESH] Retrieved %d documents for metadata processing", len(ingested_documents))

            for ingested_document in ingested_documents:
                if (
                    ingested_document.doc_metadata
                    and ingested_document.doc_metadata.get("file_name")
                ):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        "size": ingested_document.doc_metadata.get("file_size", 0),
                        "created": ingested_document.doc_metadata.get(
                            "creation_date", ""
                        ),
                        "type": self.get_file_type(file_name),
                    }

            html_content = "<div class='file-list-container'>"
            # Get inventory for segment count
            try:
                if self._chat_service:
                    inventory = self._chat_service.get_system_inventory()
                    segment_count = inventory.get("total_documents", 0)
                    file_count = len(files)
                    header_text = f"📁 Uploaded Files ({file_count}) • 📄 Segments ({segment_count})"
                else:
                    header_text = f"📁 Uploaded Files ({len(files)})"
            except Exception:
                header_text = f"📁 Uploaded Files ({len(files)})"

            html_content += f"<div style='padding: 8px; font-weight: bold; border-bottom: 2px solid #0077BE; color: #0077BE; margin-bottom: 8px;'>{header_text}</div>"

            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_meta = doc_metadata.get(file_name, {})
                    file_type = file_meta.get("type", "other")
                    type_icon = self.get_file_type_icon(file_type)

                    # Format file size
                    file_size = file_meta.get("size", 0)
                    if file_size > 0:
                        if file_size >= 1024 * 1024:  # MB
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                        elif file_size >= 1024:  # KB
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size} B"
                    else:
                        size_str = "Unknown size"

                    # Format creation date
                    created_date = file_meta.get("created", "")
                    if created_date and isinstance(created_date, str):
                        date_str = (
                            created_date[:10]
                            if len(created_date) > 10
                            else created_date
                        )
                    else:
                        date_str = "Unknown date"

                    # Create unique ID for each file item
                    file_id = f"file-{hash(file_name) % 10000:04d}"

                    html_content += f"""
                    <div class='file-item' data-filename='{file_name}' id='{file_id}'
                         style='padding: 10px; border-bottom: 1px solid #333; color: #e0e0e0; display: flex; justify-content: space-between; align-items: center; cursor: pointer; transition: background-color 0.2s;'
                         onclick='toggleFileSelection("{file_name}", "{file_id}")'>
                        <div style='display: flex; align-items: center; flex: 1;'>
                            <input type='checkbox' class='file-checkbox' data-filename='{file_name}'
                                   style='margin-right: 10px; transform: scale(1.2);'
                                   onclick='event.stopPropagation(); handleCheckboxClick("{file_name}", this.checked);'>
                            <span style='font-size: 16px; margin-right: 8px;'>{type_icon}</span>
                            <span style='font-weight: 500;'>{file_name}</span>
                        </div>
                        <div style='text-align: right; font-size: 12px; color: #888; line-height: 1.3;'>
                            <div>{size_str}</div>
                            <div>{date_str}</div>
                        </div>
                    </div>
                    """

            # Close the file list container
            # JavaScript for file selection is now loaded globally in the page head
            html_content += """
            </div>
            """
            return html_content
        except Exception as e:
            logger.error(f"Error formatting file list: {e}")
            return "<div class='file-list-container'><div style='color: #ff6b6b; padding: 20px;'>Error loading files</div></div>"

    def get_file_type(self, filename: str) -> str:
        """
        Get file type from filename.

        Args:
            filename: Name of the file

        Returns:
            File type as string
        """
        return get_file_type(filename)

    def get_file_type_icon(self, file_type: str) -> str:
        """
        Get emoji icon for file type.

        Args:
            file_type: Type of the file

        Returns:
            Emoji icon as string
        """
        return get_file_type_icon(file_type)

    def format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        return format_file_size(size_bytes)

    def analyze_document_types(self) -> dict:
        """
        Analyze document types and return counts for cybersecurity-focused categories.

        Returns:
            Dictionary with document type analysis
        """
        files = self.list_ingested_files()
        return analyze_document_types(files)

    def get_category_counts(self) -> dict:
        """
        Get document counts by category for display.

        Returns:
            Dictionary with category counts
        """
        files = self.list_ingested_files()
        return get_category_counts(files)
