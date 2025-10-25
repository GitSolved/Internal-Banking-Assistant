"""Document State Manager Component

This module contains document state management, metadata handling, and status tracking
functions extracted from ui.py during Phase 1B.4 of the UI refactoring project.

Extracted from ui.py lines:
- _get_model_info() (lines 373-429)
- _get_processing_queue_html() (lines 473-582)
- get_document_count() (lines 5919-5982)
- get_feed_count() (lines 6086-6093)
- get_model_status() (lines 6095-6107)
- _analyze_document_types() (lines 5984-6084)

Author: UI Refactoring Team
Date: 2024-01-18
Phase: 1B.4 - Document State Management Extraction
"""

import logging
from datetime import datetime
from typing import Any

from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.ui.components.documents.document_events import (
    DocumentEventHandlerBuilder,
)
from internal_assistant.ui.components.documents.document_library import (
    DocumentLibraryBuilder,
)
from internal_assistant.ui.components.documents.document_utility import (
    DocumentUtilityBuilder,
)

logger = logging.getLogger(__name__)


class DocumentStateManager:
    """Manager class for document state, metadata, and status tracking.
    Provides centralized state management for document-related operations.
    """

    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService | None,
        feeds_service: RSSFeedService,
        utility_builder: DocumentUtilityBuilder,
        library_builder: DocumentLibraryBuilder,
        event_builder: DocumentEventHandlerBuilder,
    ):
        """Initialize the DocumentStateManager.

        Args:
            ingest_service: Service for managing document ingestion
            chat_service: Service for chat-related functionality
            feeds_service: Service for RSS feeds management
            utility_builder: DocumentUtilityBuilder from Phase 1B.1
            library_builder: DocumentLibraryBuilder from Phase 1B.2
            event_builder: DocumentEventHandlerBuilder from Phase 1B.3
        """
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._feeds_service = feeds_service
        self._utility_builder = utility_builder
        self._library_builder = library_builder
        self._event_builder = event_builder

        # Document state tracking
        self._document_state = {}
        self._processing_status = {}

    def get_model_info(self) -> dict[str, str]:
        """Get information about the current LLM and embedding models.

        Returns:
            Dictionary containing model information
        """
        from internal_assistant.settings.settings import settings

        model_info = {"llm_model": "Unknown", "embedding_model": "Unknown"}

        try:
            # Get LLM model info
            if settings().llm.mode == "llamacpp":
                model_file = getattr(
                    settings().llamacpp, "llm_hf_model_file", "Unknown"
                )
                # Extract model name from filename
                if "foundation-sec" in model_file.lower():
                    model_info["llm_model"] = "Foundation-Sec-8B"
                elif "llama" in model_file.lower():
                    model_info["llm_model"] = "Llama"
                elif "phi" in model_file.lower():
                    model_info["llm_model"] = "Phi-3-Mini"
                else:
                    model_info["llm_model"] = model_file.split(".")[0][
                        :15
                    ]  # First 15 chars
            elif settings().llm.mode == "ollama":
                model_info["llm_model"] = (
                    f"Ollama-{getattr(settings().ollama, 'llm_model', 'Unknown')}"
                )
            elif settings().llm.mode == "openai":
                model_info["llm_model"] = (
                    f"OpenAI-{getattr(settings().openai, 'model', 'Unknown')}"
                )
            elif settings().llm.mode == "sagemaker":
                model_info["llm_model"] = (
                    f"SageMaker-{getattr(settings().sagemaker, 'llm_endpoint_name', 'Unknown')}"
                )
            elif settings().llm.mode == "gemini":
                model_info["llm_model"] = (
                    f"Gemini-{getattr(settings().gemini, 'model', 'Unknown')}"
                )
            elif settings().llm.mode == "mock":
                model_info["llm_model"] = "Mock-LLM"
            else:
                model_info["llm_model"] = f"{settings().llm.mode.title()}-Unknown"

            # Get embedding model info
            if settings().embedding.mode == "huggingface":
                embed_model = getattr(
                    settings().huggingface, "embedding_hf_model_name", "Unknown"
                )
                if "nomic" in embed_model.lower():
                    model_info["embedding_model"] = "Nomic-Embed"
                elif "bge" in embed_model.lower():
                    model_info["embedding_model"] = "BGE-Large"
                else:
                    model_info["embedding_model"] = embed_model.split("/")[-1][
                        :15
                    ]  # Last part, first 15 chars
            elif settings().embedding.mode == "ollama":
                model_info["embedding_model"] = (
                    f"Ollama-{getattr(settings().ollama, 'embedding_model', 'Unknown')}"
                )
            elif settings().embedding.mode == "openai":
                model_info["embedding_model"] = (
                    f"OpenAI-{getattr(settings().openai, 'embedding_model', 'Unknown')}"
                )
            elif settings().embedding.mode == "sagemaker":
                model_info["embedding_model"] = (
                    f"SageMaker-{getattr(settings().sagemaker, 'embedding_endpoint_name', 'Unknown')}"
                )
            elif settings().embedding.mode == "mock":
                model_info["embedding_model"] = "Mock-Embedding"
            else:
                model_info["embedding_model"] = (
                    f"{settings().embedding.mode.title()}-Unknown"
                )

        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            model_info["llm_model"] = (
                f"{getattr(settings().llm, 'mode', 'Unknown')}-Error"
            )
            model_info["embedding_model"] = (
                f"{getattr(settings().embedding, 'mode', 'Unknown')}-Error"
            )

        return model_info

    def get_processing_queue_html(self) -> str:
        """Generate HTML for processing queue with actual document processing status and stages.

        Returns:
            HTML string for processing queue display
        """
        try:
            queue_items = []

            # Get actual ingested documents and their processing status
            ingested_docs = self._ingest_service.list_ingested()
            files = self._utility_builder.list_ingested_files()

            if files and len(files) > 0:
                # Get document metadata to determine processing stages
                doc_metadata = {}
                for ingested_document in ingested_docs:
                    if (
                        ingested_document.doc_metadata
                        and ingested_document.doc_metadata.get("file_name")
                    ):
                        file_name = ingested_document.doc_metadata["file_name"]
                        doc_metadata[file_name] = {
                            "doc_id": ingested_document.doc_id,
                            "size": ingested_document.doc_metadata.get("file_size", 0),
                            "blocks": (
                                len(
                                    ingested_document.doc_metadata.get(
                                        "document_blocks", []
                                    )
                                )
                                if ingested_document.doc_metadata.get("document_blocks")
                                else 0
                            ),
                        }

                # Process last 5 files to show in queue
                recent_files = files[-5:] if len(files) >= 5 else files

                for i, file_row in enumerate(recent_files):
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_type = self._utility_builder.get_file_type(file_name)
                        type_icon = self._utility_builder.get_file_type_icon(file_type)

                        # Determine actual processing status based on ingestion data
                        if file_name in doc_metadata:
                            doc_info = doc_metadata[file_name]
                            blocks_count = doc_info.get("blocks", 0)

                            if blocks_count > 0:
                                status = "completed"
                                status_text = f"✅ Analyzed ({blocks_count} blocks)"
                                stage = "Vector embedding completed"
                            else:
                                status = "processing"
                                status_text = "🔄 Processing"
                                stage = "Text extraction in progress"
                        else:
                            # File uploaded but not yet ingested
                            status = "uploading"
                            status_text = "📤 Uploaded"
                            stage = "Queued for analysis"

                        queue_items.append(
                            {
                                "name": file_name,
                                "icon": type_icon,
                                "status": status,
                                "status_text": status_text,
                                "stage": stage,
                                "type": file_type,
                            }
                        )

            if not queue_items:
                return """
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div style='font-size: 18px; margin-bottom: 8px;'>📭</div>
                    <div>No documents in processing queue</div>
                    <div style='font-size: 12px; margin-top: 4px;'>Upload documents to see processing status</div>
                </div>
                """

            html_content = "<div style='space-y: 8px;'>"
            for item in queue_items:
                # Status color coding
                status_color = (
                    "#28a745"
                    if item["status"] == "completed"
                    else "#ffc107" if item["status"] == "processing" else "#6c757d"
                )

                html_content += f"""
                <div class='queue-item' style='display: flex; flex-direction: column; padding: 12px; margin: 8px 0; background: #000000; border-radius: 8px; border-left: 3px solid {status_color};'>
                    <div style='display: flex; justify-content: between; align-items: center; margin-bottom: 4px;'>
                        <div style='display: flex; align-items: center; flex: 1;'>
                            <span style='font-size: 16px; margin-right: 8px;'>{item['icon']}</span>
                            <span style='color: #e0e0e0; font-weight: 500; flex: 1;'>{item['name']}</span>
                        </div>
                        <span style='color: {status_color}; font-size: 12px; font-weight: 600; text-transform: uppercase;'>{item['type']}</span>
                    </div>
                    <div style='display: flex; justify-content: between; align-items: center;'>
                        <span style='color: {status_color}; font-size: 12px; font-weight: 500;'>{item['status_text']}</span>
                        <span style='color: #888; font-size: 11px; font-style: italic;'>{item['stage']}</span>
                    </div>
                </div>
                """

            # Add queue summary
            completed_count = sum(
                1 for item in queue_items if item["status"] == "completed"
            )
            processing_count = sum(
                1 for item in queue_items if item["status"] == "processing"
            )
            total_count = len(queue_items)

            html_content += f"""
            <div style='text-align: center; color: #666; font-size: 12px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #333;'>
                <div style='margin-bottom: 4px;'><strong>Queue Status:</strong> {total_count} total documents</div>
                <div style='display: flex; justify-content: center; gap: 16px; font-size: 11px;'>
                    <span style='color: #28a745;'>✅ {completed_count} completed</span>
                    <span style='color: #ffc107;'>🔄 {processing_count} processing</span>
                    <span style='color: #6c757d;'>📤 {total_count - completed_count - processing_count} queued</span>
                </div>
            </div>
            """

            html_content += "</div>"
            return html_content

        except Exception as e:
            logger.error(f"Error generating processing queue: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error loading processing queue</div>"

    def get_document_count(self) -> int:
        """Get the total count of ingested documents with categorization.

        Returns:
            Total number of unique documents
        """
        try:
            files = set()
            category_counts = {
                "security_compliance": 0,
                "policy_governance": 0,
                "threat_intelligence": 0,
                "incident_response": 0,
                "technical_infrastructure": 0,
                "research_analysis": 0,
            }

            ingested_documents = self._ingest_service.list_ingested()

            for ingested_document in ingested_documents:
                if (
                    ingested_document.doc_metadata
                    and ingested_document.doc_metadata.get("file_name")
                    and ingested_document.doc_metadata.get("file_name")
                    != "[FILE NAME MISSING]"
                ):
                    file_name = ingested_document.doc_metadata["file_name"]
                    files.add(file_name)

                    # Categorize for detailed counting using cybersecurity-focused categories
                    file_name_lower = file_name.lower()
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
                        category_counts["security_compliance"] += 1
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
                        ]
                    ):
                        category_counts["policy_governance"] += 1
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
                        category_counts["threat_intelligence"] += 1
                    elif any(
                        term in file_name_lower
                        for term in [
                            "incident response",
                            "forensics",
                            "investigation",
                            "breach",
                            "attack",
                            "compromise",
                            "intrusion",
                            "data breach",
                            "containment",
                            "eradication",
                        ]
                    ):
                        category_counts["incident_response"] += 1
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
                        ]
                    ):
                        category_counts["technical_infrastructure"] += 1
                    else:
                        category_counts["research_analysis"] += 1

            total_count = len(files)
            logger.info(
                f"Document counts: Total={total_count}, Security&Compliance={category_counts['security_compliance']}, "
                f"Policy&Governance={category_counts['policy_governance']}, ThreatIntelligence={category_counts['threat_intelligence']}, "
                f"IncidentResponse={category_counts['incident_response']}, TechnicalInfrastructure={category_counts['technical_infrastructure']}, "
                f"ResearchAnalysis={category_counts['research_analysis']}"
            )
            return total_count
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0

    def get_feed_count(self) -> int:
        """Get the count of configured feed sources.

        Returns:
            Number of configured RSS feed sources
        """
        try:
            # Show the number of configured feed sources (not cached items)
            # This reflects the actual feeds available in the system
            return len(self._feeds_service.FEED_SOURCES)
        except Exception as e:
            logger.error(f"Error getting feed count: {e}")
            return 0

    def get_model_status(self) -> str:
        """Get formatted model status HTML including document and feed counts.

        Returns:
            HTML string with model status information
        """
        models = self.get_model_info()
        doc_count = self.get_document_count()
        feed_count = self.get_feed_count()

        return (
            f"<div style='font-size: 18px; color: #e0e0e0; font-weight: 400; font-family: inherit; text-align: left;'>"
            f"📄 {doc_count} Documents<br>"
            f"📰 {feed_count} Feeds<br>"
            f"🤖 {models['llm_model']}<br>"
            f"🔍 {models['embedding_model']}<br>"
            f"</div>"
        )

    def analyze_document_types(self) -> dict[str, Any]:
        """Analyze uploaded documents to provide model recommendations.

        Returns:
            Dictionary containing document analysis results
        """
        try:
            files = self._utility_builder.list_ingested_files()
            if not files:
                return {
                    "total_files": 0,
                    "type_counts": {},
                    "has_financial": False,
                    "has_technical": False,
                    "has_legal": False,
                    "has_research": False,
                }

            # Analyze document content and types
            type_counts = {}
            has_financial = False
            has_technical = False
            has_legal = False
            has_research = False

            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0].lower()
                    file_type = self._utility_builder.get_file_type(file_name)

                    # Count file types
                    type_counts[file_type] = type_counts.get(file_type, 0) + 1

                    # Detect content categories
                    if any(
                        term in file_name
                        for term in ["financial", "budget", "cost", "revenue", "profit"]
                    ):
                        has_financial = True
                    if any(
                        term in file_name
                        for term in [
                            "technical",
                            "api",
                            "code",
                            "system",
                            "architecture",
                        ]
                    ):
                        has_technical = True
                    if any(
                        term in file_name
                        for term in [
                            "legal",
                            "contract",
                            "agreement",
                            "policy",
                            "compliance",
                        ]
                    ):
                        has_legal = True
                    if any(
                        term in file_name
                        for term in [
                            "research",
                            "analysis",
                            "study",
                            "report",
                            "findings",
                        ]
                    ):
                        has_research = True

            return {
                "total_files": len(files),
                "type_counts": type_counts,
                "has_financial": has_financial,
                "has_technical": has_technical,
                "has_legal": has_legal,
                "has_research": has_research,
            }
        except Exception as e:
            logger.error(f"Error analyzing document types: {e}")
            return {
                "total_files": 0,
                "type_counts": {},
                "has_financial": False,
                "has_technical": False,
                "has_legal": False,
                "has_research": False,
            }

    def update_document_state(self, doc_id: str, state: dict[str, Any]) -> None:
        """Update the state of a specific document.

        Args:
            doc_id: Document identifier
            state: State information to update
        """
        if doc_id not in self._document_state:
            self._document_state[doc_id] = {}

        self._document_state[doc_id].update(state)
        logger.debug(f"Updated state for document {doc_id}: {state}")

    def get_document_metadata(self, doc_id: str) -> dict[str, Any]:
        """Get metadata for a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            Document metadata dictionary
        """
        try:
            ingested_docs = self._ingest_service.list_ingested()
            for doc in ingested_docs:
                if doc.doc_id == doc_id:
                    return doc.doc_metadata or {}
        except Exception as e:
            logger.error(f"Error getting metadata for document {doc_id}: {e}")

        return {}

    def track_document_usage(self, doc_id: str, usage_type: str) -> None:
        """Track usage of a specific document.

        Args:
            doc_id: Document identifier
            usage_type: Type of usage (e.g., 'chat_reference', 'search', 'view')
        """
        current_state = self._document_state.get(doc_id, {})
        usage_history = current_state.get("usage_history", [])

        usage_history.append(
            {"type": usage_type, "timestamp": datetime.now().isoformat()}
        )

        self.update_document_state(
            doc_id,
            {
                "usage_history": usage_history,
                "last_used": datetime.now().isoformat(),
                "usage_count": len(usage_history),
            },
        )

    def get_document_status(self, doc_id: str) -> str:
        """Get the current status of a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            Document status string
        """
        metadata = self.get_document_metadata(doc_id)
        if not metadata:
            return "unknown"

        # Check if document has been processed
        doc_blocks = metadata.get("document_blocks", [])
        if doc_blocks and len(doc_blocks) > 0:
            return "processed"
        elif metadata.get("file_name"):
            return "uploaded"
        else:
            return "error"

    def sync_document_state(self) -> None:
        """Synchronize document state with the underlying services.
        """
        try:
            # Refresh document state from ingest service
            ingested_docs = self._ingest_service.list_ingested()

            for doc in ingested_docs:
                if doc.doc_id not in self._document_state:
                    self._document_state[doc.doc_id] = {
                        "created": datetime.now().isoformat(),
                        "status": self.get_document_status(doc.doc_id),
                    }

            logger.debug(
                f"Synchronized state for {len(self._document_state)} documents"
            )
        except Exception as e:
            logger.error(f"Error synchronizing document state: {e}")

    def get_state_summary(self) -> dict[str, Any]:
        """Get a summary of the current document state.

        Returns:
            Dictionary containing state summary information
        """
        return {
            "total_documents": self.get_document_count(),
            "total_feeds": self.get_feed_count(),
            "tracked_documents": len(self._document_state),
            "model_info": self.get_model_info(),
            "document_analysis": self.analyze_document_types(),
        }
