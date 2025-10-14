"""Complex display functions for advanced UI components."""

from typing import Optional, Any
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ComplexDisplayBuilder:
    """Builder class for complex display formatting functions."""

    def __init__(self, ingest_service=None, doc_utility_builder=None):
        """Initialize the ComplexDisplayBuilder with required services."""
        self._ingest_service = ingest_service
        self._doc_utility_builder = doc_utility_builder

    def get_recent_documents_html(self) -> str:
        """Generate HTML for recent documents with enhanced metadata."""
        try:
            if not self._ingest_service:
                return "<div style='color: #ff6b6b; padding: 20px;'>Ingest service not available</div>"

            # Get all ingested documents
            ingested_documents = list(self._ingest_service.list_ingested())
            if not ingested_documents:
                return "<div style='text-align: center; color: #666; padding: 20px;'>No recent documents</div>"

            # Get document metadata for enhanced recent documents
            doc_metadata = {}
            ingested_docs = []
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
                        "hash": ingested_document.doc_metadata.get("content_hash", ""),
                        "type": self._get_file_type(file_name),
                        "doc_id": ingested_document.doc_id,
                    }
                    ingested_docs.append(
                        (
                            file_name,
                            ingested_document.doc_metadata.get("creation_date", ""),
                        )
                    )

            # Sort by creation date (most recent first)
            ingested_docs.sort(key=lambda x: x[1], reverse=True)
            recent_files = [doc[0] for doc in ingested_docs[:8]]  # Show 8 most recent

            html_content = ""
            for file_name in recent_files:
                file_meta = doc_metadata.get(file_name, {})
                file_type = file_meta.get("type", "other")
                type_icon = self._get_file_type_icon(file_type)

                # Format creation date
                created_date = file_meta.get("created", "")
                if created_date:
                    try:
                        # Try to format the date nicely
                        if isinstance(created_date, str) and created_date:
                            date_str = (
                                created_date[:10]
                                if len(created_date) > 10
                                else created_date
                            )
                        else:
                            date_str = "Recently"
                    except Exception:
                        date_str = "Recently"
                else:
                    date_str = "Recently"

                html_content += f"""
                <div class='document-item recent-doc-item' data-filename='{file_name}' data-type='{file_type}' 
                     onclick='selectDocument(this)'>
                    <span class='document-icon'>{type_icon}</span>
                    <div style='flex: 1; min-width: 0;'>
                        <div style='font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{file_name}</div>
                        <div style='font-size: 11px; color: #888; margin-top: 2px;'>
                            {file_type.upper()} • {self._format_file_size(file_meta.get('size', 0))} • {date_str}
                        </div>
                    </div>
                    <div class='document-actions' style='margin-left: 8px; flex-shrink: 0;'>
                        <button class='doc-action-btn' onclick='event.stopPropagation(); analyzeDocument("{file_name}")' 
                                title='Quick Analyze'>🔍</button>
                        <button class='doc-action-btn' onclick='event.stopPropagation(); shareDocument("{file_name}")' 
                                title='Share'>📤</button>
                    </div>
                </div>
                """

            # Add a "View All Documents" link
            total_docs = len(ingested_documents)
            if total_docs > 8:
                html_content += f"""
                <div style='text-align: center; margin-top: 12px; padding-top: 8px; border-top: 1px solid #333;'>
                    <button onclick='expandDocumentLibrary()' 
                            style='background: transparent; border: 1px solid #0077BE; color: #0077BE; 
                                   padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;'>
                        View All {total_docs} Documents
                    </button>
                </div>
                """

            return html_content
        except Exception as e:
            logger.error(f"Error generating recent documents: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error loading recent documents</div>"

    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename."""
        if self._doc_utility_builder:
            return self._doc_utility_builder.get_file_type(filename)

        # Fallback implementation
        suffix = Path(filename).suffix.lower()
        if suffix in [".pdf"]:
            return "pdf"
        elif suffix in [".doc", ".docx"]:
            return "word"
        elif suffix in [".xls", ".xlsx"]:
            return "excel"
        elif suffix in [".ppt", ".pptx"]:
            return "powerpoint"
        elif suffix in [".txt", ".md"]:
            return "text"
        elif suffix in [".py", ".js", ".html", ".css", ".java"]:
            return "code"
        else:
            return "other"

    def _get_file_type_icon(self, file_type: str) -> str:
        """Get emoji icon for file type."""
        if self._doc_utility_builder:
            return self._doc_utility_builder.get_file_type_icon(file_type)

        # Fallback implementation
        icons = {
            "pdf": "PDF",
            "word": "DOC",
            "excel": "XLS",
            "powerpoint": "PPT",
            "text": "TXT",
            "code": "CODE",
            "other": "FILE",
        }
        return icons.get(file_type, "FILE")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if self._doc_utility_builder:
            return self._doc_utility_builder.format_file_size(size_bytes)

        # Fallback implementation
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
