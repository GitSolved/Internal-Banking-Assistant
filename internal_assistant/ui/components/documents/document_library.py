"""Document Library Builder Component

This module contains document library management, filtering, and categorization functions
extracted from ui.py during Phase 1B.2 of the UI refactoring project.

Extracted from ui.py lines:
- _get_document_library_html() (lines 430-571)
- _get_chat_mentioned_documents() (lines 704-731)
- _filter_documents() (lines 733-851)
- _generate_filtered_document_html() (lines 853-900)
- _get_document_counts() (lines 902-972)

Author: UI Refactoring Team
Date: 2024-01-18
Phase: 1B.2 - Document Library Management Extraction
"""

import datetime
import logging

from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.ui.components.documents.document_utility import (
    DocumentUtilityBuilder,
)

logger = logging.getLogger(__name__)


class DocumentLibraryBuilder:
    """Builder class for document library management.
    Handles document display, filtering, categorization, and HTML generation.
    """

    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService | None,
        utility_builder: DocumentUtilityBuilder,
    ):
        """Initialize the DocumentLibraryBuilder.

        Args:
            ingest_service: Service for managing document ingestion
            chat_service: Service for chat-related functionality
            utility_builder: DocumentUtilityBuilder from Phase 1B.1
        """
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._utility_builder = utility_builder

    def get_document_library_html(
        self, search_query: str = "", filter_tags: list = None
    ) -> str:
        """Generate HTML for document library with enhanced folder structure, search, and filtering.

        Args:
            search_query: Search query string
            filter_tags: Optional list of filter tags

        Returns:
            HTML string for document library display
        """
        try:
            files = self._utility_builder.list_ingested_files()
            if not files:
                return """
                <div style='margin-bottom: 16px;'>
                    <input type='text' id='doc-search' placeholder='🔍 Search documents...' 
                           style='width: 100%; padding: 8px 12px; background: #232526; border: 2px solid #333; 
                                  border-radius: 6px; color: #e0e0e0; font-size: 14px;'
                           onkeyup='filterDocuments()' />
                </div>
                <div style='text-align: center; color: #666; padding: 20px;'>📁 No documents yet</div>
                """

            # Enhanced categorization system with cybersecurity focus
            folders = {
                "🔒 Security & Compliance": [],
                "📋 Policy & Governance": [],
                "🕵️ Threat Intelligence": [],
                "🚨 Incident Response": [],
                "🔧 Technical & Infrastructure": [],
                "📊 Research & Analysis": [],
            }

            # Get document metadata for enhanced categorization
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
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
                        "type": self._utility_builder.get_file_type(file_name),
                    }

            # Enhanced file categorization logic
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_name_lower = file_name.lower()

                    # Security & Compliance
                    if any(
                        term in file_name_lower
                        for term in [
                            "security assessment",
                            "security audit",
                            "compliance audit",
                            "vulnerability assessment",
                            "penetration test",
                            "security scan",
                            "risk assessment",
                            "security review",
                            "compliance",
                            "regulatory",
                            "certification",
                            "iso",
                            "soc",
                            "pci",
                            "dss",
                            "gdpr",
                            "sox",
                        ]
                    ):
                        folders["🔒 Security & Compliance"].append(file_name)

                    # Policy & Governance
                    elif any(
                        term in file_name_lower
                        for term in [
                            "policy",
                            "procedure",
                            "guideline",
                            "manual",
                            "handbook",
                            "protocol",
                            "standard",
                            "regulation",
                            "code of conduct",
                            "governance",
                            "framework",
                            "baseline",
                            "control",
                            "requirement",
                            "specification",
                        ]
                    ):
                        folders["📋 Policy & Governance"].append(file_name)

                    # Threat Intelligence
                    elif any(
                        term in file_name_lower
                        for term in [
                            "threat intelligence",
                            "ioc",
                            "malware",
                            "apt",
                            "campaign",
                            "cve",
                            "exploit",
                            "mitre",
                            "att&ck",
                            "ttp",
                            "indicator",
                            "signature",
                            "yara",
                            "stix",
                            "taxii",
                            "threat",
                            "attack",
                            "vulnerability",
                            "ransomware",
                            "phishing",
                        ]
                    ):
                        folders["🕵️ Threat Intelligence"].append(file_name)

                    # Incident Response
                    elif any(
                        term in file_name_lower
                        for term in [
                            "incident response",
                            "forensics",
                            "investigation",
                            "breach",
                            "attack",
                            "incident",
                            "compromise",
                            "intrusion",
                            "data breach",
                            "containment",
                            "eradication",
                        ]
                    ):
                        folders["🚨 Incident Response"].append(file_name)

                    # Technical & Infrastructure
                    elif any(
                        term in file_name_lower
                        for term in [
                            "technical",
                            "architecture",
                            "design",
                            "api",
                            "database",
                            "system",
                            "infrastructure",
                            "code",
                            "development",
                            "software",
                            "hardware",
                            "network",
                            "blueprint",
                            "diagram",
                            "topology",
                            "schema",
                            "protocol",
                            "interface",
                        ]
                    ):
                        folders["🔧 Technical & Infrastructure"].append(file_name)

                    # Research & Analysis (default category)
                    else:
                        folders["📊 Research & Analysis"].append(file_name)

            # Document content will be managed by Gradio components
            html_content = ""

            # Generate folder structure with enhanced file information
            for folder_name, folder_files in folders.items():
                if folder_files:
                    html_content += f"""
                    <div class='document-item folder-item' onclick='toggleFolder(this)' data-folder='{folder_name}'>
                        <span class='document-icon'>📁</span>
                        <span>{folder_name} ({len(folder_files)})</span>
                        <span class='collapsible-icon'>▼</span>
                    </div>
                    <div class='folder-content' style='margin-left: 20px; display: none;'>
                    """

                    # Sort files by most recent first
                    sorted_files = sorted(folder_files, reverse=True)

                    for file_name in sorted_files[:15]:  # Show max 15 files per folder
                        file_type = self._utility_builder.get_file_type(file_name)
                        file_meta = doc_metadata.get(file_name, {})

                        # File type icon
                        type_icon = self._utility_builder.get_file_type_icon(file_type)

                        html_content += f"""
                        <div class='document-item' data-filename='{file_name}' data-type='{file_type}' 
                             onclick='selectDocument(this)'>
                            <span class='document-icon'>{type_icon}</span>
                            <div style='flex: 1;'>
                                <div style='font-weight: 500;'>{file_name}</div>
                                <div style='font-size: 11px; color: #888; margin-top: 2px;'>
                                    {file_type.upper()} • {self._utility_builder.format_file_size(file_meta.get('size', 0))}
                                </div>
                            </div>
                            <div class='document-actions' style='margin-left: 8px;'>
                                <button class='doc-action-btn' onclick='event.stopPropagation(); analyzeDocument("{file_name}")' 
                                        title='Analyze Document'>🔍</button>
                            </div>
                        </div>
                        """

                    if len(folder_files) > 15:
                        html_content += f"<div style='color: #666; font-size: 12px; padding: 4px 0; text-align: center;'>... and {len(folder_files) - 15} more documents</div>"
                    html_content += "</div>"

            return html_content
        except KeyError as e:
            logger.error(
                f"KeyError in document library generation - missing folder key: {e}"
            )
            return "<div style='color: #ff6b6b; padding: 20px;'>Error: Document categorization failed</div>"
        except AttributeError as e:
            logger.error(
                f"AttributeError in document library generation - invalid object access: {e}"
            )
            return "<div style='color: #ff6b6b; padding: 20px;'>Error: Document metadata issue</div>"
        except Exception as e:
            logger.error(
                f"Unexpected error generating document library: {type(e).__name__}: {e}"
            )
            return "<div style='color: #ff6b6b; padding: 20px;'>Error loading document library</div>"

    def get_chat_mentioned_documents(self) -> set:
        """Get set of documents that have been mentioned/referenced in chat conversations.

        Returns:
            Set of document names that have been mentioned in chat
        """
        mentioned_docs = set()

        try:
            # Get recent chat history and extract document references
            # For now, we'll simulate by checking if documents exist and have been processed
            files = self._utility_builder.list_ingested_files()
            ingested_docs = self._ingest_service.list_ingested()

            # Documents are considered "analyzed" (mentioned in chat) if they have content blocks
            # This simulates the concept of documents being referenced in conversations
            for ingested_document in ingested_docs:
                if (
                    ingested_document.doc_metadata
                    and ingested_document.doc_metadata.get("file_name")
                ):
                    file_name = ingested_document.doc_metadata["file_name"]
                    # Check if document has been processed with content blocks (indicating chat usage)
                    doc_blocks = ingested_document.doc_metadata.get(
                        "document_blocks", []
                    )
                    if doc_blocks and len(doc_blocks) > 0:
                        # Simulate chat mention detection - in reality this would check chat history
                        # for references to this document name or content
                        mentioned_docs.add(file_name)

        except Exception as e:
            logger.error(f"Error getting chat mentioned documents: {e}")

        return mentioned_docs

    def filter_documents(
        self, search_query: str = "", filter_type: str = "all"
    ) -> tuple[str, str]:
        """Filter and search documents based on query and type with scrolling.

        Args:
            search_query: Search query string
            filter_type: Type of filter to apply (all, pdf, excel, word, recent, analyzed, updated, other)

        Returns:
            Tuple of (content HTML, status message HTML)
        """
        try:
            files = self._utility_builder.list_ingested_files()
            if not files:
                status_msg = (
                    "No documents available"
                    if filter_type == "all"
                    else f"No {filter_type} files found"
                )
                return (
                    self.get_document_library_html(search_query, [filter_type]),
                    f"<div style='color: #888; font-style: italic; padding: 8px;'>{status_msg}</div>",
                )

            # Get document metadata for filtering
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
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
                        "type": self._utility_builder.get_file_type(file_name),
                    }

            # Get chat-mentioned documents (truly analyzed documents)
            analyzed_files = self.get_chat_mentioned_documents()

            # Filter documents based on filter type
            filtered_files = []
            status_message = ""

            if filter_type == "all":
                filtered_files = files
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing all documents ({len(files)} total)</div>"

            elif filter_type == "pdf":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        if file_meta.get("type", "other") == "pdf":
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing PDF files uploaded ({len(filtered_files)} found)</div>"

            elif filter_type == "excel":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        if file_meta.get("type", "other") == "excel":
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing Excel files uploaded ({len(filtered_files)} found)</div>"

            elif filter_type == "word":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        if file_meta.get("type", "other") == "word":
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing Word files uploaded ({len(filtered_files)} found)</div>"

            elif filter_type == "recent":
                # Show last 10 uploaded documents
                filtered_files = files[-10:] if len(files) >= 10 else files
                filtered_files.reverse()  # Show most recent first
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing recent documents ({len(filtered_files)} found)</div>"

            elif filter_type == "analyzed":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        if file_name in analyzed_files:
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing analyzed documents ({len(filtered_files)} found)</div>"

            elif filter_type == "updated":
                # Show documents modified in the last 7 days
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        created_str = file_meta.get("created", "")
                        if created_str:
                            try:
                                # Parse the creation date and check if it's within last 7 days
                                created_date = datetime.datetime.fromisoformat(
                                    created_str.replace("Z", "+00:00")
                                )
                                if created_date.replace(tzinfo=None) >= seven_days_ago:
                                    filtered_files.append(file_row)
                            except:
                                pass  # Skip if date parsing fails
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing recently updated documents ({len(filtered_files)} found)</div>"

            elif filter_type == "other":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        file_type = file_meta.get("type", "other")
                        if file_type not in ["pdf", "excel", "word"]:
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing other file types ({len(filtered_files)} found)</div>"

            # Apply search filter if provided
            if search_query:
                search_filtered = []
                for file_row in filtered_files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        if search_query.lower() in file_name.lower():
                            search_filtered.append(file_row)
                filtered_files = search_filtered
                if search_query:
                    status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Search results for '{search_query}' ({len(filtered_files)} found)</div>"

            # Generate filtered document library HTML with scrolling (show all documents)
            content = self.generate_filtered_document_html(filtered_files, doc_metadata)
            return content, status_message

        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return (
                "<div style='color: #ff6b6b; padding: 20px;'>Error filtering documents</div>",
                "",
            )

    def generate_filtered_document_html(
        self, filtered_files: list, doc_metadata: dict
    ) -> str:
        """Generate HTML for filtered document list with scrolling functionality.

        Args:
            filtered_files: List of filtered file entries
            doc_metadata: Dictionary of document metadata

        Returns:
            HTML string for filtered document display
        """
        if not filtered_files:
            return "<div style='text-align: center; color: #666; padding: 20px;'>📁 No documents match the current filter</div>"

        # Wrap in scrollable container to show all documents
        html_content = (
            "<div style='max-height: 600px; overflow-y: auto; padding-right: 8px;'>"
        )
        for file_row in filtered_files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_meta = doc_metadata.get(file_name, {})
                file_type = file_meta.get("type", "other")
                file_size = file_meta.get("size", 0)
                created_date = file_meta.get("created", "")

                # Format file size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size/(1024*1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size/1024:.1f} KB"
                else:
                    size_str = f"{file_size} B"

                # Get file type icon
                type_icon = "📄"
                if file_type == "pdf":
                    type_icon = "📕"
                elif file_type == "excel":
                    type_icon = "📊"
                elif file_type == "word":
                    type_icon = "📝"

                html_content += f"""
                <div class='document-item' style='display: flex; align-items: center; padding: 12px; margin: 8px 0; background: #000000; border-radius: 8px; border-left: 3px solid #0077BE;'>
                    <div style='font-size: 20px; margin-right: 12px;'>{type_icon}</div>
                    <div style='flex: 1;'>
                        <div style='color: #e0e0e0; font-weight: 500; margin-bottom: 4px;'>{file_name}</div>
                        <div style='color: #888; font-size: 12px;'>
                            <span style='margin-right: 16px;'>📏 {size_str}</span>
                            {f"<span>📅 {created_date}</span>" if created_date else ""}
                        </div>
                    </div>
                    <div style='color: #0077BE; font-size: 12px; text-transform: uppercase; font-weight: 600;'>{file_type}</div>
                </div>
                """

        html_content += "</div>"  # Close scrollable container
        return html_content

    def get_document_counts(self) -> dict[str, int]:
        """Get counts of documents for each filter type.

        Returns:
            Dictionary with document counts for each filter category
        """
        try:
            files = self._utility_builder.list_ingested_files()
            if not files:
                return {
                    "all": 0,
                    "pdf": 0,
                    "excel": 0,
                    "word": 0,
                    "other": 0,
                    "recent": 0,
                    "updated": 0,
                    "analyzed": 0,
                }

            # Get document metadata for filtering
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
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
                        "type": self._utility_builder.get_file_type(file_name),
                    }

            # Get analyzed documents
            analyzed_files = self.get_chat_mentioned_documents()

            # Count each type
            counts = {
                "all": len(files),
                "pdf": 0,
                "excel": 0,
                "word": 0,
                "other": 0,
                "recent": min(10, len(files)),  # Show last 10
                "updated": 0,
                "analyzed": len(analyzed_files),
            }

            # Count by file type
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)

            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_meta = doc_metadata.get(file_name, {})
                    file_type = file_meta.get("type", "other")

                    # Count by type
                    if file_type == "pdf":
                        counts["pdf"] += 1
                    elif file_type == "excel":
                        counts["excel"] += 1
                    elif file_type == "word":
                        counts["word"] += 1
                    else:
                        counts["other"] += 1

                    # Count updated (within 7 days)
                    created_str = file_meta.get("created", "")
                    if created_str:
                        try:
                            created_date = datetime.datetime.fromisoformat(
                                created_str.replace("Z", "+00:00")
                            )
                            if created_date.replace(tzinfo=None) >= seven_days_ago:
                                counts["updated"] += 1
                        except:
                            pass

            return counts

        except Exception as e:
            logger.error(f"Error getting document counts: {e}")
            return {
                "all": 0,
                "pdf": 0,
                "excel": 0,
                "word": 0,
                "other": 0,
                "recent": 0,
                "updated": 0,
                "analyzed": 0,
            }
