"""This file should be imported if and only if you want to run the UI locally."""

import logging
import re
import time
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import gradio as gr  # type: ignore
from fastapi import FastAPI
from gradio.themes.utils.colors import slate  # type: ignore
from injector import inject, singleton
from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.types import TokenGen
from pydantic import BaseModel, ConfigDict

from internal_assistant.constants import PROJECT_ROOT_PATH
from internal_assistant.di import global_injector
from internal_assistant.open_ai.extensions.context_filter import ContextFilter
from internal_assistant.server.chat.chat_service import ChatService, CompletionGen
from internal_assistant.server.chunks.chunks_service import Chunk, ChunksService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.recipes.summarize.summarize_service import SummarizeService
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.settings.settings import settings
from internal_assistant.ui.ui_strings import (
    UI_TAB_TITLE, CHAT_HEADER, UPLOAD_BUTTON, DELETE_BUTTON, DELETE_ALL_BUTTON, SEARCH_ALL_BUTTON,
    SIDEBAR_UPLOAD, SIDEBAR_MODE, SIDEBAR_ADVANCED
)

logger = logging.getLogger(__name__)

THIS_DIRECTORY_RELATIVE = Path(__file__).parent.relative_to(PROJECT_ROOT_PATH)
# Should be "internal_assistant/ui/avatar-bot.ico"
AVATAR_BOT = THIS_DIRECTORY_RELATIVE / "avatar-bot.ico"
# Internal Assistant logo
INTERNAL_LOGO = THIS_DIRECTORY_RELATIVE / "alpine-logo.png"

# UI_TAB_TITLE now imported from ui_strings.py
SOURCES_SEPARATOR = "<hr>Sources: \n"


class Modes(str, Enum):
    DOCUMENT_ASSISTANT = "RAG Mode"
    GENERAL_ASSISTANT = "General LLM"
    
    # Deprecated modes for backward compatibility - will map to new modes
    RAG_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SEARCH_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    COMPARE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SUMMARIZE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    DIRECT_CHAT = "General LLM"  # Maps to GENERAL_ASSISTANT


MODES: list[Modes] = [
    Modes.DOCUMENT_ASSISTANT,
    Modes.GENERAL_ASSISTANT,
]

# Backward compatibility mapping
LEGACY_MODE_MAPPING = {
    "Document Assistant": Modes.DOCUMENT_ASSISTANT.value,
    "Document Search": Modes.DOCUMENT_ASSISTANT.value,
    "Document Compare": Modes.DOCUMENT_ASSISTANT.value,
    "Document Summary": Modes.DOCUMENT_ASSISTANT.value,
    "General Assistant": Modes.GENERAL_ASSISTANT.value,
    "RAG": Modes.DOCUMENT_ASSISTANT.value,
    "SEARCH": Modes.DOCUMENT_ASSISTANT.value,
    "COMPARE": Modes.DOCUMENT_ASSISTANT.value,
    "SUMMARIZE": Modes.DOCUMENT_ASSISTANT.value,
    "DIRECT": Modes.GENERAL_ASSISTANT.value,
}


def normalize_mode(mode: str) -> str:
    """
    Normalize any mode string to one of the two supported modes.
    Provides backward compatibility for legacy mode names.
    """
    if mode in LEGACY_MODE_MAPPING:
        return LEGACY_MODE_MAPPING[mode]
    
    # Direct enum value check
    if mode == Modes.DOCUMENT_ASSISTANT.value:
        return Modes.DOCUMENT_ASSISTANT.value
    elif mode == Modes.GENERAL_ASSISTANT.value:
        return Modes.GENERAL_ASSISTANT.value
    
    # Default to RAG Mode since this is a RAG system
    return Modes.DOCUMENT_ASSISTANT.value


class Source(BaseModel):
    file: str
    page: str
    text: str

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @staticmethod
    def curate_sources(sources: list[Chunk]) -> list["Source"]:
        curated_sources = []

        for chunk in sources:
            doc_metadata = chunk.document.doc_metadata

            file_name = doc_metadata.get("file_name", "-") if doc_metadata else "-"
            page_label = doc_metadata.get("page_label", "-") if doc_metadata else "-"

            source = Source(file=file_name, page=page_label, text=chunk.text)
            curated_sources.append(source)
            curated_sources = list(
                dict.fromkeys(curated_sources).keys()
            )  # Unique sources only

        return curated_sources


@singleton
class InternalAssistantUI:
    
    # Regex patterns have been removed to simplify the interface
    
    @inject
    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService,
        chunks_service: ChunksService,
        summarizeService: SummarizeService,
        feeds_service: RSSFeedService,
    ) -> None:
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._chunks_service = chunks_service
        self._summarize_service = summarizeService
        self._feeds_service = feeds_service

        # Cache the UI blocks
        self._ui_block = None

        # Initialize system prompt based on default mode
        # Map from settings keys to new mode enums with backward compatibility
        default_mode_map = {
            # New mode names
            "DOCUMENT": Modes.DOCUMENT_ASSISTANT,
            "GENERAL": Modes.GENERAL_ASSISTANT,
            # Backward compatibility for old mode names
            "RAG": Modes.DOCUMENT_ASSISTANT,
            "SEARCH": Modes.DOCUMENT_ASSISTANT, 
            "COMPARE": Modes.DOCUMENT_ASSISTANT,
            "SUMMARIZE": Modes.DOCUMENT_ASSISTANT,
            "DIRECT": Modes.GENERAL_ASSISTANT,
            # Full names for flexibility
            "Document Assistant": Modes.DOCUMENT_ASSISTANT,
            "Document Search": Modes.DOCUMENT_ASSISTANT,
            "Document Compare": Modes.DOCUMENT_ASSISTANT,
            "Document Summary": Modes.DOCUMENT_ASSISTANT,
            "General Assistant": Modes.GENERAL_ASSISTANT,
        }
        self._default_mode = default_mode_map.get(
            settings().ui.default_mode, Modes.DOCUMENT_ASSISTANT
        )
        self._system_prompt = self._get_default_system_prompt(self._default_mode)



    def _chat(
        self, message: str, history: list[list[str]], mode: Modes, system_prompt_input, 
        similarity_threshold: float = 0.7, response_temperature: float = 0.1, citation_style: str = "Include Sources", 
        response_length: str = "Medium", *_: Any
    ) -> Any:
        # Validate input to prevent None/empty vectors from breaking vector search
        if not message or message.strip() == "" or message is None:
            yield "Please enter a valid message."
            return
        def yield_deltas(completion_gen: CompletionGen) -> Iterable[str]:
            full_response: str = ""
            stream = completion_gen.response
            for delta in stream:
                if isinstance(delta, str):
                    full_response += str(delta)
                elif isinstance(delta, ChatResponse):
                    full_response += delta.delta or ""
                yield full_response
                time.sleep(0.02)

            # Apply citation style settings for document sources with enhanced correlation
            if completion_gen.sources and citation_style != "Exclude Sources":
                full_response += SOURCES_SEPARATOR
                cur_sources = Source.curate_sources(completion_gen.sources)
                sources_text = "\n\n**📄 Document Sources:**\n\n"
                used_files = set()
                
                for index, source in enumerate(cur_sources, start=1):
                    if f"{source.file}-{source.page}" not in used_files:
                        if citation_style == "Minimal Citations":
                            sources_text = sources_text + f"{index}. {source.file}\n"
                        else:  # Include Sources (full citations)
                            sources_text = (
                                sources_text
                                + f"{index}. {source.file} (page {source.page}) \n\n"
                            )
                        used_files.add(f"{source.file}-{source.page}")
                        
                sources_text += "*Document sources from knowledge base*\n"
                sources_text += "<hr>\n\n"
                full_response += sources_text
            
            
            yield full_response

        def yield_tokens(token_gen: TokenGen) -> Iterable[str]:
            full_response: str = ""
            for token in token_gen:
                full_response += str(token)
                yield full_response

        def build_history() -> list[ChatMessage]:
            history_messages: list[ChatMessage] = []

            for interaction in history:
                history_messages.append(
                    ChatMessage(content=interaction[0], role=MessageRole.USER)
                )
                if len(interaction) > 1 and interaction[1] is not None:
                    history_messages.append(
                        ChatMessage(
                            # Remove from history content the Sources information
                            content=interaction[1].split(SOURCES_SEPARATOR)[0],
                            role=MessageRole.ASSISTANT,
                        )
                    )

            # max 20 messages to try to avoid context overflow
            return history_messages[:20]

        new_message = ChatMessage(content=message, role=MessageRole.USER)
        all_messages = [*build_history(), new_message]
        
        # Use system prompt as-is for better performance
        system_prompt = self._system_prompt or ""
        
        # If a system prompt is set, add it as a system message
        if system_prompt:
            all_messages.insert(
                0,
                ChatMessage(
                    content=system_prompt,
                    role=MessageRole.SYSTEM,
                ),
            )
        
        # Normalize mode to ensure backward compatibility
        normalized_mode = normalize_mode(mode)
        logger.info(f"Processing query in {normalized_mode} mode")
        
        match normalized_mode:
            case Modes.DOCUMENT_ASSISTANT.value:
                # Document Assistant mode - search documents for contextual answers
                try:
                    available_files = self._list_ingested_files()
                    if not available_files or len(available_files) == 0:
                        yield "📄 **Document Assistant Mode - No Documents Available**\n\nI'm in Document Assistant mode but couldn't find any uploaded documents to search. Here's what you can do:\n\n• **📁 Upload Files**: Use the Upload tab to add documents\n• **📂 Upload Folders**: Use the Folder tab to ingest directories\n• **🤖 Switch Mode**: Use General Assistant for questions that don't require documents\n\n**Supported formats**: PDF, Word, Excel, PowerPoint, Text, Markdown, and more\n\nOnce documents are uploaded, I'll search through them to provide contextual answers."
                        return
                except Exception as e:
                    yield f"⚠️ **Document Assistant Mode - Error**\n\nI couldn't access your document library. This might be a temporary issue.\n\n**Try these solutions:**\n• Refresh the page and try again\n• Switch to General Assistant mode for non-document questions\n• Check if your documents are still uploading\n\nIf the problem persists, please contact support."
                    return
                
                context_filter = self._create_context_filter()
                
                query_stream = self._chat_service.stream_chat(
                    messages=all_messages,
                    use_context=True,
                    context_filter=context_filter,
                )
                yield from yield_deltas(query_stream)

            case Modes.GENERAL_ASSISTANT.value:
                # General Assistant mode - direct LLM without document search
                query_stream = self._chat_service.stream_chat(
                    messages=all_messages,
                    use_context=False,  # No document context
                    context_filter=None,
                )
                yield from yield_deltas(query_stream)
                
                

    # On initialization and on mode change, this function set the system prompt
    # to the default prompt based on the mode (and user settings).
    @staticmethod
    def _get_default_system_prompt(mode: Modes) -> str:
        match mode:
            case Modes.DIRECT_CHAT:
                # Foundation-Sec-8B already knows cybersecurity - minimal prompt
                return "Answer questions directly and concisely."

            case Modes.RAG_MODE:
                # Foundation-Sec-8B knows how to analyze security docs - minimal prompt
                return "Use document context to answer questions."

            case Modes.COMPARE_MODE:
                # Foundation-Sec-8B knows how to compare security documents
                return "Compare and analyze the provided documents."

            case Modes.SEARCH_MODE:
                # Foundation-Sec-8B knows how to search security content
                return "Find relevant information from documents."

            case Modes.SUMMARIZE_MODE:
                # Foundation-Sec-8B knows how to summarize security content
                return "Provide concise summaries."

            case _:
                # Default fallback - minimal
                return "Answer directly."

    @staticmethod
    def _get_default_mode_explanation(mode: Modes) -> str:
        match mode:
            case Modes.RAG_MODE:
                return "💬 Ask questions about your uploaded documents with enhanced correlation analysis. Get intelligent answers that draw connections across your entire document collection."
            case Modes.SEARCH_MODE:
                return "🔍 Search through all documents to find specific information, quotes, or references with intelligent cross-document correlation."
            case Modes.COMPARE_MODE:
                return "⚖️ Advanced document correlation analysis. Compare policies, identify patterns, track changes over time, and discover relationships between documents."
            case Modes.SUMMARIZE_MODE:
                return "📄 Generate intelligent summaries that identify themes spanning multiple documents and highlight key correlations and insights."
            case Modes.DIRECT_CHAT:
                return "🧠 General banking assistant for calculations, definitions, and questions that don't require document lookup."
            case _:
                return ""

    def _set_system_prompt(self, system_prompt_input: str) -> None:
        logger.info(f"Setting system prompt to: {system_prompt_input}")
        self._system_prompt = system_prompt_input

    # Removed _analyze_response_and_recommend method - no longer needed for deterministic mode selection

    def _get_model_info(self) -> dict:
        """Get information about the current LLM and embedding models."""
        from internal_assistant.settings.settings import settings
        
        model_info = {
            "llm_model": "Unknown",
            "embedding_model": "Unknown"
        }
        
        try:
            # Get LLM model info
            if settings().llm.mode == "llamacpp":
                model_file = getattr(settings().llamacpp, "llm_hf_model_file", "Unknown")
                # Extract model name from filename
                if "foundation-sec" in model_file.lower():
                    model_info["llm_model"] = "Foundation-Sec-8B"

                elif "llama" in model_file.lower():
                    model_info["llm_model"] = "Llama"
                elif "phi" in model_file.lower():
                    model_info["llm_model"] = "Phi-3-Mini"
                else:
                    model_info["llm_model"] = model_file.split('.')[0][:15]  # First 15 chars
            elif settings().llm.mode == "ollama":
                model_info["llm_model"] = f"Ollama-{getattr(settings().ollama, 'llm_model', 'Unknown')}"
            elif settings().llm.mode == "openai":
                model_info["llm_model"] = f"OpenAI-{getattr(settings().openai, 'model', 'Unknown')}"
            elif settings().llm.mode == "sagemaker":
                model_info["llm_model"] = f"SageMaker-{getattr(settings().sagemaker, 'llm_endpoint_name', 'Unknown')}"
            elif settings().llm.mode == "gemini":
                model_info["llm_model"] = f"Gemini-{getattr(settings().gemini, 'model', 'Unknown')}"
            elif settings().llm.mode == "mock":
                model_info["llm_model"] = "Mock-LLM"
            else:
                model_info["llm_model"] = f"{settings().llm.mode.title()}-Unknown"
            
            # Get embedding model info
            if settings().embedding.mode == "huggingface":
                embed_model = getattr(settings().huggingface, "embedding_hf_model_name", "Unknown")
                if "nomic" in embed_model.lower():
                    model_info["embedding_model"] = "Nomic-Embed"
                elif "bge" in embed_model.lower():
                    model_info["embedding_model"] = "BGE-Large"
                else:
                    model_info["embedding_model"] = embed_model.split('/')[-1][:15]  # Last part, first 15 chars
            elif settings().embedding.mode == "ollama":
                model_info["embedding_model"] = f"Ollama-{getattr(settings().ollama, 'embedding_model', 'Unknown')}"
            elif settings().embedding.mode == "openai":
                model_info["embedding_model"] = f"OpenAI-{getattr(settings().openai, 'embedding_model', 'Unknown')}"
            elif settings().embedding.mode == "sagemaker":
                model_info["embedding_model"] = f"SageMaker-{getattr(settings().sagemaker, 'embedding_endpoint_name', 'Unknown')}"
            elif settings().embedding.mode == "gemini":
                model_info["embedding_model"] = f"Gemini-{getattr(settings().gemini, 'embedding_model', 'Unknown')}"
            elif settings().embedding.mode == "mock":
                model_info["embedding_model"] = "Mock-Embedding"
            else:
                model_info["embedding_model"] = f"{settings().embedding.mode.title()}-Unknown"
                
        except Exception as e:
            # Log the error but don't crash the UI
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting model info: {e}")
            model_info["llm_model"] = f"{getattr(settings().llm, 'mode', 'Unknown')}-Error"
            model_info["embedding_model"] = f"{getattr(settings().embedding, 'mode', 'Unknown')}-Error"
        
        return model_info

    def _list_ingested_files(self) -> list[list[str]]:
        """List all ingested files with improved error handling and logging."""
        files = set()
        total_documents = 0
        skipped_documents = 0
        
        try:
            ingested_documents = self._ingest_service.list_ingested()
            total_documents = len(ingested_documents)
            
            for ingested_document in ingested_documents:
                if ingested_document.doc_metadata is None:
                    # Skipping documents without metadata
                    skipped_documents += 1
                    logger.warning(f"Skipping document {ingested_document.doc_id} - no metadata")
                    continue
                
                file_name = ingested_document.doc_metadata.get(
                    "file_name", "[FILE NAME MISSING]"
                )
                
                if file_name == "[FILE NAME MISSING]":
                    logger.warning(f"Document {ingested_document.doc_id} has missing file name")
                    skipped_documents += 1
                    continue
                
                files.add(file_name)
            
            # Log summary for debugging
            unique_files = len(files)
            logger.info(f"File listing: {unique_files} unique files from {total_documents} total documents (skipped: {skipped_documents})")
            
            # Convert to list format expected by Gradio List component
            file_list = [[file_name] for file_name in sorted(files)]
            logger.debug(f"Returning file list with {len(file_list)} items for UI display")
            
            return file_list
            
        except Exception as e:
            logger.error(f"Error listing ingested files: {e}", exc_info=True)
            return [["[ERROR: Could not load files]"]]

    def _format_file_list(self) -> str:
        """Format file list as HTML for better display."""
        try:
            files = self._list_ingested_files()
            if not files:
                return "<div class='file-list-container'><div style='text-align: center; color: #888; padding: 20px;'>No documents uploaded yet</div></div>"
            
            # Get metadata for enhanced display
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        'size': ingested_document.doc_metadata.get('file_size', 0),
                        'created': ingested_document.doc_metadata.get('creation_date', ''),
                        'type': self._get_file_type(file_name)
                    }
            
            html_content = "<div class='file-list-container'>"
            # Get inventory for segment count
            try:
                inventory = self._chat_service.get_system_inventory()
                segment_count = inventory.get('total_documents', 0)
                file_count = len(files)
                header_text = f"📁 Uploaded Files ({file_count}) • 📄 Segments ({segment_count})"
            except Exception:
                header_text = f"📁 Uploaded Files ({len(files)})"
            
            html_content += f"<div style='padding: 8px; font-weight: bold; border-bottom: 2px solid #0077BE; color: #0077BE; margin-bottom: 8px;'>{header_text}</div>"
            
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_meta = doc_metadata.get(file_name, {})
                    file_type = file_meta.get('type', 'other')
                    type_icon = self._get_file_type_icon(file_type)
                    
                    # Format file size
                    file_size = file_meta.get('size', 0)
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
                    created_date = file_meta.get('created', '')
                    if created_date and isinstance(created_date, str):
                        date_str = created_date[:10] if len(created_date) > 10 else created_date
                    else:
                        date_str = "Unknown date"
                    
                    html_content += f"""
                    <div style='padding: 10px; border-bottom: 1px solid #333; color: #e0e0e0; display: flex; justify-content: space-between; align-items: center;'>
                        <div style='display: flex; align-items: center; flex: 1;'>
                            <span style='font-size: 16px; margin-right: 8px;'>{type_icon}</span>
                            <span style='font-weight: 500;'>{file_name}</span>
                        </div>
                        <div style='text-align: right; font-size: 12px; color: #888; line-height: 1.3;'>
                            <div>{size_str}</div>
                            <div>{date_str}</div>
                        </div>
                    </div>
                    """
            
            html_content += "</div>"
            return html_content
        except Exception as e:
            logger.error(f"Error formatting file list: {e}")
            return "<div class='file-list-container'><div style='color: #ff6b6b; padding: 20px;'>Error loading files</div></div>"

    def _get_document_library_html(self, search_query: str = "", filter_tags: list = None) -> str:
        """Generate HTML for document library with enhanced folder structure, search, and filtering."""
        try:
            files = self._list_ingested_files()
            if not files:
                return """
                <div style='margin-bottom: 16px;'>
                    <input type='text' id='doc-search' placeholder='🔍 Search documents...' 
                           style='width: 100%; padding: 8px 12px; background: #232526; border: 2px solid #333; 
                                  border-radius: 6px; color: #e0e0e0; font-size: 14px;'
                           onkeyup='filterDocuments()' />
                </div>
                <div class='filter-tags' style='margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 4px;'>
                    <button class='filter-tag' data-filter='all' onclick='toggleFilter(this)'>All</button>
                    <button class='filter-tag' data-filter='pdf' onclick='toggleFilter(this)'>PDF</button>
                    <button class='filter-tag' data-filter='excel' onclick='toggleFilter(this)'>Excel</button>
                    <button class='filter-tag' data-filter='word' onclick='toggleFilter(this)'>Word</button>
                    <button class='filter-tag' data-filter='recent' onclick='toggleFilter(this)'>Recent</button>
                    <button class='filter-tag' data-filter='analyzed' onclick='toggleFilter(this)'>Analyzed</button>
                    <button class='filter-tag' data-filter='pending' onclick='toggleFilter(this)'>Pending</button>
                </div>
                <div style='text-align: center; color: #666; padding: 20px;'>📁 No documents yet</div>
                """
            
            # Enhanced categorization system
            folders = {
                "📋 Security Policies": [],
                "🔍 Threat Intelligence": [],
                "🔒 Compliance & Audit": [],
                "📊 Incident Reports": [],
                "📄 Other Documents": []
            }
            
            # Get document metadata for enhanced categorization
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        'size': ingested_document.doc_metadata.get('file_size', 0),
                        'created': ingested_document.doc_metadata.get('creation_date', ''),
                        'hash': ingested_document.doc_metadata.get('content_hash', ''),
                        'type': self._get_file_type(file_name)
                    }
            
            # Enhanced file categorization logic
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_name_lower = file_name.lower()
                    
                    # Incident Reports
                    if any(term in file_name_lower for term in [
                        'incident', 'breach', 'attack', 'malware', 'phishing', 'ransomware',
                        'alert', 'threat', 'vulnerability', 'exploit', 'response', 'forensics'
                    ]):
                        folders["📊 Incident Reports"].append(file_name)
                    
                    # Security Policies
                    elif any(term in file_name_lower for term in [
                        'policy', 'procedure', 'guideline', 'manual', 'handbook', 
                        'protocol', 'standard', 'regulation', 'code of conduct', 'security'
                    ]):
                        folders["📋 Security Policies"].append(file_name)
                    
                    # Threat Intelligence
                    elif any(term in file_name_lower for term in [
                        'threat', 'intelligence', 'ioc', 'apt', 'malware', 'campaign',
                        'actor', 'group', 'mitre', 'attack', 'tactic', 'technique'
                    ]):
                        folders["🔍 Threat Intelligence"].append(file_name)
                    
                    # Compliance & Audit
                    elif any(term in file_name_lower for term in [
                        'compliance', 'audit', 'risk', 'regulatory', 'legal', 
                        'sox', 'gdpr', 'hipaa', 'iso', 'certification', 'assessment'
                    ]):
                        folders["🔒 Compliance & Audit"].append(file_name)
                    
                    # Other Documents
                    else:
                        folders["📄 Other Documents"].append(file_name)
            
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
                        file_type = self._get_file_type(file_name)
                        file_meta = doc_metadata.get(file_name, {})
                        
                        # File type icon
                        type_icon = self._get_file_type_icon(file_type)
                        
                        html_content += f"""
                        <div class='document-item' data-filename='{file_name}' data-type='{file_type}' 
                             onclick='selectDocument(this)'>
                            <span class='document-icon'>{type_icon}</span>
                            <div style='flex: 1;'>
                                <div style='font-weight: 500;'>{file_name}</div>
                                <div style='font-size: 11px; color: #888; margin-top: 2px;'>
                                    {file_type.upper()} • {self._format_file_size(file_meta.get('size', 0))}
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
            logger.error(f"KeyError in document library generation - missing folder key: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error: Document categorization failed</div>"
        except AttributeError as e:
            logger.error(f"AttributeError in document library generation - invalid object access: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error: Document metadata issue</div>"
        except Exception as e:
            logger.error(f"Unexpected error generating document library: {type(e).__name__}: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error loading document library</div>"

    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename."""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        type_mapping = {
            'pdf': 'pdf',
            'doc': 'word', 'docx': 'word',
            'xls': 'excel', 'xlsx': 'excel', 'csv': 'excel',
        }
        return type_mapping.get(extension, 'other')

    def _get_file_type_icon(self, file_type: str) -> str:
        """Get emoji icon for file type."""
        icon_mapping = {
            'pdf': '📄',
            'word': '📝',
            'excel': '📊',
            'other': '📄'
        }
        return icon_mapping.get(file_type, '📄')

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"

    def _get_category_counts(self) -> dict:
        """Get document counts by category for display."""
        try:
            category_counts = {
                "📊 Financial Reports": 0,
                "📋 Policy Documents": 0,
                "🔍 Compliance": 0,
                "👥 Customer Data": 0
            }
            
            files = self._list_ingested_files()
            
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_name_lower = file_name.lower()
                    
                    # Financial Reports
                    if any(term in file_name_lower for term in [
                        'financial', 'budget', 'expense', 'revenue', 'profit', 'loss', 
                        'income', 'balance', 'cash flow', 'quarterly', 'annual report'
                    ]):
                        category_counts["📊 Financial Reports"] += 1
                    
                    # Policy Documents
                    elif any(term in file_name_lower for term in [
                        'policy', 'procedure', 'guideline', 'manual', 'handbook', 
                        'protocol', 'standard', 'regulation', 'code of conduct'
                    ]):
                        category_counts["📋 Policy Documents"] += 1
                    
                    # Compliance
                    elif any(term in file_name_lower for term in [
                        'compliance', 'audit', 'risk', 'regulatory', 'legal', 
                        'sox', 'gdpr', 'hipaa', 'iso', 'certification'
                    ]):
                        category_counts["🔍 Compliance"] += 1
                    
                    # Customer Data
                    elif any(term in file_name_lower for term in [
                        'customer', 'client', 'contact', 'crm', 'lead', 
                        'prospect', 'account', 'sales', 'marketing'
                    ]):
                        category_counts["👥 Customer Data"] += 1
                    
                    # Skip files that don't match any category
                    else:
                        pass
            
            return category_counts
        except Exception as e:
            logger.error(f"Error getting category counts: {e}")
            return {}

    def _analyze_document_types(self) -> dict:
        """Analyze document types and return counts for Financial, Policy, Compliance, Customer, and Other categories."""
        try:
            # Initialize counters
            type_counts = {
                "Financial": 0,
                "Policy": 0,
                "Compliance": 0,
                "Customer": 0,
                "Other": 0
            }
            
            # Initialize content type flags
            has_financial = False
            has_technical = False
            has_legal = False
            has_research = False
            
            files = self._list_ingested_files()
            total_files = len(files) if files else 0
            
            if total_files == 0:
                return {
                    'total_files': 0,
                    'type_counts': type_counts,
                    'has_financial': False,
                    'has_technical': False,
                    'has_legal': False,
                    'has_research': False
                }
            
            # Analyze each file
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_name_lower = file_name.lower()
                    
                    # Financial Documents
                    if any(term in file_name_lower for term in [
                        'financial', 'budget', 'expense', 'revenue', 'profit', 'loss', 
                        'income', 'balance', 'cash flow', 'quarterly', 'annual report',
                        'investment', 'portfolio', 'trading', 'loan', 'credit', 'debt',
                        'accounting', 'tax', 'audit', 'earnings', 'dividend'
                    ]):
                        type_counts["Financial"] += 1
                        has_financial = True
                    
                    # Policy Documents
                    elif any(term in file_name_lower for term in [
                        'policy', 'procedure', 'guideline', 'manual', 'handbook', 
                        'protocol', 'standard', 'regulation', 'code of conduct',
                        'rules', 'terms', 'conditions', 'agreement', 'contract'
                    ]):
                        type_counts["Policy"] += 1
                        has_legal = True
                    
                    # Compliance Documents
                    elif any(term in file_name_lower for term in [
                        'compliance', 'regulatory', 'legal', 'sox', 'gdpr', 'hipaa', 
                        'iso', 'certification', 'risk', 'governance', 'ethics',
                        'whistleblower', 'aml', 'kyc', 'cdd', 'sanctions'
                    ]):
                        type_counts["Compliance"] += 1
                        has_legal = True
                    
                    # Customer Data
                    elif any(term in file_name_lower for term in [
                        'customer', 'client', 'contact', 'crm', 'lead', 
                        'prospect', 'account', 'sales', 'marketing',
                        'demographic', 'segment', 'persona', 'journey'
                    ]):
                        type_counts["Customer"] += 1
                    
                    # Technical Documents
                    elif any(term in file_name_lower for term in [
                        'technical', 'spec', 'architecture', 'design', 'api',
                        'database', 'system', 'infrastructure', 'code', 'development',
                        'software', 'hardware', 'network', 'security', 'config'
                    ]):
                        type_counts["Other"] += 1
                        has_technical = True
                    
                    # Research Documents
                    elif any(term in file_name_lower for term in [
                        'research', 'analysis', 'study', 'report', 'whitepaper',
                        'survey', 'market', 'trend', 'forecast', 'insight',
                        'data', 'statistics', 'metrics', 'kpi', 'benchmark'
                    ]):
                        type_counts["Other"] += 1
                        has_research = True
                    
                    # Everything else
                    else:
                        type_counts["Other"] += 1
            
            return {
                'total_files': total_files,
                'type_counts': type_counts,
                'has_financial': has_financial,
                'has_technical': has_technical,
                'has_legal': has_legal,
                'has_research': has_research
            }
            
        except Exception as e:
            logger.error(f"Error analyzing document types: {e}")
            return {
                'total_files': 0,
                'type_counts': {
                    "Financial": 0,
                    "Policy": 0,
                    "Compliance": 0,
                    "Customer": 0,
                    "Other": 0
                },
                'has_financial': False,
                'has_technical': False,
                'has_legal': False,
                'has_research': False
            }

    def _get_processing_queue_html(self) -> str:
        """Generate HTML for processing queue with actual document processing status and stages."""
        try:
            queue_items = []
            
            # Get actual ingested documents and their processing status
            ingested_docs = self._ingest_service.list_ingested()
            files = self._list_ingested_files()
            
            if files and len(files) > 0:
                # Get document metadata to determine processing stages
                doc_metadata = {}
                for ingested_document in ingested_docs:
                    if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                        file_name = ingested_document.doc_metadata["file_name"]
                        doc_metadata[file_name] = {
                            'doc_id': ingested_document.doc_id,
                            'size': ingested_document.doc_metadata.get('file_size', 0),
                            'blocks': len(ingested_document.doc_metadata.get('document_blocks', [])) if ingested_document.doc_metadata.get('document_blocks') else 0
                        }
                
                # Process last 5 files to show in queue
                recent_files = files[-5:] if len(files) >= 5 else files
                
                for i, file_row in enumerate(recent_files):
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_type = self._get_file_type(file_name)
                        type_icon = self._get_file_type_icon(file_type)
                        
                        # Determine actual processing status based on ingestion data
                        if file_name in doc_metadata:
                            doc_info = doc_metadata[file_name]
                            blocks_count = doc_info.get('blocks', 0)
                            
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
                        
                        queue_items.append({
                            'name': file_name,
                            'icon': type_icon,
                            'status': status,
                            'status_text': status_text,
                            'stage': stage,
                            'type': file_type
                        })
            
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
                status_color = "#28a745" if item['status'] == "completed" else "#ffc107" if item['status'] == "processing" else "#6c757d"
                
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
            completed_count = sum(1 for item in queue_items if item['status'] == 'completed')
            processing_count = sum(1 for item in queue_items if item['status'] == 'processing')
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

    def _get_chat_mentioned_documents(self) -> set:
        """Get set of documents that have been mentioned/referenced in chat conversations."""
        # This would track documents mentioned in chat - for now we'll simulate this
        # In a real implementation, this would parse chat history for document references
        mentioned_docs = set()
        
        try:
            # Get recent chat history and extract document references
            # For now, we'll simulate by checking if documents exist and have been processed
            files = self._list_ingested_files()
            ingested_docs = self._ingest_service.list_ingested()
            
            # Documents are considered "analyzed" (mentioned in chat) if they have content blocks
            # This simulates the concept of documents being referenced in conversations
            for ingested_document in ingested_docs:
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    # Check if document has been processed with content blocks (indicating chat usage)
                    doc_blocks = ingested_document.doc_metadata.get('document_blocks', [])
                    if doc_blocks and len(doc_blocks) > 0:
                        # Simulate chat mention detection - in reality this would check chat history
                        # for references to this document name or content
                        mentioned_docs.add(file_name)
            
        except Exception as e:
            logger.error(f"Error getting chat mentioned documents: {e}")
        
        return mentioned_docs

    # Classification methods have been removed to simplify the interface
    # - _intelligent_mode_detection()
    # - _get_smart_system_prompt()
    # - _test_intelligent_routing()
    # 
    # The system now uses the user's selected mode directly without any automatic switching

    def _filter_documents(self, search_query: str = "", filter_type: str = "all") -> tuple[str, str]:
        """Filter and search documents based on query and type with scrolling. Returns (content, status_message)."""
        try:
            files = self._list_ingested_files()
            if not files:
                status_msg = "No documents available" if filter_type == "all" else f"No {filter_type} files found"
                return self._get_document_library_html(search_query, [filter_type]), f"<div style='color: #888; font-style: italic; padding: 8px;'>{status_msg}</div>"
            
            # Get document metadata for filtering
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        'size': ingested_document.doc_metadata.get('file_size', 0),
                        'created': ingested_document.doc_metadata.get('creation_date', ''),
                        'type': self._get_file_type(file_name)
                    }
            
            # Get chat-mentioned documents (truly analyzed documents)
            analyzed_files = self._get_chat_mentioned_documents()
            
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
                        if file_meta.get('type', 'other') == 'pdf':
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing PDF files uploaded ({len(filtered_files)} found)</div>"
            
            elif filter_type == "excel":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        if file_meta.get('type', 'other') == 'excel':
                            filtered_files.append(file_row)
                status_message = f"<div style='color: #0077BE; font-weight: 500; padding: 8px;'>Showing Excel files uploaded ({len(filtered_files)} found)</div>"
            
            elif filter_type == "word":
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        if file_meta.get('type', 'other') == 'word':
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
                import datetime
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                for file_row in files:
                    if file_row and len(file_row) > 0:
                        file_name = file_row[0]
                        file_meta = doc_metadata.get(file_name, {})
                        created_str = file_meta.get('created', '')
                        if created_str:
                            try:
                                # Parse the creation date and check if it's within last 7 days
                                created_date = datetime.datetime.fromisoformat(created_str.replace('Z', '+00:00'))
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
                        file_type = file_meta.get('type', 'other')
                        if file_type not in ['pdf', 'excel', 'word']:
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
            content = self._generate_filtered_document_html(filtered_files, doc_metadata)
            return content, status_message
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return "<div style='color: #ff6b6b; padding: 20px;'>Error filtering documents</div>", ""

    def _generate_filtered_document_html(self, filtered_files: list, doc_metadata: dict) -> str:
        """Generate HTML for filtered document list with scrolling functionality."""
        if not filtered_files:
            return "<div style='text-align: center; color: #666; padding: 20px;'>📁 No documents match the current filter</div>"
        
        # Wrap in scrollable container to show all documents
        html_content = "<div style='max-height: 600px; overflow-y: auto; padding-right: 8px;'>"
        for file_row in filtered_files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_meta = doc_metadata.get(file_name, {})
                file_type = file_meta.get('type', 'other')
                file_size = file_meta.get('size', 0)
                created_date = file_meta.get('created', '')
                
                # Format file size
                if file_size > 1024*1024:
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

    def _get_document_counts(self) -> dict[str, int]:
        """Get counts of documents for each filter type."""
        try:
            files = self._list_ingested_files()
            if not files:
                return {
                    'all': 0, 'pdf': 0, 'excel': 0, 'word': 0, 'other': 0,
                    'recent': 0, 'updated': 0, 'analyzed': 0
                }
            
            # Get document metadata for filtering
            doc_metadata = {}
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        'size': ingested_document.doc_metadata.get('file_size', 0),
                        'created': ingested_document.doc_metadata.get('creation_date', ''),
                        'type': self._get_file_type(file_name)
                    }
            
            # Get analyzed documents
            analyzed_files = self._get_chat_mentioned_documents()
            
            # Count each type
            counts = {
                'all': len(files),
                'pdf': 0, 'excel': 0, 'word': 0, 'other': 0,
                'recent': min(10, len(files)),  # Show last 10
                'updated': 0,
                'analyzed': len(analyzed_files)
            }
            
            # Count by file type
            import datetime
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            
            for file_row in files:
                if file_row and len(file_row) > 0:
                    file_name = file_row[0]
                    file_meta = doc_metadata.get(file_name, {})
                    file_type = file_meta.get('type', 'other')
                    
                    # Count by type
                    if file_type == 'pdf':
                        counts['pdf'] += 1
                    elif file_type == 'excel':
                        counts['excel'] += 1
                    elif file_type == 'word':
                        counts['word'] += 1
                    else:
                        counts['other'] += 1
                    
                    # Count updated (within 7 days)
                    created_str = file_meta.get('created', '')
                    if created_str:
                        try:
                            created_date = datetime.datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            if created_date.replace(tzinfo=None) >= seven_days_ago:
                                counts['updated'] += 1
                        except:
                            pass
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting document counts: {e}")
            return {
                'all': 0, 'pdf': 0, 'excel': 0, 'word': 0, 'other': 0,
                'recent': 0, 'updated': 0, 'analyzed': 0
            }

    def _format_feeds_display(self, source_filter: str = None, days_filter: int = None) -> str:
        """Format RSS feeds for display in the UI."""
        try:
            feeds = self._feeds_service.get_feeds(source_filter, days_filter)
            
            if not feeds:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>📡 No external information available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest regulatory feeds
                        </div>
                    </div>
                </div>"""
            
            html_content = "<div class='feed-content' style='max-height: none; height: auto; overflow-y: auto; overflow-x: auto; padding-right: 8px; scroll-behavior: smooth; min-width: 100%;'>"
            
            # Group feeds by source
            sources = {}
            for feed in feeds:
                source = feed['source']
                if source not in sources:
                    sources[source] = []
                sources[source].append(feed)
            
            # Sort feeds within each source by date (latest first)
            for source in sources:
                sources[source].sort(key=lambda x: x['published'], reverse=True)
            
            for source, source_feeds in sources.items():
                # Source header with color scheme
                # Enhanced source icons for threat intelligence agencies
                source_icons = {
                    # Banking Regulators
                    "Federal Reserve": "🏦",
                    "FDIC": "🏛️", 
                    "OCC": "🏦",
                    "FFIEC": "📋",
                    
                    # Financial Crimes
                    "FinCEN": "💰",
                    "FBI IC3": "🔍",
                    "Secret Service Financial Crimes": "🕵️",
                    
                    # Cybersecurity
                    "US-CERT": "🔒",
                    "NIST": "📊",
                    "DHS": "🏛️",
                    "NSA": "🕵️",
                    
                    # Government & Treasury
                    "Treasury": "💰",
                    
                    # Consumer Protection
                    "CFPB": "🛡️",
                    
                    # Securities & Markets
                    "SEC": "📈",
                    "FINRA": "📋",
                    "NCUA": "🏦",
                }
                source_icon = source_icons.get(source, "📰")
                
                # Get color from feeds service
                source_color = self._feeds_service.SOURCE_COLORS.get(source, "#0077BE")
                
                html_content += f"""
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' data-source='{source}' 
                        style='color: {source_color}; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold; cursor: pointer; transition: all 0.2s;'
                        onmouseover='this.style.textDecoration="underline"; this.style.color="{source_color}"; this.style.opacity="0.8";'
                        onmouseout='this.style.textDecoration="none"; this.style.color="{source_color}"; this.style.opacity="1";'
                        onclick='filterBySource("{source}")'>
                        {source_icon} {source} ({len(source_feeds)} items)
                    </h4>
                """
                
                # Feed items for this source
                for feed in source_feeds[:25]:  # Increased limit for better scrolling experience
                    html_content += f"""
                    <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid {source_color}; background: #f9f9f9; min-width: 400px; white-space: normal; word-wrap: break-word;'>
                        <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                            <a href='javascript:void(0)' onclick='confirmOpenExternal("{feed["link"]}", "{feed["title"]}")' 
                               style='color: {source_color}; text-decoration: none; font-size: 16px;'>
                                {feed["title"][:120]}{'...' if len(feed["title"]) > 120 else ''}
                            </a>
                        </div>
                        <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                            {feed["summary"][:200]}{'...' if len(feed["summary"]) > 200 else ''}
                        </div>
                        <div class='feed-meta' style='font-size: 12px; color: #888;'>
                            📅 {feed["published"]}
                        </div>
                    </div>"""
                
                html_content += "</div>"  # Close source section
            
            html_content += "</div>"  # Close feed content
            
            # Add JavaScript for TermFeed-style confirmation and source filtering
            html_content += """
            <script>
            function confirmOpenExternal(url, title) {
                const confirmed = confirm(`Open external article?\\n\\n"${title}"\\n\\nThis will open in your default browser. Continue?`);
                if (confirmed) {
                    window.open(url, '_blank', 'noopener,noreferrer');
                }
            }
            
            function filterBySource(sourceName) {
                // Find the source filter dropdown in the Gradio interface
                const dropdowns = document.querySelectorAll('label');
                let sourceDropdown = null;
                
                // Find the dropdown by its label
                dropdowns.forEach(label => {
                    if (label.textContent.includes('Source Category')) {
                        const container = label.parentElement;
                        const input = container.querySelector('input');
                        if (input) {
                            sourceDropdown = input;
                        }
                    }
                });
                
                if (sourceDropdown) {
                    // Set the dropdown value to the clicked source
                    sourceDropdown.value = sourceName;
                    
                    // Create and dispatch a change event to trigger Gradio's handler
                    const event = new Event('input', { bubbles: true });
                    sourceDropdown.dispatchEvent(event);
                    
                    // Also dispatch change event for compatibility
                    const changeEvent = new Event('change', { bubbles: true });
                    sourceDropdown.dispatchEvent(changeEvent);
                    
                    // Scroll to top of feed display
                    const feedDisplay = document.querySelector('.file-list-container');
                    if (feedDisplay) {
                        feedDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                    
                    // Visual feedback
                    const header = event.target || window.event.srcElement;
                    if (header) {
                        header.style.color = '#4CAF50';
                        setTimeout(() => {
                            header.style.color = '#0077BE';
                        }, 500);
                    }
                }
            }
            </script>"""
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error formatting feeds display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading external information</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def _format_simple_forum_display(self) -> str:
        """Format forum directory display with beautiful RSS feed-style styling."""
        try:
            # Get ALL forum data with no limits
            forums_data = self._get_simple_forum_data()
            
            if not forums_data:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🌐 No forum directory available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load forum directory
                        </div>
                    </div>
                </div>"""
            
            # Beautiful header matching RSS feed style
            total_count = len(forums_data)
            html_content = f"""<div class='feed-content'>
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' 
                        style='color: #FF6B35; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                        🌐 Tor Taxi ({total_count} forums)
                    </h4>
                </div>
            """
            
            # Display forums with beautiful RSS feed-style formatting
            for forum in forums_data:
                forum_name = forum.get('name', 'Unknown Forum')
                forum_url = forum.get('url', '')
                
                if not forum_url:
                    continue
                
                # Condensed forum item styling - title and link on same line
                html_content += f"""
                <div class='feed-item' style='margin-bottom: 8px; padding: 8px; border-left: 3px solid #FF6B35; background: #f9f9f9;'>
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        <span style='color: #FF6B35; font-weight: bold; font-size: 16px; min-width: 120px;'>
                            🔗 {forum_name}
                        </span>
                        <span style='color: #666; font-family: monospace; font-size: 15px; flex: 1;'>
                            {forum_url}
                        </span>
                    </div>
                </div>"""
            
            html_content += "</div>"
            
            # Removed copy functionality - simplified display
            html_content += ""
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error formatting forum directory: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading forum directory</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""
    
    def _get_simple_forum_data(self) -> list:
        """Get forum data from the forum service or fallback to complete sample data."""
        try:
            # Try to get forum service from dependency injection
            from internal_assistant.di import global_injector
            
            try:
                # Try the simple forum service first
                from internal_assistant.server.feeds.simple_forum_service import SimpleForumDirectoryService
                forum_service = global_injector.get(SimpleForumDirectoryService)
                forums = forum_service.get_forums()
                
                if forums:
                    logger.info(f"Retrieved {len(forums)} forums from SimpleForumDirectoryService")
                    # Convert to the format expected by UI
                    return [
                        {
                            "name": forum.get("name", "Unknown"),
                            "url": forum.get("onion_link", "")
                        }
                        for forum in forums if forum.get("onion_link")
                    ]
                    
            except Exception as e:
                logger.debug(f"SimpleForumDirectoryService not available: {e}")
                
            try:
                # Try the main forum directory service
                from internal_assistant.server.feeds.forum_directory_service import ForumDirectoryService
                forum_service = global_injector.get(ForumDirectoryService)
                forums = forum_service.get_forums()
                
                if forums:
                    logger.info(f"Retrieved {len(forums)} forums from ForumDirectoryService")
                    # Convert ForumLink objects to dict format
                    return [
                        {
                            "name": getattr(forum, 'name', 'Unknown'),
                            "url": getattr(forum, 'onion_link', '') or getattr(forum, 'url', '')
                        }
                        for forum in forums
                    ]
                    
            except Exception as e:
                logger.debug(f"ForumDirectoryService not available: {e}")
                
        except Exception as e:
            logger.warning(f"Could not access forum services: {e}")
        
        # Fallback to complete sample data with ALL known forums
        logger.info("Using fallback forum data with complete forum list")
        return [
            {
                "name": "Dread",
                "url": "dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion"
            },
            {
                "name": "Pitch - 2", 
                "url": "n7vermpu3kwcgz527x265cpkwq4h2jtgynq7qdrvm3erdx7p4ifqd.onion"
            },
            {
                "name": "NZ Darknet Market Forum",
                "url": "nzmarketbf5k4z7b2xcdaovacm3kj2apcpw7yxjqggdwt5q2evtj55oad.onion"
            },
            {
                "name": "Germania",
                "url": "germaniadhqfm5cnqyc7jq7qcklbvdkk5r7nfq6g5whpvkpxhqtb4xd.onion"
            },
            {
                "name": "EndChan",
                "url": "enxx3byspwsdo446jujc52ucy2pf5urdbhqw3kbsfhlfjwmbpj5smdad.onion"
            },
            {
                "name": "XSS.is",
                "url": "xssforever4s7z6ennrfmyfkwq2qmbtmdpbclvfzqqrxzpcaxtpnqmpqad.onion"
            }
        ]

    def _format_cve_display(self, source_filter: str = None, severity_filter: str = "All Severities", vendor_filter: str = "All Vendors") -> str:
        """Format CVE data for display in the UI."""
        try:
            # Get CVE data from feeds service, specifically Microsoft Security
            feeds = self._feeds_service.get_feeds("Microsoft Security", 30)  # Get Microsoft Security feeds specifically
            
            if not feeds:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🔍 No Microsoft Security CVE data available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest Microsoft Security vulnerabilities
                        </div>
                    </div>
                </div>"""
            
            html_content = "<div class='feed-content'>"
            
            # Group feeds by source
            sources = {}
            for feed in feeds:
                source = feed['source']
                if source not in sources:
                    sources[source] = []
                sources[source].append(feed)
            
            for source, source_feeds in sources.items():
                # Only show Microsoft Security for CVE panel
                if source != "Microsoft Security":
                    continue
                
                # Source header with CVE-specific styling
                source_icons = {
                    "Microsoft Security": "🔒",
                }
                source_icon = source_icons.get(source, "🔍")
                
                # Get color from feeds service
                source_color = self._feeds_service.SOURCE_COLORS.get(source, "#0077BE")
                
                html_content += f"""
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' data-source='{source}' 
                        style='color: {source_color}; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                        {source_icon} {source} ({len(source_feeds)} vulnerabilities)
                    </h4>
                </div>
                """
                
                # Feed items for this source
                for feed in source_feeds[:15]:  # Limit to 15 items per source for CVE panel
                    # Extract CVE ID if present in title or summary
                    cve_id = self._extract_cve_id(feed["title"] + " " + feed["summary"])
                    
                    # Determine severity based on content
                    severity = self._determine_cve_severity(feed["title"] + " " + feed["summary"])
                    
                    # Apply filters
                    if severity_filter != "All Severities" and severity != severity_filter:
                        continue
                    
                    if vendor_filter != "All Vendors":
                        if vendor_filter == "Microsoft" and source != "Microsoft Security":
                            continue
                        if vendor_filter == "Banking Systems" and "bank" not in feed["title"].lower() and "financial" not in feed["title"].lower():
                            continue
                        if vendor_filter == "Network Equipment" and not any(term in feed["title"].lower() for term in ["router", "switch", "firewall", "network"]):
                            continue
                    
                    # Severity color coding
                    severity_colors = {
                        "Critical": "#FF0000",
                        "High": "#FF6B35", 
                        "Medium": "#FFA500",
                        "Low": "#FFFF00"
                    }
                    severity_color = severity_colors.get(severity, "#0077BE")
                    
                    html_content += f"""
                    <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid {severity_color}; background: #f9f9f9;'>
                        <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                            <span style='color: {severity_color}; font-size: 14px; font-weight: bold; margin-right: 8px;'>
                                {severity.upper()}
                            </span>
                            <a href='javascript:void(0)' onclick='confirmOpenExternal("{feed["link"]}", "{feed["title"]}")' 
                               style='color: {source_color}; text-decoration: none; font-size: 16px;'>
                                {feed["title"][:80]}{'...' if len(feed["title"]) > 80 else ''}
                            </a>
                        </div>
                        <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                            {feed["summary"][:120]}{'...' if len(feed["summary"]) > 120 else ''}
                        </div>
                        <div class='feed-meta' style='font-size: 12px; color: #888;'>
                            {f'🔍 CVE: {cve_id} • ' if cve_id else ''}📅 {feed["published"]}
                        </div>
                    </div>"""
                
                html_content += "</div>"  # Close source section
            
            html_content += "</div>"  # Close feed content
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error formatting CVE display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading CVE data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def _get_cve_data(self) -> list:
        """Get CVE data from feeds service."""
        try:
            # Get Microsoft Security feeds specifically
            feeds = self._feeds_service.get_feeds("Microsoft Security", 30)
            return feeds or []
        except Exception as e:
            logger.error(f"Error getting CVE data: {e}")
            return []

    def _extract_cve_id(self, text: str) -> str:
        """Extract CVE ID from text."""
        import re
        cve_pattern = r'CVE-\d{4}-\d{4,7}'
        match = re.search(cve_pattern, text)
        return match.group(0) if match else ""

    def _determine_cve_severity(self, text: str) -> str:
        """Determine CVE severity based on text content."""
        text_lower = text.lower()
        
        # Critical indicators
        if any(term in text_lower for term in ["critical", "remote code execution", "rce", "zero-day", "0-day"]):
            return "Critical"
        
        # High indicators
        if any(term in text_lower for term in ["high", "privilege escalation", "authentication bypass", "sql injection"]):
            return "High"
        
        # Medium indicators
        if any(term in text_lower for term in ["medium", "information disclosure", "denial of service", "dos"]):
            return "Medium"
        
        # Default to Low
        return "Low"

    def _format_mitre_display(self, domain_filter: str = "Enterprise", domain_focus: str = "All Domains", 
                             search_query: str = None, tactic_filter: str = "All Tactics", 
                             show_groups: bool = False, banking_focus: bool = False) -> str:
        """Format MITRE ATT&CK data for display in the UI."""
        try:
            # Get MITRE data from API
            mitre_data = self._get_mitre_data()
            
            if not mitre_data:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🛡️ No MITRE ATT&CK data available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest threat intelligence
                        </div>
                    </div>
                </div>"""
            
            html_content = "<div class='feed-content'>"
            
            if show_groups:
                # Display Threat Groups
                groups = mitre_data.get('groups', [])
                if groups:
                    html_content += f"""
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #FF0000; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🎯 {'Banking-Targeting ' if banking_focus else 'All '}Threat Groups ({len(groups)} groups)
                        </h4>
                    </div>
                    """
                    
                    for group in groups[:10]:  # Limit to 10 groups
                        group_name = group.get('name', 'Unknown Group')
                        group_id = group.get('group_id', '')
                        description = group.get('description', 'No description available')
                        techniques = group.get('techniques', [])
                        targets = group.get('targets', [])
                        
                        html_content += f"""
                        <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid #FF0000; background: #f9f9f9;'>
                            <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                                <span style='color: #FF0000; font-size: 14px; font-weight: bold; margin-right: 8px;'>
                                    🕵️ {group_name}
                                </span>
                                <a href='javascript:void(0)' onclick='confirmOpenExternal("{group.get("url", "")}", "{group_name}")' 
                                   style='color: #FF0000; text-decoration: none; font-size: 16px;'>
                                    {group_id}
                                </a>
                            </div>
                            <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                                {description[:120]}{'...' if len(description) > 120 else ''}
                            </div>
                            <div class='feed-meta' style='font-size: 12px; color: #888;'>
                                🔍 Techniques: {len(techniques)} • 🎯 Targets: {', '.join(targets[:3])}{'...' if len(targets) > 3 else ''}
                            </div>
                        </div>"""
                else:
                    html_content += """
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #FF0000; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🎯 No Threat Groups Available
                        </h4>
                    </div>
                    """
            else:
                # Display Techniques
                techniques = mitre_data.get('techniques', [])
                if techniques:
                    # Apply filters
                    filtered_techniques = []
                    for tech in techniques:
                        # Domain focus filter
                        if domain_focus != "All Domains" and tech.get('technique_id') not in self._get_domain_techniques(domain_focus):
                            continue
                        
                        # Search filter
                        if search_query:
                            search_lower = search_query.lower()
                            if not (search_lower in tech.get('name', '').lower() or 
                                   search_lower in tech.get('technique_id', '').lower() or
                                   search_lower in tech.get('description', '').lower()):
                                continue
                        
                        # Tactic filter
                        if tactic_filter != "All Tactics" and tech.get('tactic') != tactic_filter:
                            continue
                        
                        filtered_techniques.append(tech)
                    
                    if filtered_techniques:
                        html_content += f"""
                        <div class='feed-source-section'>
                            <h4 class='feed-source-header' 
                                style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                                🔍 {'Domain-Relevant ' if domain_focus != "All Domains" else 'All '}Techniques ({len(filtered_techniques)} techniques)
                            </h4>
                        </div>
                        """
                        
                        for tech in filtered_techniques[:15]:  # Limit to 15 techniques
                            technique_id = tech.get('technique_id', '')
                            name = tech.get('name', 'Unknown Technique')
                            description = tech.get('description', 'No description available')
                            tactic = tech.get('tactic', 'Unknown Tactic')
                            platforms = tech.get('platforms', [])
                            
                            # Tactic color coding
                            tactic_colors = {
                                "Initial Access": "#FF0000",
                                "Execution": "#FF6B35",
                                "Persistence": "#FFA500",
                                "Privilege Escalation": "#FFFF00",
                                "Defense Evasion": "#00FF00",
                                "Credential Access": "#00FFFF",
                                "Discovery": "#0000FF",
                                "Lateral Movement": "#FF00FF",
                                "Collection": "#800080",
                                "Command & Control": "#008000",
                                "Exfiltration": "#800000",
                                "Impact": "#FF0000"
                            }
                            tactic_color = tactic_colors.get(tactic, "#0077BE")
                            
                            html_content += f"""
                            <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid {tactic_color}; background: #f9f9f9;'>
                                <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                                    <span style='color: {tactic_color}; font-size: 14px; font-weight: bold; margin-right: 8px;'>
                                        🎯 {tactic}
                                    </span>
                                    <a href='javascript:void(0)' onclick='confirmOpenExternal("{tech.get("url", "")}", "{name}")' 
                                       style='color: {tactic_color}; text-decoration: none; font-size: 16px;'>
                                        {technique_id} - {name}
                                    </a>
                                </div>
                                <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                                    {description[:120]}{'...' if len(description) > 120 else ''}
                                </div>
                                <div class='feed-meta' style='font-size: 12px; color: #888;'>
                                    💻 Platforms: {', '.join(platforms[:3])}{'...' if len(platforms) > 3 else ''}
                                </div>
                            </div>"""
                    else:
                        html_content += """
                        <div class='feed-source-section'>
                            <h4 class='feed-source-header' 
                                style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                                🔍 No Techniques Match Filters
                            </h4>
                        </div>
                        """
                else:
                    html_content += """
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🔍 No Techniques Available
                        </h4>
                    </div>
                    """
            
            html_content += "</div>"  # Close feed content
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error formatting MITRE display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading MITRE ATT&CK data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def _get_mitre_data(self) -> dict:
        """Get MITRE ATT&CK data from API."""
        try:
            import aiohttp
            import asyncio
            
            # For now, return sample data since we need async context
            # In a real implementation, this would call the MITRE ATT&CK API
            return {
                'techniques': [
                    # Initial Access Techniques
                    {
                        'technique_id': 'T1078.004',
                        'name': 'Valid Accounts: Cloud Accounts',
                        'description': 'Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.',
                        'tactic': 'Initial Access',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1078/004/'
                    },
                    {
                        'technique_id': 'T1566.001',
                        'name': 'Phishing: Spearphishing Attachment',
                        'description': 'Adversaries may send spearphishing emails with a malicious attachment in an attempt to gain access to victim systems.',
                        'tactic': 'Initial Access',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1566/001/'
                    },
                    {
                        'technique_id': 'T1190',
                        'name': 'Exploit Public-Facing Application',
                        'description': 'Adversaries may attempt to take advantage of a weakness in an Internet-facing computer system or program.',
                        'tactic': 'Initial Access',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1190/'
                    },
                    # Execution Techniques
                    {
                        'technique_id': 'T1059.001',
                        'name': 'Command and Scripting Interpreter: PowerShell',
                        'description': 'Adversaries may abuse PowerShell commands and scripts for execution. PowerShell is a powerful interactive command-line interface and scripting environment.',
                        'tactic': 'Execution',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1059/001/'
                    },
                    {
                        'technique_id': 'T1059.003',
                        'name': 'Command and Scripting Interpreter: Windows Command Shell',
                        'description': 'Adversaries may abuse the Windows command shell for execution. The Windows command shell can control the system and execute various commands.',
                        'tactic': 'Execution',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1059/003/'
                    },
                    {
                        'technique_id': 'T1053.005',
                        'name': 'Scheduled Task/Job: Scheduled Task',
                        'description': 'Adversaries may abuse the Windows Task Scheduler to perform task scheduling for initial or recurring execution of malicious code.',
                        'tactic': 'Execution',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1053/005/'
                    },
                    # Persistence Techniques
                    {
                        'technique_id': 'T1547.001',
                        'name': 'Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder',
                        'description': 'Adversaries may configure system settings to automatically execute a program during system boot or logon.',
                        'tactic': 'Persistence',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1547/001/'
                    },
                    {
                        'technique_id': 'T1053.005',
                        'name': 'Scheduled Task/Job: Scheduled Task',
                        'description': 'Adversaries may abuse the Windows Task Scheduler to perform task scheduling for initial or recurring execution of malicious code.',
                        'tactic': 'Persistence',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1053/005/'
                    },
                    # Privilege Escalation Techniques
                    {
                        'technique_id': 'T1548.002',
                        'name': 'Abuse Elevation Control Mechanism: Bypass User Account Control',
                        'description': 'Adversaries may bypass UAC mechanisms to elevate process privileges on system.',
                        'tactic': 'Privilege Escalation',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1548/002/'
                    },
                    {
                        'technique_id': 'T1068',
                        'name': 'Exploitation for Privilege Escalation',
                        'description': 'Adversaries may exploit software vulnerabilities in an attempt to collect privileges.',
                        'tactic': 'Privilege Escalation',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1068/'
                    },
                    # Defense Evasion Techniques
                    {
                        'technique_id': 'T1562.001',
                        'name': 'Impair Defenses: Disable or Modify Tools',
                        'description': 'Adversaries may modify and/or disable security tools to avoid possible detection of their malware/tools and activities.',
                        'tactic': 'Defense Evasion',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1562/001/'
                    },
                    {
                        'technique_id': 'T1070.004',
                        'name': 'Indicator Removal on Host: File Deletion',
                        'description': 'Adversaries may delete files left behind by the actions of their intrusion activity.',
                        'tactic': 'Defense Evasion',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1070/004/'
                    },
                    # Credential Access Techniques
                    {
                        'technique_id': 'T1003.001',
                        'name': 'OS Credential Dumping: LSASS Memory',
                        'description': 'Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS).',
                        'tactic': 'Credential Access',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1003/001/'
                    },
                    {
                        'technique_id': 'T1110.001',
                        'name': 'Brute Force: Password Guessing',
                        'description': 'Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.',
                        'tactic': 'Credential Access',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1110/001/'
                    },
                    # Discovery Techniques
                    {
                        'technique_id': 'T1083',
                        'name': 'File and Directory Discovery',
                        'description': 'Adversaries may enumerate files and directories or may search in specific locations of a host or network share for certain information.',
                        'tactic': 'Discovery',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1083/'
                    },
                    {
                        'technique_id': 'T1082',
                        'name': 'System Information Discovery',
                        'description': 'An adversary may attempt to get detailed information about the operating system and hardware, including version, patches, hotfixes, service packs, and architecture.',
                        'tactic': 'Discovery',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1082/'
                    },
                    {
                        'technique_id': 'T1018',
                        'name': 'Remote System Discovery',
                        'description': 'Adversaries may attempt to get a listing of other systems by IP address, hostname, or other logical identifiers on a network.',
                        'tactic': 'Discovery',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1018/'
                    },
                    # Lateral Movement Techniques
                    {
                        'technique_id': 'T1021.001',
                        'name': 'Remote Services: Remote Desktop Protocol',
                        'description': 'Adversaries may use Valid Accounts to log into a computer using the Remote Desktop Protocol (RDP).',
                        'tactic': 'Lateral Movement',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1021/001/'
                    },
                    {
                        'technique_id': 'T1021.002',
                        'name': 'Remote Services: SMB/Windows Admin Shares',
                        'description': 'Adversaries may use Valid Accounts to interact with a remote network share using Server Message Block (SMB).',
                        'tactic': 'Lateral Movement',
                        'platforms': ['Windows'],
                        'url': 'https://attack.mitre.org/techniques/T1021/002/'
                    },
                    # Collection Techniques
                    {
                        'technique_id': 'T1005',
                        'name': 'Data from Local System',
                        'description': 'Adversaries may search local system sources, such as file systems and configuration files or local databases, to find files of interest and sensitive data.',
                        'tactic': 'Collection',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1005/'
                    },
                    {
                        'technique_id': 'T1074.001',
                        'name': 'Data Staged: Local Data Staging',
                        'description': 'Adversaries may stage collected data in a central location or directory on the local system prior to Exfiltration.',
                        'tactic': 'Collection',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1074/001/'
                    },
                    # Command & Control Techniques
                    {
                        'technique_id': 'T1071.001',
                        'name': 'Application Layer Protocol: Web Protocols',
                        'description': 'Adversaries may communicate using application layer protocols associated with web traffic to avoid detection/network filtering by blending in with existing traffic.',
                        'tactic': 'Command & Control',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1071/001/'
                    },
                    {
                        'technique_id': 'T1071.004',
                        'name': 'Application Layer Protocol: DNS',
                        'description': 'Adversaries may communicate using the Domain Name System (DNS) application layer protocol to avoid detection/network filtering by blending in with existing traffic.',
                        'tactic': 'Command & Control',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1071/004/'
                    },
                    # Exfiltration Techniques
                    {
                        'technique_id': 'T1041',
                        'name': 'Exfiltration Over C2 Channel',
                        'description': 'Adversaries may steal data by exfiltrating it over an existing command and control channel.',
                        'tactic': 'Exfiltration',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1041/'
                    },
                    {
                        'technique_id': 'T1048.003',
                        'name': 'Exfiltration Over Alternative Protocol: Exfiltration Over Unencrypted/Obfuscated Non-C2 Protocol',
                        'description': 'Adversaries may steal data by exfiltrating it over an unencrypted or obfuscated non-C2 protocol instead of over an existing command and control channel.',
                        'tactic': 'Exfiltration',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1048/003/'
                    },
                    # Impact Techniques
                    {
                        'technique_id': 'T1486',
                        'name': 'Data Encrypted for Impact',
                        'description': 'Adversaries may encrypt data on target systems or on large numbers of systems in a network to interrupt availability to system and network resources.',
                        'tactic': 'Impact',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1486/'
                    },
                    {
                        'technique_id': 'T1490',
                        'name': 'Inhibit System Recovery',
                        'description': 'Adversaries may delete or remove built-in data and turn off services designed to aid in the recovery of a corrupted system.',
                        'tactic': 'Impact',
                        'platforms': ['Windows', 'Linux', 'macOS'],
                        'url': 'https://attack.mitre.org/techniques/T1490/'
                    }
                ],
                'groups': [
                    {
                        'group_id': 'G0007',
                        'name': 'APT29',
                        'description': 'APT29 is a Russian cyber espionage group that has been active since at least 2008. The group has targeted government organizations and think tanks.',
                        'techniques': ['T1078', 'T1566', 'T1059'],
                        'targets': ['Financial institutions', 'Government'],
                        'url': 'https://attack.mitre.org/groups/G0007/'
                    },
                    {
                        'group_id': 'G0032',
                        'name': 'Lazarus Group',
                        'description': 'Lazarus Group is a North Korean cyber threat group that has been active since at least 2009. The group has targeted financial institutions and cryptocurrency exchanges.',
                        'techniques': ['T1078', 'T1566', 'T1105'],
                        'targets': ['Banking', 'Cryptocurrency'],
                        'url': 'https://attack.mitre.org/groups/G0032/'
                    },
                    {
                        'group_id': 'G0006',
                        'name': 'APT28',
                        'description': 'APT28 is a Russian cyber espionage group that has been active since at least 2007. The group has targeted government, military, and security organizations.',
                        'techniques': ['T1078', 'T1566', 'T1059', 'T1083'],
                        'targets': ['Government', 'Military', 'Security'],
                        'url': 'https://attack.mitre.org/groups/G0006/'
                    },
                    {
                        'group_id': 'G0016',
                        'name': 'APT-C-01',
                        'description': 'APT-C-01 is a Chinese cyber espionage group that has been active since at least 2004. The group has targeted various industries including technology and government.',
                        'techniques': ['T1078', 'T1566', 'T1059', 'T1083'],
                        'targets': ['Technology', 'Government', 'Healthcare'],
                        'url': 'https://attack.mitre.org/groups/G0016/'
                    },
                    {
                        'group_id': 'G0046',
                        'name': 'APT-C-23',
                        'description': 'APT-C-23 is a Palestinian cyber espionage group that has been active since at least 2017. The group has targeted various organizations in the Middle East.',
                        'techniques': ['T1078', 'T1566', 'T1059'],
                        'targets': ['Government', 'Education', 'Media'],
                        'url': 'https://attack.mitre.org/groups/G0046/'
                    },
                    {
                        'group_id': 'G0094',
                        'name': 'APT-C-35',
                        'description': 'APT-C-35 is an Iranian cyber espionage group that has been active since at least 2017. The group has targeted various industries and government entities.',
                        'techniques': ['T1078', 'T1566', 'T1059', 'T1083'],
                        'targets': ['Government', 'Technology', 'Healthcare'],
                        'url': 'https://attack.mitre.org/groups/G0094/'
                    },
                    {
                        'group_id': 'G0126',
                        'name': 'APT-C-36',
                        'description': 'APT-C-36 is a Pakistani cyber espionage group that has been active since at least 2016. The group has targeted various organizations in South Asia.',
                        'techniques': ['T1078', 'T1566', 'T1059'],
                        'targets': ['Government', 'Education', 'Media'],
                        'url': 'https://attack.mitre.org/groups/G0126/'
                    },
                    {
                        'group_id': 'G0134',
                        'name': 'APT-C-37',
                        'description': 'APT-C-37 is a Vietnamese cyber espionage group that has been active since at least 2014. The group has targeted various organizations in Southeast Asia.',
                        'techniques': ['T1078', 'T1566', 'T1059', 'T1083'],
                        'targets': ['Government', 'Technology', 'Education'],
                        'url': 'https://attack.mitre.org/groups/G0134/'
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error getting MITRE data: {e}")
            return {}

    def _get_domain_techniques(self, domain: str) -> list:
        """Get list of domain-relevant MITRE ATT&CK techniques."""
        domain_techniques = {
            "Financial Services": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1078.002",  # Valid Accounts: Domain Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1566.002",  # Phishing: Spearphishing Link
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1071.004",  # Application Layer Protocol: DNS
                "T1105",      # Ingress Tool Transfer
                "T1059.001",  # Command and Scripting Interpreter: PowerShell
                "T1059.003",  # Command and Scripting Interpreter: Windows Command Shell
                "T1083",      # File and Directory Discovery
                "T1082",      # System Information Discovery
                "T1018",      # Remote System Discovery
                "T1057",      # Process Discovery
                "T1049",      # System Network Connections Discovery
                "T1016",      # System Network Configuration Discovery
            ],
            "Healthcare": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",      # Ingress Tool Transfer
                "T1083",      # File and Directory Discovery
                "T1082",      # System Information Discovery
                "T1057",      # Process Discovery
                "T1049",      # System Network Connections Discovery
            ],
            "Government": [
                "T1078.002",  # Valid Accounts: Domain Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",      # Ingress Tool Transfer
                "T1083",      # File and Directory Discovery
                "T1082",      # System Information Discovery
                "T1018",      # Remote System Discovery
                "T1057",      # Process Discovery
            ],
            "Technology": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",      # Ingress Tool Transfer
                "T1083",      # File and Directory Discovery
                "T1082",      # System Information Discovery
                "T1057",      # Process Discovery
            ]
        }
        return domain_techniques.get(domain, [])

    def _get_recent_documents_html(self) -> str:
        """Generate HTML for recent documents with enhanced metadata."""
        try:
            files = self._list_ingested_files()
            if not files:
                return "<div style='text-align: center; color: #666; padding: 20px;'>No recent documents</div>"
            
            # Get document metadata for enhanced recent documents
            doc_metadata = {}
            ingested_docs = []
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata and ingested_document.doc_metadata.get("file_name"):
                    file_name = ingested_document.doc_metadata["file_name"]
                    doc_metadata[file_name] = {
                        'size': ingested_document.doc_metadata.get('file_size', 0),
                        'created': ingested_document.doc_metadata.get('creation_date', ''),
                        'hash': ingested_document.doc_metadata.get('content_hash', ''),
                        'type': self._get_file_type(file_name),
                        'doc_id': ingested_document.doc_id
                    }
                    ingested_docs.append((file_name, ingested_document.doc_metadata.get('creation_date', '')))
            
            # Sort by creation date (most recent first)
            ingested_docs.sort(key=lambda x: x[1], reverse=True)
            recent_files = [doc[0] for doc in ingested_docs[:8]]  # Show 8 most recent
            
            html_content = ""
            for file_name in recent_files:
                file_meta = doc_metadata.get(file_name, {})
                file_type = file_meta.get('type', 'other')
                type_icon = self._get_file_type_icon(file_type)
                
                # Format creation date
                created_date = file_meta.get('created', '')
                if created_date:
                    try:
                        # Try to format the date nicely
                        # datetime already imported at top of file
                        if isinstance(created_date, str) and created_date:
                            date_str = created_date[:10] if len(created_date) > 10 else created_date
                        else:
                            date_str = "Recently"
                    except:
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
            total_docs = len(files)
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

    def _upload_file(self, files: list[str]) -> None:
        logger.debug("Loading count=%s files", len(files))
        paths = [Path(file) for file in files]

        # Use service-level duplicate detection
        files_to_ingest = []
        for path in paths:
            files_to_ingest.append((str(path.name), path))
        
        if files_to_ingest:
            logger.info(f"Uploading {len(files_to_ingest)} files with automatic duplicate detection")
            self._ingest_service.bulk_ingest(files_to_ingest)

    def _ingest_folder(self, folder_files: list[str]) -> tuple[list, str]:
        """Ingest an entire folder with progress tracking."""
        try:
            if not folder_files:
                return self._list_ingested_files(), "❌ No folder selected"
            
            # Get the folder path from the first file
            folder_path = Path(folder_files[0]).parent
            logger.info(f"Starting folder ingestion for: {folder_path}")
            
            if not folder_path.exists():
                return self._list_ingested_files(), "❌ Folder not found"
            
            # Import the LocalIngestWorker from the script
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
            
            try:
                from ingest_folder import LocalIngestWorker
                from internal_assistant.settings.settings import settings
            except ImportError as e:
                logger.error(f"Failed to import LocalIngestWorker: {e}")
                return self._list_ingested_files(), f"❌ Folder ingestion not available: {str(e)}"
            
            # Initialize worker with UI-friendly settings
            worker = LocalIngestWorker(
                self._ingest_service, 
                settings(), 
                max_attempts=2,
                checkpoint_file="ui_folder_ingestion_checkpoint.json"
            )
            
            # Start ingestion
            worker.ingest_folder(folder_path, ignored=[], resume=True)
            
            logger.info(f"Folder ingestion completed successfully: {folder_path}")
            return self._list_ingested_files(), "✅ Folder ingested successfully!"
            
        except Exception as e:
            logger.error(f"Folder ingestion failed: {e}", exc_info=True)
            return self._list_ingested_files(), f"❌ Ingestion failed: {str(e)}"

    def _create_context_filter(self) -> ContextFilter | None:
        """Create a context filter using all available documents."""
        try:
            # Use all available documents
            all_doc_ids = []
            for ingested_document in self._ingest_service.list_ingested():
                if ingested_document.doc_metadata:
                    all_doc_ids.append(ingested_document.doc_id)
            
            if all_doc_ids:
                logger.info(f"Searching in {len(all_doc_ids)} total documents")
                return ContextFilter(docs_ids=all_doc_ids)
            else:
                logger.warning("No documents available for search")
                return None
        except Exception as e:
            logger.error(f"Error creating context filter: {e}")
            return None

    def _set_explanatation_mode(self, explanation_mode: str) -> None:
        self._explanation_mode = explanation_mode

    @staticmethod
    def _get_system_prompt_template(template_name: str) -> str:
        """Get pre-configured system prompt templates for different use cases."""
        templates = {
            "Default Assistant": "You are a helpful AI assistant. Provide accurate, concise, and helpful responses based on the available context.",
            "Financial Analyst": "You are a financial analyst AI. Focus on financial metrics, trends, market analysis, and investment insights. Provide data-driven responses with clear explanations of financial concepts.",
            "Technical Expert": "You are a technical expert AI. Provide detailed technical explanations, focus on accuracy, include relevant technical specifications, and explain complex concepts clearly.",
            "Research Assistant": "You are a research assistant AI. Provide comprehensive analysis, cite sources when available, present multiple perspectives, and organize information logically for research purposes.",
            "Document Summarizer": "You are a document summarization AI. Extract key points, create concise summaries, highlight important findings, and organize information in a clear, structured format.",
            "Compliance Reviewer": "You are a compliance review AI. Focus on regulatory requirements, identify potential compliance issues, highlight risk factors, and provide recommendations for regulatory adherence.",
            "Custom": ""
        }
        return templates.get(template_name, templates["Default Assistant"])

    def _set_current_mode(self, mode: Modes) -> Any:
        self.mode = mode
        self._set_system_prompt(self._get_default_system_prompt(mode))
        interactive = self._system_prompt is not None
        return gr.update(placeholder=self._system_prompt, interactive=interactive)









    def _build_ui_blocks(self) -> gr.Blocks:
        logger.debug("Creating the accessible UI blocks")
        
        # Accessible UI Styling - Black Background with Light Text
        modern_css = """
        /* Force black background everywhere */
        * {
            background-color: #000000 !important;
            color: #e0e0e0 !important;
        }
        
        /* Accessible UI Styling - Black Background with High Contrast */
        html, body, .gradio-container {
            background: #000000 !important;
            color: #e0e0e0 !important;
        }
        .gradio-container {
            max-width: 1400px !important;
            margin: 0 auto !important;
            font-family: 'Arial', 'Helvetica', sans-serif !important;
            font-size: 16px !important;
            line-height: 1.6 !important;
        }
        
        /* Header Styling - Tighter Vertical Spacing */
        .header-container {
            background: #000 !important;
            border-radius: 12px;
            padding: 8px 22px; /* Reduced vertical padding from 22px to 8px, kept horizontal 22px */
            margin-bottom: 8px; /* Reduced from 22px to 8px */
            box-shadow: 0 4px 20px rgba(0, 119, 190, 0.2);
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 3px solid #0077BE;
            min-height: 120px; /* Reduced from 280px to 120px */
            overflow: visible;
        }
        
        .header-logo {
            display: flex;
            align-items: center;
            justify-content: center; /* Changed to center for better layout */
            gap: 7px;
            padding: 4px 7px; /* Reduced vertical padding from 7px to 4px */
            min-height: 100px; /* Reduced from 273px to match new header height */
        }
        
        .header-logo img, .internal-logo-img img {
            height: 150px; /* Increased from 100px for better prominence */
            max-width: 450px; /* Increased from 300px for better readability */
            width: auto;
            object-fit: contain;
            filter: brightness(1) invert(0);
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            background: none !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        
        .internal-logo-img {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }
        
        .header-title {
            color: #e0e0e0;
            font-size: 32px; /* Reduced from 37px to fit tighter header */
            font-family: 'Merriweather', 'Inter', 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            font-weight: 800;
            margin: 0 auto;
            text-align: center;
            letter-spacing: 1.0px;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.7);
            line-height: 1.0; /* Tighter line height */
        }
        
        .header-subtitle {
            color: #b0b0b0;
            font-size: 20px; /* Reduced from 25px to fit tighter header */
            margin: 0;
            font-weight: 500;
            line-height: 1.0; /* Tighter line height */
        }
        
        /* ========================================
           SIDEBAR STYLING CONSISTENCY DOCUMENTATION
           ========================================
           
           This section ensures perfect visual consistency across all sidebar components:
           
           BUTTON STYLING HIERARCHY:
           1. .filter-btn - Document Library Actions buttons (ALL, PDF, EXCEL, WORD, RECENT, ANALYZED)
           2. .mode-selector label - Chat Mode buttons (RAG, SEARCH, COMPARE, SUMMARIZE, DIRECT CHAT)
           
           BOTH use IDENTICAL properties:
           - Green outline: #8BC34A (unselected)
           - Blue highlight: #0077BE (selected/hover)
           - Padding: 4px 8px
           - Border-radius: 12px
           - Font-size: 11px
           - Font-weight: 600
           - Letter-spacing: 0.5px
           - Margin: 2px
           
           INPUT STYLING:
           - .doc-search-input input (search box)
           - .gradio-textbox (AI Configuration inputs)
           BOTH use IDENTICAL properties to match exactly
           
           FONT CONSISTENCY:
           - .sidebar-container sets: font-family: 'Inter', 'Segoe UI', 'Roboto', 'Arial', sans-serif
           - All children inherit via: .sidebar-container * { font-family: inherit }
           
           HEADER STYLING:
           - .collapsible-title - Section headers use consistent blue color (#0077BE)
           
           ======================================== */
        
        /* Sidebar Styling */
        .sidebar-container {
            background: #000;
            border-radius: 12px;
            padding: 24px;
            border: 3px solid #0077BE;
            height: fit-content;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
            /* CONSISTENT FONT FAMILY throughout sidebar */
            font-family: 'Inter', 'Segoe UI', 'Roboto', 'Arial', sans-serif !important;
        }
        
        /* Ensure all sidebar elements inherit consistent font */
        .sidebar-container * {
            font-family: inherit !important;
        }
        
        
        /* Configuration Button Styling - Purple theme */
        .config-btn {
            background: #18181b !important;
            border: 2px solid #8B5CF6 !important; /* Purple instead of green */
            border-radius: 12px !important;
            color: #8B5CF6 !important; /* Purple text */
            font-weight: 600 !important;
            font-size: 11px !important;
            letter-spacing: 0.5px !important;
            padding: 4px 8px !important;
            margin: 2px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            font-family: inherit !important;
            text-transform: uppercase !important;
        }

        .config-btn:hover {
            background: #8B5CF6 !important; /* Purple background on hover */
            color: white !important;
            border-color: #8B5CF6 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4) !important; /* Purple shadow */
        }

        .config-btn:active,
        .config-btn.filter-active {
            background: #8B5CF6 !important; /* Purple when active */
            color: white !important;
            border-color: #8B5CF6 !important;
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3) !important; /* Purple shadow */
        }

        /* Ingest Directory Button Styling - Yellow theme (OVERRIDE) */
        .modern-button.ingest-button {
            background: transparent !important; /* Match other upload buttons */
            border: 2px solid #EAB308 !important; /* Yellow border */
            color: #EAB308 !important; /* Yellow text */
            font-size: 16px !important; /* Explicitly match .modern-button */
            padding: 12px 20px !important; /* Explicitly match .modern-button */
            border-radius: 8px !important; /* Match .modern-button */
            font-weight: 600 !important; /* Match .modern-button */
        }

        .modern-button.ingest-button:hover {
            background: #EAB308 !important; /* Yellow background on hover */
            color: black !important; /* Black text on yellow background for better contrast */
            border-color: #EAB308 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(234, 179, 8, 0.4) !important; /* Yellow shadow */
        }

        .modern-button.ingest-button:active {
            background: #EAB308 !important; /* Yellow when active */
            color: black !important;
            border-color: #EAB308 !important;
            box-shadow: 0 2px 8px rgba(234, 179, 8, 0.3) !important; /* Yellow shadow */
        }

        .sidebar-section {
            margin-bottom: 16px;
        }
        
        .sidebar-title {
            font-size: 18px;
            font-weight: 700;
            color: #0077BE;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #333;
            padding-bottom: 8px;
        }
        
        /* Enhanced Collapsible Section Styling */
        .collapsible-section {
            margin-bottom: 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #18181b;
            transition: all 0.3s ease;
        }
        
        .collapsible-section:hover {
            border-color: #0077BE;
            box-shadow: 0 2px 10px rgba(0, 119, 190, 0.1);
        }
        
        .collapsible-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            cursor: pointer;
            background: #232526;
            border-radius: 6px 6px 0 0;
            user-select: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .collapsible-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 119, 190, 0.1), transparent);
            transition: left 0.6s ease;
        }
        
        .collapsible-header:hover::before {
            left: 100%;
        }
        
        .collapsible-header:hover {
            background: linear-gradient(135deg, #2a2d2e 0%, #323639 100%);
            transform: translateY(-1px);
        }
        
        .collapsible-title {
            font-size: 16px;
            font-weight: 600;
            color: #0077BE;
            margin: 0;
            transition: color 0.3s ease;
        }
        
        .collapsible-header:hover .collapsible-title {
            color: #00A3FF;
            text-shadow: 0 0 10px rgba(0, 119, 190, 0.3);
        }
        
        .collapsible-icon {
            color: #0077BE;
            font-size: 16px; /* Increased size for better visibility */
            font-weight: bold;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            min-width: 20px; /* Ensure consistent width */
            text-align: center;
            display: inline-block;
        }
        
        .collapsible-header:hover .collapsible-icon {
            color: #00A3FF;
            transform: scale(1.3); /* Slightly bigger scale */
            text-shadow: 0 0 8px rgba(0, 163, 255, 0.5);
        }
        
        .collapsible-content {
            padding: 16px;
            border-top: 1px solid #333;
            background: #18181b;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
            max-height: 1000px; /* Large enough for expanded content */
            opacity: 1;
            transform: translateY(0);
        }
        
        .collapsed .collapsible-content {
            max-height: 0;
            padding-top: 0;
            padding-bottom: 0;
            opacity: 0;
            transform: translateY(-10px);
            border-top: none;
        }
        
        /* Smooth rotation transition for icons - included in main .collapsible-icon definition above */
        
        /* Enhanced icon rotation for collapsed state */
        .collapsed .collapsible-icon {
            transform: rotate(-90deg);
        }
        
        /* Enhanced hover states during collapse/expand */
        .collapsible-section.expanding .collapsible-header,
        .collapsible-section.collapsing .collapsible-header {
            background: linear-gradient(135deg, #2a2d2e 0%, #323639 100%);
        }
        
        .collapsible-section.expanding .collapsible-icon,
        .collapsible-section.collapsing .collapsible-icon {
            color: #00A3FF;
            text-shadow: 0 0 8px rgba(0, 163, 255, 0.5);
            animation: pulse 0.4s ease-in-out;
        }
        
        /* Pulse animation for icon during transitions */
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .collapsed:hover .collapsible-icon {
            transform: rotate(-90deg) scale(1.3);
            text-shadow: 0 0 8px rgba(0, 163, 255, 0.5);
        }
        
        /* Ensure triangles are always visible and properly sized */
        .collapsible-icon::before {
            content: '';
            display: inline-block;
            width: 0;
            height: 0;
        }
        
        /* Document Library Styling */
        /* Note: .document-item styling moved to enhanced section below (around line 1742) */
        
        .document-icon {
            margin-right: 8px;
            color: #0077BE;
        }
        
        .folder-item {
            font-weight: 600;
            color: #8BC34A;
        }
        
        .folder-item .document-icon {
            color: #8BC34A;
        }
        
        /* Filter Tags Styling - REMOVED: Legacy filter tag classes not used in current implementation */
        /* Current sidebar uses .filter-btn classes instead (see below) */
        
        /* Filter Button Styling */
        .filter-btn {
            background: transparent !important;
            border: 2px solid #8BC34A !important;
            color: #8BC34A !important;
            padding: 8px 16px !important;
            border-radius: 12px !important;
            font-size: 16px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            text-transform: uppercase !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            margin: 2px !important;
            box-shadow: 0 0 5px rgba(139, 195, 74, 0.3) !important;
            min-height: 48px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        .filter-btn:hover {
            border-color: #0077BE !important;
            color: #0077BE !important;
            background: rgba(0, 119, 190, 0.1) !important;
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.4) !important;
        }
        
        .filter-active {
            background: transparent !important;
            border-color: #0077BE !important;
            color: #0077BE !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
        }
        
        /* Document Search Input Styling */
        .doc-search-input input {
            background: #232526 !important;
            border: 2px solid #333 !important;
            border-radius: 6px !important;
            color: #e0e0e0 !important;
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        .doc-search-input input:focus {
            border-color: #0077BE !important;
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.3) !important;
        }
        
        /* Document Actions Styling */
        .document-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        
        .document-item:hover .document-actions {
            opacity: 1;
        }
        
        .doc-action-btn {
            background: transparent;
            border: 1px solid #555;
            color: #888;
            padding: 4px 6px;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .doc-action-btn:hover {
            background: #0077BE;
            border-color: #0077BE;
            color: #ffffff;
            transform: scale(1.1);
        }
        
        /* Enhanced Document Item Layout with Advanced Hover Effects */
        .document-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin: 4px 0;
            background: #232526;
            border: 1px solid #333;
            border-radius: 6px;
            color: #e0e0e0;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        /* Hover gradient overlay effect */
        .document-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 119, 190, 0.1), transparent);
            transition: left 0.6s ease;
        }
        
        .document-item:hover::before {
            left: 100%;
        }
        
        .document-item:hover {
            background: linear-gradient(135deg, #0077BE 0%, #005A8B 100%);
            color: #ffffff;
            transform: translateX(6px) translateY(-1px);
            border-color: #005A8B;
            box-shadow: 0 4px 20px rgba(0, 119, 190, 0.3);
        }
        
        .document-item:active {
            transform: translateX(4px) translateY(0px);
            transition: all 0.1s ease;
        }
        
        .document-item.selected {
            background: rgba(0, 119, 190, 0.3);
            border-color: #0077BE;
            box-shadow: 0 2px 10px rgba(0, 119, 190, 0.2);
        }
        
        /* Recent Documents Special Styling with Enhanced Effects */
        .recent-doc-item {
            border-left: 3px solid #8BC34A;
            position: relative;
        }
        
        .recent-doc-item::after {
            content: 'NEW';
            position: absolute;
            top: 4px;
            right: 4px;
            background: #8BC34A;
            color: #000;
            font-size: 8px;
            font-weight: bold;
            padding: 1px 4px;
            border-radius: 2px;
            opacity: 0.7;
            transition: opacity 0.3s ease;
        }
        
        .recent-doc-item:hover {
            border-left-color: #ffffff;
            border-left-width: 4px;
        }
        
        .recent-doc-item:hover::after {
            opacity: 1;
            background: #ffffff;
            color: #0077BE;
        }
        
        /* Enhanced Quick Actions Styling */
        .quick-action-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 12px;
        }
        
        .quick-action-btn {
            background: transparent !important;
            color: #0077BE !important;
            border: 2px solid #0077BE !important;
            padding: 8px 12px !important;
            font-size: 14px !important;
            border-radius: 6px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative !important;
            overflow: hidden !important;
            cursor: pointer !important;
        }
        
        .quick-action-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 119, 190, 0.2), transparent);
            transition: left 0.5s ease;
        }
        
        .quick-action-btn:hover::before {
            left: 100%;
        }
        
        .quick-action-btn:hover {
            background: linear-gradient(135deg, #0077BE 0%, #005A8B 100%) !important;
            color: #ffffff !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(0, 119, 190, 0.4) !important;
            border-color: #005A8B !important;
        }
        
        .quick-action-btn:active {
            transform: translateY(-1px) scale(0.98) !important;
            transition: all 0.1s ease !important;
        }
        
        /* Green styling for quick action buttons */
        .green-btn {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
            color: #ffffff !important;
            border: 2px solid #28a745 !important;
        }
        
        .green-btn:hover {
            background: linear-gradient(135deg, #218838 0%, #1e7e34 100%) !important;
            border-color: #1e7e34 !important;
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4) !important;
        }
        
        /* Filter status message styling */
        .filter-status {
            margin: 8px 0;
            font-size: 13px;
            text-align: center;
        }
        
        /* Enhanced Processing Queue Item */
        .queue-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            margin: 4px 0;
            background: #232526;
            border: 1px solid #333;
            border-radius: 6px;
            color: #e0e0e0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .queue-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(139, 195, 74, 0.1), transparent);
            transition: left 0.6s ease;
        }
        
        .queue-item:hover::before {
            left: 100%;
        }
        
        .queue-item:hover {
            background: #2a2d2e;
            border-color: #555;
            transform: translateX(3px);
        }
        
        .queue-status {
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 12px;
            background: #8BC34A;
            color: #000;
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .queue-status.completed {
            background: #8BC34A;
            box-shadow: 0 2px 8px rgba(139, 195, 74, 0.3);
        }
        
        .queue-status.processing {
            background: #FF9800;
            animation: processingPulse 2s infinite;
            box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
        }
        
        .queue-status.pending {
            background: #666;
            box-shadow: 0 2px 8px rgba(102, 102, 102, 0.3);
        }
        
        @keyframes processingPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        /* Mode Explanation Styling */
        .mode-explanation-container {
            margin-top: 12px;
        }
        
        .mode-explanation {
            background: #232526;
            border: 2px solid #0077BE;
            border-radius: 8px;
            padding: 12px 16px;
            color: #e0e0e0;
            font-size: 14px;
            line-height: 1.4;
            font-style: italic;
        }
        
        /* Usage Instructions Section Styling */
        .usage-instructions-section {
            background: #000000;
            border: 2px solid #0077BE;
            border-radius: 12px;
            padding: 20px;
            margin: 0;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.2);
            z-index: 10;
        }
        
        .usage-instructions-container {
            color: #e0e0e0;
            line-height: 1.6;
        }
        
        .usage-instructions-title {
            font-size: 20px;
            font-weight: 700;
            color: #0077BE;
            margin-bottom: 20px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #0077BE;
            padding-bottom: 10px;
        }
        
        .usage-instructions-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 16px;
        }
        
        .instruction-category {
            background: #232526;
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid #0077BE;
        }
        
        .instruction-category h4 {
            color: #0077BE;
            margin: 0 0 12px 0;
            font-size: 16px;
            font-weight: 600;
        }
        
        .instruction-category ul {
            margin: 0;
            padding-left: 20px;
            list-style-type: none;
        }
        
        .instruction-category li {
            margin-bottom: 8px;
            position: relative;
            padding-left: 0;
        }
        
        .instruction-category li::before {
            content: "▶";
            color: #0077BE;
            font-size: 12px;
            position: absolute;
            left: -16px;
            top: 2px;
        }
        
        .instruction-category strong {
            color: #0077BE;
            font-weight: 600;
        }
        
        /* File Management Section Styling - Matching Chat Container */
        .file-management-section {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #0077BE;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
            height: auto; /* Auto height to wrap content */
            min-height: 500px; /* Same as chat */
            max-height: calc(100vh - 200px); /* Same as chat */
            display: flex;
            flex-direction: column;
            position: relative; /* For resize handle positioning */
            resize: vertical; /* Enable basic CSS resize as fallback */
            overflow: auto; /* Allow scrolling when content exceeds max-height */
            flex-shrink: 1; /* Allow shrinking */
            margin-top: 20px;
            padding: 20px;
        }
        
        .file-section-title {
            font-size: 18px;
            font-weight: 700;
            color: #0077BE;
            margin-bottom: 16px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #232526; /* Add background for visibility */
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #0077BE;
        }
        
        .file-list-header {
            font-size: 16px;
            font-weight: 600;
            color: #0077BE;
            margin: 16px 0 8px 0;
            border-bottom: 1px solid #333;
            padding-bottom: 4px;
        }
        
        /* Enhanced File List Container with Better Scrolling */
        .file-list-container {
            background: #232526;
            border-radius: 8px;
            border: 2px solid #333;
            height: 800px; /* Doubled height to show more files */
            overflow-y: scroll; /* Always show scrollbar */
            overflow-x: auto; /* Enable horizontal scrolling */
            scrollbar-width: auto;
            scrollbar-color: #0077BE #232526;
            padding: 12px;
            scroll-behavior: smooth; /* Smooth scrolling */
            position: relative;
            min-width: 100%; /* Ensure minimum width */
        }
        
        /* Enhanced scrollbar for file list container - More visible */
        .file-list-container::-webkit-scrollbar {
            width: 16px; /* Wider scrollbar for easier use */
            background: #18181b;
            border-radius: 8px;
        }
        
        .file-list-container::-webkit-scrollbar-track {
            background: #18181b;
            border-radius: 8px;
            margin: 2px;
            border: 1px solid #333;
        }
        
        .file-list-container::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #0077BE 0%, #005A8B 100%);
            border-radius: 8px;
            border: 2px solid #18181b;
            min-height: 30px; /* Minimum thumb height for easier grabbing */
        }
        
        .file-list-container::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #005A8B 0%, #004A73 100%);
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.5);
            border-color: #0077BE;
        }
        
        .file-list-container::-webkit-scrollbar-thumb:active {
            background: linear-gradient(135deg, #004A73 0%, #003A5C 100%);
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.7);
        }
        
        /* Scrollbar corner */
        .file-list-container::-webkit-scrollbar-corner {
            background: #18181b;
        }
        
        /* Horizontal scrollbar styling */
        .file-list-container::-webkit-scrollbar:horizontal {
            height: 16px; /* Height for horizontal scrollbar */
        }
        
        .file-list-container::-webkit-scrollbar-thumb:horizontal {
            background: linear-gradient(90deg, #0077BE 0%, #005A8B 100%);
            border-radius: 8px;
            border: 2px solid #18181b;
            min-width: 30px; /* Minimum thumb width for easier grabbing */
        }
        
        .file-list-container::-webkit-scrollbar-thumb:horizontal:hover {
            background: linear-gradient(90deg, #005A8B 0%, #004A73 100%);
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.5);
            border-color: #0077BE;
        }
        
        
        /* Enhanced File List Items for Better Scrolling */
        .file-list-container tr,
        .file-list-container td {
            background: #2a2d2e !important;
            border: 1px solid #404344 !important;
            border-radius: 6px !important;
            padding: 12px 16px !important;
            margin: 4px 0 !important;
            color: #e0e0e0 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            display: block !important;
            word-wrap: break-word !important;
            white-space: normal !important;
            min-height: 24px !important;
            line-height: 1.4 !important;
        }
        
        .file-list-container tr:hover,
        .file-list-container td:hover {
            background: #0077BE !important;
            color: #ffffff !important;
            transform: translateX(4px) !important;
            box-shadow: 4px 0 12px rgba(0, 119, 190, 0.4) !important;
            border-color: #005A8B !important;
        }
        
        .file-list-container tr:nth-child(even),
        .file-list-container td:nth-child(even) {
            background: #1f2223 !important;
        }
        
        .file-list-container tr:nth-child(even):hover,
        .file-list-container td:nth-child(even):hover {
            background: #0077BE !important;
        }
        
        /* Add file type indicators */
        .file-list-container tr::before,
        .file-list-container td::before {
            content: "📄 ";
            color: #0077BE;
            margin-right: 8px;
            font-size: 12px;
        }
        
        /* Upload Button Styling */
        .upload-button {
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
        }
        
        .upload-button:hover {
            background: linear-gradient(135deg, #8BC34A 0%, #7CB342 100%) !important;
            color: #e0e0e0 !important;
            border-color: #689F38 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(139, 195, 74, 0.3) !important;
        }
        
        /* Folder Button Styling */
        .folder-button {
            background: transparent !important;
            color: #0077BE !important;
            border: 2px solid #0077BE !important;
        }
        
        .folder-button:hover {
            background: linear-gradient(135deg, #0077BE 0%, #005A8B 100%) !important;
            color: #e0e0e0 !important;
            border-color: #004A73 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 119, 190, 0.3) !important;
        }
        
        /* Danger Button Styling */
        .danger-button {
            background: transparent !important;
            color: #FF6B6B !important;
            border: 2px solid #FF6B6B !important;
        }
        
        .danger-button:hover {
            background: linear-gradient(135deg, #FF6B6B 0%, #E55555 100%) !important;
            color: #e0e0e0 !important;
            border-color: #CC5555 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.3) !important;
        }
        
        /* Ingest Button Styling */
        .ingest-button {
            background: transparent !important;
            color: #8A2BE2 !important;
            border: 2px solid #8A2BE2 !important;
        }
        
        .ingest-button:hover {
            background: linear-gradient(135deg, #8A2BE2 0%, #7B1FA2 100%) !important;
            color: #e0e0e0 !important;
            border-color: #6A1B9A !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(138, 43, 226, 0.3) !important;
        }
        
        /* Hide folder input by default */
        .folder-input {
            display: none !important;
        }
        
        /* Universal Button Styling - Standardized across all left sidebar sections */
        .modern-button, 
        button,
        .gradio-button,
        input[type="submit"],
        input[type="button"] {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 12px 20px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            min-height: 48px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
            position: relative !important;
            z-index: 50 !important; /* Ensure buttons stay above content */
        }
        
        /* Universal hover effect - green gradient with lift */
        .modern-button:hover, 
        button:hover,
        .gradio-button:hover,
        input[type="submit"]:hover,
        input[type="button"]:hover {
            background: linear-gradient(135deg, #8BC34A 0%, #7CB342 100%) !important;
            color: #e0e0e0 !important;
            border-color: #689F38 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(139, 195, 74, 0.3) !important;
        }
        
        /* Universal active/pressed effect - darker green, pressed down */
        .modern-button:active,
        .modern-button:focus,
        button:active,
        button:focus,
        .gradio-button:active,
        .gradio-button:focus,
        input[type="submit"]:active,
        input[type="submit"]:focus,
        input[type="button"]:active,
        input[type="button"]:focus {
            background: linear-gradient(135deg, #689F38 0%, #558B2F 100%) !important;
            color: #e0e0e0 !important;
            border-color: #33691E !important;
            transform: translateY(0px) !important;
            box-shadow: 0 2px 8px rgba(104, 159, 56, 0.4) !important;
            outline: none !important;
        }
        
        
        /* Danger buttons - red variation with same behavior */
        .danger-button {
            background: transparent !important;
            color: #dc2626 !important;
            border: 2px solid #dc2626 !important;
        }
        
        .danger-button:hover {
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%) !important;
            color: #e0e0e0 !important;
            border-color: #b91c1c !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(220, 38, 38, 0.3) !important;
        }
        
        /* Secondary buttons - blue variation with same behavior */
        .secondary-button {
            background: transparent !important;
            color: #0077BE !important;
            border: 2px solid #0077BE !important;
        }
        
        .secondary-button:hover {
            background: linear-gradient(135deg, #005A8B 0%, #0077BE 100%) !important;
            color: #e0e0e0 !important;
            border-color: #004A73 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 119, 190, 0.3) !important;
        }
        
        /* Active state for search buttons - REMOVED: Not used in current sidebar implementation */
        
        
        /* Chat Interface Styling */
        .chat-container {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #0077BE;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
            height: auto; /* Auto height to wrap content */
            min-height: 300px; /* Minimum height for usability */
            max-height: calc(100vh - 250px); /* Still limit maximum height */
            display: flex;
            flex-direction: column;
            position: relative; /* For resize handle positioning */
            resize: vertical; /* Enable basic CSS resize as fallback */
            overflow: auto; /* Allow scrolling when content exceeds max-height */
            flex-shrink: 1; /* Allow shrinking to make space for document management */
        }
        
        /* Chat Resize Handle - REMOVED: Fixed size chatbox */
        
        /* Custom Chat Layout Styling */
        .chat-input-top {
            background: #1a1a1a !important;
            border: 2px solid #0077BE !important;
            border-radius: 12px 12px 0 0 !important;
            padding: 20px !important;
            order: 1; /* Ensure it's at the top */
        }
        
        .chat-input-textbox textarea {
            min-height: 84px !important; /* Keep our doubled height */
            background: #232526 !important;
            border: 2px solid #333 !important;
            color: #e0e0e0 !important;
            font-size: 16px !important;
        }
        
        /* Action Buttons - Reduced Height by Half */
        .send-button,
        .retry-button,
        .undo-button,
        .clear-button {
            background: linear-gradient(135deg, #0077BE 0%, #005a9e 100%) !important;
            color: white !important;
            border: 2px solid #0077BE !important;
            min-height: 24px !important; /* Reduced from 48px to 24px */
            padding: 6px 10px !important; /* Reduced from 12px 20px to 6px 10px */
            font-size: 14px !important; /* Slightly smaller font for compact buttons */
        }
        
        .send-button:hover,
        .retry-button:hover,
        .undo-button:hover,
        .clear-button:hover {
            background: linear-gradient(135deg, #005a9e 0%, #004080 100%) !important;
        }
        
        .chat-messages {
            order: 2; /* Middle position */
            flex: 1 !important;
        }
        
        .chat-bottom-area {
            background: #1a1a1a !important;
            border: 2px solid #333 !important;
            border-radius: 0 0 12px 12px !important;
            padding: 10px !important;
            order: 3; /* Bottom position */
        }
        
        /* Document Management Resize Handle */
        .doc-resize-handle {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 20px;
            height: 20px;
            cursor: nw-resize;
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #0077BE 25%, #0077BE 50%, transparent 50%, transparent 75%, #0077BE 75%);
            background-size: 4px 4px;
            border-bottom-right-radius: 12px;
            opacity: 0.7;
            transition: opacity 0.2s ease;
            z-index: 10;
            user-select: none;
        }
        
        .doc-resize-handle:hover {
            opacity: 1;
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #00A3FF 25%, #00A3FF 50%, transparent 50%, transparent 75%, #00A3FF 75%);
        }
        
        .doc-resize-handle::after {
            content: '';
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            background: linear-gradient(-45deg, transparent 30%, #0077BE 30%, #0077BE 40%, transparent 40%, transparent 60%, #0077BE 60%, #0077BE 70%, transparent 70%);
            background-size: 2px 2px;
            border-radius: 2px;
        }
        
        /* Chat container when being resized */
        .chat-container.resizing {
            transition: none !important; /* Disable transitions during resize */
            user-select: none;
        }
        
        .chat-header {
            padding: 20px 24px;
            border-bottom: 2px solid #333;
            background: #232526;
            border-radius: 12px 12px 0 0;
        }
        
        /* Enhanced Chat Header with Mode Selector */
        .enhanced-chat-header {
            background: #000000 !important;
            border-bottom: 2px solid #0077BE !important;
            padding: 12px 16px !important;
            margin-bottom: 8px !important;
            border-radius: 8px 8px 0 0 !important;
        }
        
        /* Chat Mode Selector - Adapted for Header */
        .chat-mode-selector {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 4px !important;
            width: 100% !important;
            align-items: center !important;
            justify-content: flex-end !important;
        }
        
        /* Chat Mode Buttons - Compact Header Version */
        .chat-mode-selector label {
            background: transparent !important;
            border: 2px solid #8BC34A !important;
            color: #8BC34A !important;
            padding: 6px 12px !important;
            border-radius: 8px !important;
            font-size: 14px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            text-transform: uppercase !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            margin: 1px !important;
            box-shadow: 0 0 5px rgba(139, 195, 74, 0.3) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: calc(50% - 4px) !important;
            flex: 0 0 calc(50% - 4px) !important;
            box-sizing: border-box !important;
            min-height: 36px !important;
            height: auto !important;
        }
        
        /* Active Mode (Blue) */
        .chat-mode-selector .mode-active,
        .chat-mode-selector input[type="radio"]:checked + label.mode-active {
            background: #0077BE !important;
            border-color: #0077BE !important;
            color: #ffffff !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
        }
        
        /* Inactive Mode (Green) */
        .chat-mode-selector .mode-inactive,
        .chat-mode-selector input[type="radio"]:not(:checked) + label.mode-inactive {
            background: #1e1e1e !important;
            border-color: #8BC34A !important;
            color: #8BC34A !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Hover Effects */
        .chat-mode-selector label:hover {
            border-color: #0077BE !important;
            color: #0077BE !important;
            background: rgba(0, 119, 190, 0.1) !important;
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.4) !important;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            background: #18181b;
            min-height: 500px; /* Increased minimum height */
            height: auto;
        }
        
        .chat-input {
            padding: 24px;
            border-top: none;
            background: #232526;
            border-radius: 0 0 12px 12px;
            position: relative; /* Changed from sticky to relative */
            bottom: 0;
            z-index: 100;
            flex-shrink: 0; /* Prevent input area from shrinking */
        }
        
        /* Enhanced Chat Interface Layout */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 300px); /* FIXED: Auto-size based on viewport */
            min-height: 500px; /* IMPROVED: Better minimum height */
            max-height: calc(100vh - 200px); /* IMPROVED: More generous maximum */
            position: relative; /* For resize handle positioning */
        }
        
        .chat-messages {
            flex: 1; /* Take all available space in container */
            overflow-y: auto; /* Enable vertical scrolling for messages */
            overflow-x: hidden; /* Hide horizontal scrollbar */
            padding: 16px;
            background: #000000;
            display: flex;
            flex-direction: column;
            min-height: 0; /* Allow shrinking */
        }
        
        /* Enhanced Chat Interface Layout */
        .chat-interface {
            display: flex !important;
            flex-direction: column !important;
            height: auto !important; /* Auto height to wrap content */
            min-height: 200px !important; /* Reduced minimum */
            max-height: 100% !important;
        }
        
        /* Main content area layout optimization */
        .main-content-column {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 100px);
            gap: 0;
            overflow-y: auto; /* Allow scrolling if content overflows */
        }
        
        /* Main chatbot container - improved message display */
        .main-chatbot,
        .chat-interface .chatbot,
        #chatbot {
            flex: 1 1 auto !important; /* Fill most of the available space */
            overflow-y: visible !important; /* FIXED: Let parent handle scrolling */
            min-height: auto !important; /* FIXED: Dynamic minimum height */
            max-height: none !important; /* Remove height limit to enable flex growth */
            background: #000000 !important;
            border: 1px solid #333 !important;
            border-radius: 8px !important;
            height: auto !important; /* Allow dynamic height adjustment */
            resize: none !important; /* Disable individual chatbot resize, use container resize instead */
            scrollbar-width: thin !important;
            scrollbar-color: #0077BE #232526 !important;
            margin-bottom: 8px !important; /* Small margin above controls */
            padding: 16px !important;
        }
        
        /* Ensure chat messages area adapts to container resize */
        .chat-messages {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
            overflow-y: auto;     /* FIXED: Allow vertical scrolling */
            overflow-x: hidden;   /* Keep horizontal hidden */
            padding: 16px; /* Add padding back to the messages container */
        }
        
        /* Chat input area styling to stay at bottom of blue outline */
        .chat-interface > div:last-child,
        .chat-interface .input-container {
            flex-shrink: 0 !important; /* Keep at fixed size */
            margin-top: auto !important; /* Push to bottom */
            position: sticky !important; /* Stick to bottom */
            bottom: 0 !important; /* At the very bottom */
            background: #18181b !important; /* Match container background */
            border-top: 1px solid #333 !important; /* Subtle separator */
            padding: 12px !important; /* Consistent padding */
            z-index: 10 !important; /* Ensure it's above other elements */
        }
        
        /* Ensure chat messages are visible */
        .main-chatbot .message,
        .main-chatbot .user-message,
        .main-chatbot .bot-message,
        #chatbot .message,
        #chatbot .user-message,
        #chatbot .bot-message {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            background: transparent !important;
            color: #00ff00 !important; /* Green text */
            font-size: 14pt !important;
            line-height: 1.6 !important;
            margin: 8px 0 !important;
            padding: 8px !important;
        }
        
        /* Chat input and control buttons repositioned to bottom edge of blue outline */
        .chat-interface .input-container,
        .chat-interface > div:last-child,
        .chat-interface .gradio-button,
        .chat-interface button {
            flex-shrink: 0 !important; /* Keep buttons at fixed height */
            position: relative !important; /* Allow normal flow within sticky container */
            background: #18181b !important; /* Match chat container background */
            border: none !important;
            margin: 4px !important; /* Small margins between buttons */
            z-index: 100 !important;
            order: 999 !important; /* Force to bottom */
        }
        
        /* Ensure control buttons stay properly positioned */
        .chat-interface .input-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            justify-content: space-between;
        }
        
        /* Force proper button positioning */
        .chat-interface button {
            flex-shrink: 0;
        }
        
        /* Additional Gradio Chat Interface Fixes */
        
        /* Force chat messages to be visible - plain text without bubbles/containers */
        .chatbot .message-bubble,
        .chatbot .chat-bubble,
        .chatbot .bubble {
            background: transparent !important;
            border: none !important;
            color: #00ff00 !important; /* Green text */
            font-size: 14pt !important;
            padding: 0 !important;
            margin: 2px 0 !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        
        /* Gradio specific message styling */
        .gr-chatbot,
        .gr-chatbot .message,
        .gr-chatbot .user-message,
        .gr-chatbot .bot-message {
            background: transparent !important;
            color: #ffffff !important;
            font-size: 14pt !important;
            line-height: 1.6 !important;
        }
        
        /* Hide Gradio avatars */
        .gr-chatbot .avatar,
        .gr-chatbot .message-avatar,
        .gr-chatbot img[alt="avatar"] {
            display: none !important;
        }
        
        /* Force message content to be displayed */
        .chatbot .message-content,
        .chatbot .text-content,
        .chatbot .markdown,
        .chatbot .md {
            display: block !important;
            color: #00ff00 !important; /* Green text */
            font-size: 14pt !important;
            background: transparent !important;
        }
        
        /* Chat Interface Button Styling - Override universal for specific actions */
        /* Destructive chat actions get red styling */
        button[aria-label*="Clear"], 
        button[aria-label*="Undo"] {
            background: transparent !important;
            color: #dc2626 !important;
            border: 2px solid #dc2626 !important;
        }
        
        button[aria-label*="Clear"]:hover, 
        button[aria-label*="Undo"]:hover {
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%) !important;
            color: #e0e0e0 !important;
            border-color: #b91c1c !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(220, 38, 38, 0.3) !important;
        }
        
        /* All other chat buttons inherit universal green styling from above */
        
        /* Mode Selector Styling - Exact Match to Document Library Actions Filter Buttons */
        .mode-selector {
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
            width: 100% !important;
            align-items: stretch !important;
        }
        
        /* Mode Selector Button Styling */
        .mode-selector label {
            background: transparent !important;
            border: 2px solid #8BC34A !important;
            color: #8BC34A !important;
            padding: 8px 16px !important;
            border-radius: 12px !important;
            font-size: 16px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            text-transform: uppercase !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            margin: 2px !important;
            box-shadow: 0 0 5px rgba(139, 195, 74, 0.3) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: calc(50% - 8px) !important;
            flex: 0 0 calc(50% - 8px) !important;
            box-sizing: border-box !important;
            min-height: 48px !important;
            height: auto !important;
            /* FORCE OVERRIDE of universal button styles */
            background: transparent !important;
            border: 2px solid #8BC34A !important;
            color: #8BC34A !important;
        }
        
        .mode-selector label:hover {
            border-color: #0077BE !important;
            color: #0077BE !important;
            background: rgba(0, 119, 190, 0.1) !important;
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.4) !important;
        }
        
        /* CRITICAL: Override the universal * selector for mode-selector labels */
        .mode-selector label,
        .mode-selector label * {
            color: #8BC34A !important;
        }
        
        .mode-selector label:hover,
        .mode-selector label:hover * {
            color: #0077BE !important;
        }
        
        .mode-selector input[type="radio"]:checked + label {
            background: #0077BE !important;
            border-color: #0077BE !important;
            color: #ffffff !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
        }
        
        /* Dynamic Button States - Active Mode (Blue) - Higher specificity */
        .mode-selector input[type="radio"] + label.mode-active,
        .mode-selector input[type="radio"]:checked + label.mode-active,
        .mode-selector .mode-active,
        .mode-selector .mode-active * {
            background: #0077BE !important;
            border-color: #0077BE !important;
            color: #ffffff !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
            transition: all 0.3s ease !important;
        }
        
        /* Dynamic Button States - Inactive Mode (Green) - Higher specificity */
        .mode-selector input[type="radio"] + label.mode-inactive,
        .mode-selector input[type="radio"]:not(:checked) + label.mode-inactive,
        .mode-selector .mode-inactive,
        .mode-selector .mode-inactive * {
            background: #1e1e1e !important;
            border-color: #8BC34A !important;
            color: #8BC34A !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        /* Hover effects for dynamic buttons */
        .mode-selector .mode-inactive:hover,
        .mode-selector .mode-inactive:hover * {
            color: #0077BE !important;
            border-color: #0077BE !important;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3) !important;
        }
        
        /* Ensure active mode always stays blue - override checked state */
        .mode-selector input[type="radio"]:checked + label.mode-active {
            background: #0077BE !important;
            border-color: #0077BE !important;
            color: #ffffff !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
        }
        
        /* Hide radio button inputs */
        .mode-selector input[type="radio"] {
            display: none !important;
        }
        
        /* Advanced Settings Styling */
        .modern-slider {
            background: #18181b !important;
            border-radius: 8px !important;
            padding: 12px !important;
            border: 2px solid #333 !important;
        }
        
        .modern-slider .gr-slider {
            background: #0077BE !important;
        }
        
        .modern-slider .gr-slider::-webkit-slider-thumb {
            background: #8BC34A !important;
            border: 2px solid #689F38 !important;
            border-radius: 50% !important;
            width: 18px !important;
            height: 18px !important;
        }
        
        /* Accordion Styling - Standardized with Document Library Actions */
        .gradio-accordion {
            background: #18181b !important;
            border: 2px solid #333 !important;
            border-radius: 8px !important;
            margin: 8px 0 !important;
        }
        
        .gradio-accordion .label-wrap {
            background: #232526 !important;
            color: #0077BE !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 12px 16px !important;
            border-radius: 6px 6px 0 0 !important;
        }
        
        .gradio-accordion[open] .label-wrap {
            border-bottom: 2px solid #333 !important;
        }
        
        /* Checkbox Styling - Keep functional */
        input[type="checkbox"] {
            accent-color: #8BC34A !important;
            transform: scale(1.5) !important;
            cursor: pointer !important;
            margin-right: 8px !important;
        }
        
        /* Checkbox label styling - Standardized */
        .gradio-checkbox label {
            color: #8BC34A !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            padding: 8px 0 !important;
        }
        
        .gradio-checkbox label:hover {
            color: #7CB342 !important;
        }
        
        /* Dropdown Styling - Standardized with consistent sizing */
        .gradio-dropdown,
        select {
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 12px 20px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            min-height: 48px !important;
        }
        
        .gradio-dropdown:hover,
        select:hover {
            background: linear-gradient(135deg, #8BC34A 0%, #7CB342 100%) !important;
            color: #e0e0e0 !important;
            border-color: #689F38 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(139, 195, 74, 0.3) !important;
        }
        
        .gradio-dropdown:focus,
        select:focus {
            background: linear-gradient(135deg, #8BC34A 0%, #7CB342 100%) !important;
            color: #e0e0e0 !important;
            border-color: #689F38 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(139, 195, 74, 0.3) !important;
        }
        
        /* Advanced Settings Radio Buttons - Functional with custom styling */
        .gradio-radio label {
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 2px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 0 5px rgba(139, 195, 74, 0.3) !important;
            position: relative !important;
            min-width: calc(50% - 8px) !important;
            flex: 0 0 calc(50% - 8px) !important;
            box-sizing: border-box !important;
            height: auto !important;
            min-height: 32px !important;
        }
        
        .gradio-radio label:hover {
            border-color: #0077BE !important;
            color: #0077BE !important;
            background: rgba(0, 119, 190, 0.1) !important;
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.4) !important;
        }
        
        .gradio-radio input[type="radio"]:checked + label {
            background: #0077BE !important;
            border-color: #0077BE !important;
            color: #ffffff !important;
            box-shadow: 0 0 15px rgba(0, 119, 190, 0.5) !important;
        }
        
        /* Hide radio buttons but keep them functional */
        .gradio-radio input[type="radio"] {
            position: absolute !important;
            opacity: 0 !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
        }
        
        /* Ensure radio buttons in accordions work */
        .gradio-accordion .gradio-radio input[type="radio"] {
            position: absolute !important;
            opacity: 0 !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
            pointer-events: auto !important;
        }
        
        .gradio-accordion .gradio-radio label {
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 11px !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 2px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 0 5px rgba(139, 195, 74, 0.3) !important;
            position: relative !important;
            pointer-events: auto !important;
            min-width: calc(50% - 8px) !important;
            flex: 0 0 calc(50% - 8px) !important;
            box-sizing: border-box !important;
            height: auto !important;
            min-height: 32px !important;
        }
        
        /* Text Input and Textarea Styling - REMOVED: Conflicted with specific .gradio-textbox rules */
        /* THESE RULES WERE OVERRIDING THE SEARCH BOX CONSISTENCY */
        /* Now using specific .gradio-textbox rules that match .doc-search-input exactly */
        /*
        textarea,
        input[type="text"],
        .gradio-textbox,
        .gradio-textarea {
            background: transparent !important;
            color: #8BC34A !important;
            border: 2px solid #8BC34A !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 12px 20px !important;
            transition: all 0.2s ease !important;
            min-height: 48px !important;
        }
        
        textarea:focus,
        input[type="text"]:focus,
        .gradio-textbox:focus,
        .gradio-textarea:focus {
            border-color: #0077BE !important;
            box-shadow: 0 0 0 2px rgba(0, 119, 190, 0.2) !important;
            outline: none !important;
        }
        
        textarea:hover,
        input[type="text"]:hover,
        .gradio-textbox:hover,
        .gradio-textarea:hover {
            border-color: #0077BE !important;
            box-shadow: 0 2px 8px rgba(0, 119, 190, 0.1) !important;
        }
        */

        /* Status Indicators */
        .status-indicator {
            background: #232526;
            border: 2px solid #0077BE;
            border-radius: 8px;
            padding: 20px 24px;
            font-size: 28px;
            color: #0077BE;
            font-weight: 800;
            line-height: 1.4;
            text-align: center;
        }
        
        /* Search Results - REMOVED: Not used in current sidebar implementation */
        
        /* Text Input Styling - CORRECTED: Now matches .doc-search-input exactly */
        .gradio-textbox {
            background: #232526 !important; /* MATCHES .doc-search-input */
            border: 2px solid #333 !important; /* CORRECTED: Now matches search box */
            border-radius: 6px !important; /* CORRECTED: Now matches search box */
            color: #e0e0e0 !important; /* MATCHES .doc-search-input */
            font-size: 14px !important; /* CORRECTED: Now matches search box */
            padding: 8px 12px !important; /* CORRECTED: Now matches search box */
        }
        
        .gradio-textbox:focus {
            border-color: #0077BE !important; /* MATCHES .doc-search-input:focus */
            box-shadow: 0 0 10px rgba(0, 119, 190, 0.3) !important; /* CORRECTED: Now matches search box */
        }
        
        /* Enhanced Chatbot Message Display */
        .chatbot,
        .main-chatbot,
        #chatbot {
            background: #000000 !important;
            border: 1px solid #333 !important;
            border-radius: 8px !important;
            padding: 20px !important;
            font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif !important;
            overflow-y: auto !important;
            max-height: 100% !important;
        }
        
        /* Remove avatar boxes and improve message layout - plain text without containers */
        .chatbot .message,
        .chatbot .bot,
        .chatbot .user,
        .chatbot .message-wrap,
        .chatbot .message-row {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 4px 0 !important;
            display: block !important;
            width: 100% !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        
        /* Hide avatar containers completely */
        .chatbot .avatar,
        .chatbot .avatar-container,
        .chatbot .message img,
        .chatbot img {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* Enhanced message text styling - readable colors and sizing */
        .chatbot .message-content,
        .chatbot .bot-message,
        .chatbot .user-message,
        .chatbot p,
        .chatbot div,
        .chatbot span,
        .chatbot .prose {
            color: #e0e0e0 !important; /* Light gray for readability */
            font-size: 14px !important;
            line-height: 1.6 !important;
            font-weight: 400 !important;
            background: transparent !important;
            border: none !important;
            margin: 8px 0 !important;
            padding: 8px !important;
            text-align: left !important;
            box-shadow: none !important;
            border-radius: 6px !important;
        }
        
        /* User message styling - distinct blue */
        .chatbot .user,
        .chatbot .user-message,
        .chatbot .message:nth-child(odd) {
            color: #0077BE !important;
            font-weight: 500 !important;
            background: rgba(0, 119, 190, 0.1) !important;
        }
        
        /* AI response styling - distinct green */
        .chatbot .bot,
        .chatbot .bot-message,
        .chatbot .message:nth-child(even) {
            color: #8BC34A !important;
            font-weight: 400 !important;
            background: rgba(139, 195, 74, 0.1) !important;
        }
        
        /* Hide labels and headers */
        .chatbot .label-wrap,
        .chatbot label,
        .chatbot .chatbot-header,
        .chatbot .chatbot-title,
        .chatbot .chatbot-subtitle {
            display: none !important;
        }
        
        /* Ensure messages are properly visible - plain text without containers */
        .chatbot .message-row,
        .chatbot .chat-message {
            display: block !important;
            width: 100% !important;
            background: transparent !important;
            min-height: auto !important;
            border: none !important;
            padding: 0 !important;
            margin: 2px 0 !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        
        /* Radio Button Styling */
        .gradio-radio {
            background: #232526 !important;
            border: 2px solid #0077BE !important;
            color: #e0e0e0 !important;
        }
        
        /* List Styling */
        .gradio-list {
            background: #232526 !important;
            border: 2px solid #0077BE !important;
            color: #e0e0e0 !important;
        }
        
        
        /* Custom Scrollbars */
        ::-webkit-scrollbar {
            width: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: #232526;
            border-radius: 6px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #0077BE;
            border-radius: 6px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #005A8B;
        }
        
        /* Fix scrollbar for Firefox */
        * {
            scrollbar-width: auto;
            scrollbar-color: #0077BE #232526;
        }
        
        /* Global Background */
        body {
            background: #000000 !important;
            color: #e0e0e0 !important;
        }
        
        /* Gradio Theme Override */
        .gradio-container {
            background: #000000 !important;
        }
        
        /* Fix white boxes around titles and headers */
        .header-container,
        .header-container *,
        .header-logo,
        .header-logo *,
        .header-title,
        .header-title *,
        .header-subtitle,
        .header-subtitle * {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        .header-container {
            border: 3px solid #0077BE !important;
        }
        .header-logo {
            border: none !important;
        }
        .header-title {
            border: none !important;
        }
        .header-subtitle {
            border: none !important;
        }
        
        /* Fix any remaining white backgrounds */
        .gradio-app,
        .gradio-app *,
        .main,
        .main *,
        .contain,
        .contain *,
        .gradio-interface,
        .gradio-interface * {
            background-color: #000000 !important;
        }
        
        /* Override any dark backgrounds */
        .gradio-app,
        .gradio-app *,
        .main,
        .main *,
        .contain,
        .contain * {
            background-color: #000000 !important;
        }
        
        /* Specific overrides for common elements */
        .gradio-block,
        .gradio-group,
        .gradio-row,
        .gradio-column {
            background-color: #000000 !important;
        }
        
        /* Fix any iframe or embedded content */
        iframe {
            background-color: #000000 !important;
        }
        
        /* Chat messages - clean white text without backgrounds - plain text display */
        .message,
        .message * {
            background-color: transparent !important;
            color: #ffffff !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 2px 0 !important;
            border-radius: 0 !important;
        }
        
        .message.user,
        .message.user * {
            background-color: transparent !important;
            color: #8BC34A !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 2px 0 !important;
            border-radius: 0 !important;
        }
        
        .message.bot,
        .message.bot * {
            background-color: transparent !important;
            color: #ffffff !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 2px 0 !important;
            border-radius: 0 !important;
        }
        
        /* Fix input areas */
        .input-container {
            background: #232526 !important;
        }
        
        .input-container input,
        .input-container textarea {
            background: #232526 !important;
            border: 2px solid #333 !important;
            color: #e0e0e0 !important;
            font-size: 16px !important;
            min-height: 84px !important; /* Doubled from default ~42px */
        }
        
        /* Specifically target chat interface textarea */
        .chat-interface textarea,
        .chat-messages textarea,
        textarea[data-testid="textbox"] {
            min-height: 84px !important; /* Doubled from default ~42px */
            height: 84px !important;
            max-height: 200px !important; /* Allow some expansion but not too much */
        }
        
        /* Fix all gradio components */
        .gradio-block {
            background: #000000 !important;
        }
        
        .gradio-group {
            background: #000000 !important;
        }
        
        .gradio-row {
            background: #000000 !important;
        }
        
        .gradio-column {
            background: #000000 !important;
        }
        
        /* Ensure proper inheritance */
        .gradio-container * {
            background-color: #000000 !important;
        }
        
        .sidebar-container * {
            background-color: #000000 !important;
        }
        
        .chat-container * {
            background-color: #000000 !important;
        }
        
        /* Large, clear labels */
        label {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #0077BE !important;
            margin-bottom: 8px !important;
        }
        
        /* Better spacing for all elements */
        .gradio-block {
            margin-bottom: 24px !important;
        }
        
        /* Improved button spacing */
        button {
            margin: 8px 4px !important;
        }
        
        
        /* Better text readability */
        p, div, span {
            line-height: 1.6 !important;
        }
        
        /* Focus indicators for accessibility */
        *:focus {
            outline: 3px solid #0077BE !important;
            outline-offset: 2px !important;
        }
        
        /* High contrast mode support */
        @media (prefers-contrast: high) {
            .modern-button {
                border-width: 3px !important;
            }
            
            .sidebar-container,
            .chat-container {
                border-width: 3px !important;
            }
        }
        
        /* External Information Section Styling - Matching Chat Container */
        .external-info-section {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #0077BE;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
            height: auto; /* Auto height to wrap content */
            min-height: 500px; /* Same as chat */
            max-height: none; /* Remove height restriction for unlimited scrolling */
            display: flex;
            flex-direction: column;
            position: relative; /* For resize handle positioning */
            resize: vertical; /* Enable basic CSS resize as fallback */
            overflow: visible; /* Allow content to extend naturally */
            flex-shrink: 1; /* Allow shrinking */
            margin-top: 20px;
            padding: 20px;
        }
        
        /* Forum Directory Section Styling - Enhanced Security Theme */
        .forum-directory-section {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #ff6b35; /* Orange border for security/warning theme */
            box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
            height: auto;
            min-height: 400px;
            max-height: calc(100vh - 250px);
            display: flex;
            flex-direction: column;
            position: relative;
            resize: vertical;
            overflow: auto;
            flex-shrink: 1;
            margin-top: 20px;
            padding: 20px;
        }
        
        /* Forum Directory Content - Matching RSS Feed Beauty */
        .forum-directory-section .feed-content {
            background: transparent;
            color: #e0e0e0;
        }
        
        .forum-directory-section .feed-source-section {
            margin-bottom: 16px;
        }
        
        .forum-directory-section .feed-source-header {
            color: #FF6B35 !important;
            font-size: 18px !important;
            font-weight: bold !important;
            margin: 16px 0 8px 0 !important;
            padding: 8px 0 !important;
            border-bottom: 2px solid #FF6B35;
        }
        
        .forum-directory-section .feed-item {
            background: #1a1a1a !important;
            border-left: 3px solid #FF6B35 !important;
            border-radius: 6px !important;
            margin-bottom: 8px !important;
            padding: 8px !important;
            transition: all 0.2s ease !important;
        }
        
        .forum-directory-section .feed-item:hover {
            background: #2a2a2a !important;
            transform: translateX(4px) !important;
            box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2) !important;
        }
        
        .forum-directory-section .feed-item span:first-child {
            color: #FF6B35 !important;
            font-weight: bold !important;
            font-size: 16px !important;
            min-width: 120px !important;
        }
        
        .forum-directory-section .feed-item span:last-child {
            color: #cccccc !important;
            font-family: 'Courier New', monospace !important;
            font-size: 15px !important;
            flex: 1 !important;
        }
        
        /* Forum Content Styling */
        .forum-content {
            color: #e0e0e0;
            font-family: inherit;
        }
        
        .security-warning {
            animation: subtle-pulse 3s ease-in-out infinite;
        }
        
        @keyframes subtle-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.9; }
        }
        
        .forum-item {
            transition: all 0.2s ease;
        }
        
        .forum-item:hover {
            background: #2a2a2a !important;
            transform: translateX(2px);
        }
        
        .forum-item button {
            transition: all 0.2s ease;
            font-weight: bold;
        }
        
        /* CVE Tracking Section Styling - Enhanced Security Theme */
        .cve-tracking-section {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #0077BE; /* Blue border for CVE/security theme */
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
            height: auto;
            min-height: 400px;
            max-height: calc(100vh - 250px);
            display: flex;
            flex-direction: column;
            position: relative;
            resize: vertical;
            overflow: auto;
            flex-shrink: 1;
            margin-top: 20px;
            padding: 20px;
        }
        
        /* CVE Content - Matching RSS Feed Beauty */
        .cve-tracking-section .feed-content {
            background: transparent;
            color: #e0e0e0;
        }
        
        .cve-tracking-section .feed-source-section {
            margin-bottom: 16px;
        }
        
        .cve-tracking-section .feed-source-header {
            color: #0077BE !important;
            font-size: 18px !important;
            font-weight: bold !important;
            margin: 16px 0 8px 0 !important;
            padding: 8px 0 !important;
            border-bottom: 2px solid #0077BE;
        }
        
        .cve-tracking-section .feed-item {
            background: #1a1a1a !important;
            border-radius: 6px !important;
            margin-bottom: 12px !important;
            padding: 8px !important;
            transition: all 0.2s ease !important;
        }
        
        .cve-tracking-section .feed-item:hover {
            background: #2a2a2a !important;
            transform: translateX(4px) !important;
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.2) !important;
        }
        
        /* CVE Severity Color Coding */
        .cve-tracking-section .feed-item[data-severity="Critical"] {
            border-left: 3px solid #FF0000 !important;
        }
        
        .cve-tracking-section .feed-item[data-severity="High"] {
            border-left: 3px solid #FF6B35 !important;
        }
        
        .cve-tracking-section .feed-item[data-severity="Medium"] {
            border-left: 3px solid #FFA500 !important;
        }
        
        .cve-tracking-section .feed-item[data-severity="Low"] {
            border-left: 3px solid #FFFF00 !important;
        }
        
        /* CVE Severity Labels */
        .cve-severity-label {
            font-size: 12px !important;
            font-weight: bold !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            margin-right: 8px !important;
        }
        
        .cve-severity-critical {
            background: #FF0000 !important;
            color: white !important;
        }
        
        .cve-severity-high {
            background: #FF6B35 !important;
            color: white !important;
        }
        
        .cve-severity-medium {
            background: #FFA500 !important;
            color: black !important;
        }
        
        .cve-severity-low {
            background: #FFFF00 !important;
            color: black !important;
        }
        
        /* MITRE ATT&CK Section Styling - Enhanced Threat Intelligence Theme */
        .mitre-attack-section {
            background: #000000;
            border-radius: 12px;
            border: 3px solid #FF0000; /* Red border for threat intelligence theme */
            box-shadow: 0 4px 12px rgba(255, 0, 0, 0.3);
            height: auto;
            min-height: 400px;
            max-height: calc(100vh - 250px);
            display: flex;
            flex-direction: column;
            position: relative;
            resize: vertical;
            overflow: auto;
            flex-shrink: 1;
            margin-top: 20px;
            padding: 20px;
        }
        
        /* MITRE Content - Matching RSS Feed Beauty */
        .mitre-attack-section .feed-content {
            background: transparent;
            color: #e0e0e0;
        }
        
        .mitre-attack-section .feed-source-section {
            margin-bottom: 16px;
        }
        
        .mitre-attack-section .feed-source-header {
            color: #FF0000 !important;
            font-size: 18px !important;
            font-weight: bold !important;
            margin: 16px 0 8px 0 !important;
            padding: 8px 0 !important;
            border-bottom: 2px solid #FF0000;
        }
        
        .mitre-attack-section .feed-item {
            background: #1a1a1a !important;
            border-radius: 6px !important;
            margin-bottom: 12px !important;
            padding: 8px !important;
            transition: all 0.2s ease !important;
        }
        
        .mitre-attack-section .feed-item:hover {
            background: #2a2a2a !important;
            transform: translateX(4px) !important;
            box-shadow: 0 4px 12px rgba(255, 0, 0, 0.2) !important;
        }
        
        /* MITRE Tactic Color Coding */
        .mitre-attack-section .feed-item[data-tactic="Initial Access"] {
            border-left: 3px solid #FF0000 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Execution"] {
            border-left: 3px solid #FF6B35 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Persistence"] {
            border-left: 3px solid #FFA500 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Privilege Escalation"] {
            border-left: 3px solid #FFFF00 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Defense Evasion"] {
            border-left: 3px solid #00FF00 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Credential Access"] {
            border-left: 3px solid #00FFFF !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Discovery"] {
            border-left: 3px solid #0000FF !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Lateral Movement"] {
            border-left: 3px solid #FF00FF !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Collection"] {
            border-left: 3px solid #800080 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Command & Control"] {
            border-left: 3px solid #008000 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Exfiltration"] {
            border-left: 3px solid #800000 !important;
        }
        
        .mitre-attack-section .feed-item[data-tactic="Impact"] {
            border-left: 3px solid #FF0000 !important;
        }
        
        /* MITRE Tactic Labels */
        .mitre-tactic-label {
            font-size: 12px !important;
            font-weight: bold !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            margin-right: 8px !important;
        }
        
        .mitre-tactic-initial-access {
            background: #FF0000 !important;
            color: white !important;
        }
        
        .mitre-tactic-execution {
            background: #FF6B35 !important;
            color: white !important;
        }
        
        .mitre-tactic-persistence {
            background: #FFA500 !important;
            color: black !important;
        }
        
        .mitre-tactic-privilege-escalation {
            background: #FFFF00 !important;
            color: black !important;
        }
        
        .mitre-tactic-defense-evasion {
            background: #00FF00 !important;
            color: black !important;
        }
        
        .mitre-tactic-credential-access {
            background: #00FFFF !important;
            color: black !important;
        }
        
        .mitre-tactic-discovery {
            background: #0000FF !important;
            color: white !important;
        }
        
        .mitre-tactic-lateral-movement {
            background: #FF00FF !important;
            color: white !important;
        }
        
        .mitre-tactic-collection {
            background: #800080 !important;
            color: white !important;
        }
        
        .mitre-tactic-command-control {
            background: #008000 !important;
            color: white !important;
        }
        
        .mitre-tactic-exfiltration {
            background: #800000 !important;
            color: white !important;
        }
        
        .mitre-tactic-impact {
            background: #FF0000 !important;
            color: white !important;
        }
        }
        
        .forum-item button:hover {
            transform: scale(1.05);
            box-shadow: 0 2px 8px rgba(255, 107, 53, 0.4);
        }
        
        /* Copy Status Styling */
        .copy-status, .forum-status {
            min-height: 20px;
            display: flex;
            align-items: center;
        }
        
        /* Resize handles for new panels - Matching chat style */
        .internal-resize-handle,
        .external-resize-handle,
        .forum-resize-handle {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 20px;
            height: 20px;
            cursor: nw-resize;
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #0077BE 25%, #0077BE 50%, transparent 50%, transparent 75%, #0077BE 75%);
            background-size: 4px 4px;
            border-bottom-right-radius: 12px;
            opacity: 0.7;
            transition: opacity 0.2s ease;
            z-index: 10;
            user-select: none;
        }
        
        /* Forum resize handle - Orange theme */
        .forum-resize-handle {
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #ff6b35 25%, #ff6b35 50%, transparent 50%, transparent 75%, #ff6b35 75%);
        }
        
        .internal-resize-handle:hover,
        .external-resize-handle:hover,
        .forum-resize-handle:hover {
            opacity: 1;
        }
        
        .internal-resize-handle:hover,
        .external-resize-handle:hover {
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #00A3FF 25%, #00A3FF 50%, transparent 50%, transparent 75%, #00A3FF 75%);
        }
        
        .forum-resize-handle:hover {
            background: linear-gradient(-45deg, transparent 0%, transparent 25%, #ff8c69 25%, #ff8c69 50%, transparent 50%, transparent 75%, #ff8c69 75%);
        }
        
        .internal-resize-handle::after,
        .external-resize-handle::after {
            content: '';
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            background: linear-gradient(-45deg, transparent 30%, #0077BE 30%, #0077BE 40%, transparent 40%, transparent 60%, #0077BE 60%, #0077BE 70%, transparent 70%);
            background-size: 2px 2px;
            border-radius: 2px;
        }
        
        

        /* Hide Gradio's default close/minimize buttons */
        .gradio-container .close-btn,
        .gradio-container .minimize-btn,
        .gradio-container button[aria-label*="Close"],
        .gradio-container button[aria-label*="Minimize"],
        .gradio-container button[aria-label*="close"],
        .gradio-container button[aria-label*="minimize"],
        .gradio-container .close-button,
        .gradio-container .minimize-button,
        .gradio-container .header-close,
        .gradio-container .header-minimize,
        .gradio-container .interface-close,
        .gradio-container .interface-minimize,
        .gradio-container .top-right-controls,
        .gradio-container .top-controls,
        .gradio-container .header-controls,
        .gradio-container .interface-controls,
        .gradio-container .close,
        .gradio-container .minimize,
        .gradio-container .x-button,
        .gradio-container .close-x,
        .gradio-container .minimize-x {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        
        /* Hide any buttons with X content */
        .gradio-container button:contains("×"),
        .gradio-container button:contains("✕"),
        .gradio-container button:contains("✖"),
        .gradio-container button:contains("X"),
        .gradio-container button:contains("x") {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        
        /* Hide Gradio's "Use via API" / "Fake API" button - Comprehensive approach */
        .gradio-container a[href*="api"],
        .gradio-container button:contains("API"),
        .gradio-container button:contains("api"),
        .gradio-container button[aria-label*="API"],
        .gradio-container button[aria-label*="api"],
        .gradio-container .api-button,
        .gradio-container .use-api,
        .gradio-container .api-link,
        /* Target the specific fake API button from ChatInterface */
        .gradio-container button[id*="fake"],
        .gradio-container button[class*="fake"],
        .gradio-container #component-*[value="Fake API"],
        .gradio-container button[value="Fake API"],
        .gradio-container input[value="Fake API"],
        /* Hide any button that might contain "Fake API" text */
        .gradio-container *[text*="Fake API"],
        .gradio-container *[innerText*="Fake API"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
            width: 0 !important;
            height: 0 !important;
        }
        
        /* Hide top-right positioned close buttons */
        .gradio-container button[style*="position: absolute"],
        .gradio-container button[style*="top: 0"],
        .gradio-container button[style*="right: 0"],
        .gradio-container button[style*="top-right"],
        .gradio-container button[style*="position: fixed"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        </style>
        
        <script>
        // Enhanced Document Organization JavaScript Functions with Event Delegation
        function toggleSection(header) {
            const section = header.parentElement;
            const icon = header.querySelector('.collapsible-icon');
            const content = section.querySelector('.collapsible-content');
            
            if (!section || !icon || !content) {
                console.warn('toggleSection: required elements not found', {section, icon, content, header});
                return;
            }
            
            console.log('Toggling section:', section, 'Current collapsed state:', section.classList.contains('collapsed'));
            
            // Prevent double-clicking during animation
            if (section.classList.contains('expanding') || section.classList.contains('collapsing')) {
                return;
            }
            
            const isCollapsing = !section.classList.contains('collapsed');
            
            if (isCollapsing) {
                // Collapsing the section
                section.classList.add('collapsing');
                section.classList.remove('expanding');
                
                // Update icon immediately
                icon.textContent = '▶';
                
                // Start collapse animation
                setTimeout(() => {
                    section.classList.add('collapsed');
                    section.classList.remove('collapsing');
                }, 400); // Match CSS transition duration
                
            } else {
                // Expanding the section  
                section.classList.add('expanding');
                section.classList.remove('collapsing');
                section.classList.remove('collapsed');
                
                // Update icon immediately
                icon.textContent = '▼';
                
                // End expand animation
                setTimeout(() => {
                    section.classList.remove('expanding');
                }, 400); // Match CSS transition duration
            }
            
            // Enhanced visual feedback with pulse effect
            icon.style.color = '#00A3FF';
            icon.style.textShadow = '0 0 8px rgba(0, 163, 255, 0.8)';
            
            setTimeout(() => {
                icon.style.color = '';
                icon.style.textShadow = '';
            }, 400);
            
            console.log('Section toggle completed:', section.classList.contains('collapsed') ? 'collapsed' : 'expanded');
        }
        
        // Global event delegation for collapsible headers - TEMPORARILY DISABLED FOR DEBUGGING
        function setupEventDelegation() {
            // DISABLED: Commenting out to test if this is blocking dropdown functionality
            /*
            document.addEventListener('click', function(e) {
                // Debug logging for dropdown issues
                if (e.target.tagName === 'SELECT' || e.target.closest('select') || e.target.closest('[role="listbox"]') || e.target.closest('[role="combobox"]')) {
                    console.log('Dropdown click detected, allowing default behavior');
                    return;
                }
                
                // Skip if clicking on ANY form elements or Gradio components
                if (e.target.closest('input, select, button, textarea, [role="button"], [role="listbox"], [role="combobox"], [class*="dropdown"], [class*="gradio"], [class*="svelte"]')) {
                    console.log('Form element click detected, allowing default behavior');
                    return;
                }
                
                // Check if clicked element is a collapsible header or inside one
                const header = e.target.closest('.collapsible-header');
                if (header) {
                    console.log('Collapsible header click detected, preventing default');
                    e.preventDefault();
                    e.stopPropagation();
                    toggleSection(header);
                }
            });
            */
            console.log('Global event delegation DISABLED for dropdown debugging');
        }
        
        function toggleFolder(folderItem) {
            const content = folderItem.nextElementSibling;
            const icon = folderItem.querySelector('.collapsible-icon');
            
            if (content.style.display === 'none' || content.style.display === '') {
                content.style.display = 'block';
                icon.textContent = '▼';
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        }
        
        let activeFilters = ['all'];
        
        function toggleFilter(filterBtn) {
            const filterType = filterBtn.getAttribute('data-filter');
            
            // Handle 'all' filter specially
            if (filterType === 'all') {
                // Clear all other filters and activate 'all'
                document.querySelectorAll('.filter-tag').forEach(btn => btn.classList.remove('active'));
                filterBtn.classList.add('active');
                activeFilters = ['all'];
            } else {
                // Remove 'all' filter if it's active
                const allBtn = document.querySelector('.filter-tag[data-filter="all"]');
                if (allBtn) allBtn.classList.remove('active');
                
                // Toggle this filter
                if (filterBtn.classList.contains('active')) {
                    filterBtn.classList.remove('active');
                    activeFilters = activeFilters.filter(f => f !== filterType);
                } else {
                    filterBtn.classList.add('active');
                    activeFilters.push(filterType);
                }
                
                // If no filters are active, activate 'all'
                if (activeFilters.length === 0) {
                    if (allBtn) allBtn.classList.add('active');
                    activeFilters = ['all'];
                }
            }
            
            filterDocuments();
        }
        
        function filterDocuments() {
            const searchQuery = document.getElementById('doc-search')?.value.toLowerCase() || '';
            const documentItems = document.querySelectorAll('.document-item:not(.folder-item)');
            const folderItems = document.querySelectorAll('.folder-item');
            
            let visibleCounts = {};
            
            documentItems.forEach(item => {
                const filename = item.getAttribute('data-filename') || '';
                const filetype = item.getAttribute('data-type') || '';
                const itemText = item.textContent.toLowerCase();
                
                // Check if item matches search query
                const matchesSearch = searchQuery === '' || 
                    filename.toLowerCase().includes(searchQuery) || 
                    itemText.includes(searchQuery);
                
                // Check if item matches active filters
                let matchesFilter = false;
                if (activeFilters.includes('all')) {
                    matchesFilter = true;
                } else {
                    matchesFilter = activeFilters.some(filter => {
                        switch (filter) {
                            case 'pdf': return filetype === 'pdf';
                            case 'excel': return filetype === 'excel';
                            case 'word': return filetype === 'word';
                            case 'recent': return item.classList.contains('recent-doc-item');
                            case 'analyzed': return item.textContent.includes('analyzed');
                            case 'pending': return item.textContent.includes('pending');
                            default: return false;
                        }
                    });
                }
                
                // Show/hide item based on filters
                const shouldShow = matchesSearch && matchesFilter;
                item.style.display = shouldShow ? 'flex' : 'none';
                
                // Count visible items per folder
                if (shouldShow) {
                    const folder = item.closest('.folder-content')?.previousElementSibling;
                    if (folder && folder.classList.contains('folder-item')) {
                        const folderName = folder.getAttribute('data-folder');
                        visibleCounts[folderName] = (visibleCounts[folderName] || 0) + 1;
                    }
                }
            });
            
            // Update folder counts and visibility
            folderItems.forEach(folder => {
                const folderName = folder.getAttribute('data-folder');
                const count = visibleCounts[folderName] || 0;
                const folderContent = folder.nextElementSibling;
                
                // Update count in folder title
                const titleSpan = folder.querySelector('span:nth-child(2)');
                if (titleSpan) {
                    const baseName = folderName;
                    titleSpan.textContent = `${baseName} (${count})`;
                }
                
                // Hide folder if no visible items
                folder.style.display = count > 0 ? 'flex' : 'none';
                if (count === 0 && folderContent) {
                    folderContent.style.display = 'none';
                    const icon = folder.querySelector('.collapsible-icon');
                    if (icon) icon.textContent = '▶';
                }
            });
        }
        
        function selectDocument(docItem) {
            // Remove previous selection
            document.querySelectorAll('.document-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Add selection to clicked item
            docItem.classList.add('selected');
            
            // Store selected document info
            const filename = docItem.getAttribute('data-filename');
            console.log('Selected document:', filename);
        }
        
        function analyzeDocument(filename) {
            console.log('Analyzing document:', filename);
            // Add your analyze logic here
            alert(`Starting analysis of: ${filename}`);
        }
        
        function shareDocument(filename) {
            console.log('Sharing document:', filename);
            // Add your share logic here
            alert(`Sharing: ${filename}`);
        }
        
        function expandDocumentLibrary() {
            // Expand the Document Library section
            const docLibSection = document.querySelector('.collapsible-section');
            if (docLibSection && docLibSection.classList.contains('collapsed')) {
                const header = docLibSection.querySelector('.collapsible-header');
                if (header) toggleSection(header);
            }
            
            // Clear filters to show all documents
            document.querySelectorAll('.filter-tag').forEach(btn => btn.classList.remove('active'));
            const allBtn = document.querySelector('.filter-tag[data-filter="all"]');
            if (allBtn) allBtn.classList.add('active');
            activeFilters = ['all'];
            filterDocuments();
        }
        
        function startNewAnalysis() {
            console.log('Starting new analysis...');
            
            // Get selected documents or all documents
            const selectedDocs = document.querySelectorAll('.document-item.selected');
            if (selectedDocs.length === 0) {
                alert('Please select documents to analyze, or the system will analyze all documents.');
            } else {
                const filenames = Array.from(selectedDocs).map(doc => doc.getAttribute('data-filename')).join(', ');
                alert(`Starting analysis for: ${filenames}`);
            }
            
            // Show processing queue and expand it
            const queueSection = document.querySelector('.collapsible-section:has(#processing-queue-content)');
            if (queueSection && queueSection.classList.contains('collapsed')) {
                const header = queueSection.querySelector('.collapsible-header');
                if (header) toggleSection(header);
            }
        }
        
        function bulkProcess() {
            console.log('Starting bulk processing...');
            
            const totalDocs = document.querySelectorAll('.document-item:not(.folder-item)').length;
            if (totalDocs === 0) {
                alert('No documents available for bulk processing. Please upload documents first.');
                return;
            }
            
            const confirmation = confirm(`Start bulk processing for ${totalDocs} documents? This may take some time.`);
            if (confirmation) {
                alert(`Bulk processing started for ${totalDocs} documents. Check the Processing Queue for status updates.`);
                
                // Show processing queue
                const queueSection = document.querySelector('.collapsible-section:has(#processing-queue-content)');
                if (queueSection && queueSection.classList.contains('collapsed')) {
                    const header = queueSection.querySelector('.collapsible-header');
                    if (header) toggleSection(header);
                }
            }
        }
        
        function exportDocuments() {
            console.log('Exporting documents...');
            
            const selectedDocs = document.querySelectorAll('.document-item.selected');
            const exportCount = selectedDocs.length > 0 ? selectedDocs.length : document.querySelectorAll('.document-item:not(.folder-item)').length;
            
            if (exportCount === 0) {
                alert('No documents available for export. Please upload documents first.');
                return;
            }
            
            const formats = ['PDF Report', 'Excel Spreadsheet', 'JSON Data', 'CSV File'];
            const selectedFormat = prompt(`Choose export format for ${exportCount} documents:\n1. PDF Report\n2. Excel Spreadsheet\n3. JSON Data\n4. CSV File\n\nEnter number (1-4):`);
            
            if (selectedFormat && selectedFormat >= 1 && selectedFormat <= 4) {
                const formatName = formats[selectedFormat - 1];
                alert(`Preparing ${formatName} export for ${exportCount} documents. Download will start shortly.`);
            }
        }
        
        // Initialize collapsible sections and filters on page load
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM Content Loaded - Setting up collapsible sections');
            
            // Setup global event delegation first
            setupEventDelegation();
            
            // Initialize all collapsible sections with proper triangle states
            const initializeCollapsibleSections = () => {
                const sections = document.querySelectorAll('.collapsible-section');
                console.log('Initializing collapsible sections, found:', sections.length);
                
                sections.forEach((section, index) => {
                    const icon = section.querySelector('.collapsible-icon');
                    const header = section.querySelector('.collapsible-header');
                    const content = section.querySelector('.collapsible-content');
                    
                    console.log(`Section ${index}:`, {
                        section: section.classList.toString(),
                        hasIcon: !!icon,
                        hasHeader: !!header,
                        hasContent: !!content
                    });
                    
                    if (icon && header && content) {
                        // Ensure proper initial state
                        if (section.classList.contains('collapsed')) {
                            icon.textContent = '▶';
                            // Let CSS handle the transform via .collapsed .collapsible-icon
                        } else {
                            icon.textContent = '▼';
                            // Let CSS handle the transform (default state)
                        }
                        
                        // Remove any inline styles that might interfere with CSS
                        icon.style.transform = '';
                        icon.style.transition = '';
                        icon.style.color = '';
                        icon.style.textShadow = '';
                        
                        // Ensure header is clickable
                        header.style.cursor = 'pointer';
                        
                        // Add aria attributes for accessibility
                        const isCollapsed = section.classList.contains('collapsed');
                        header.setAttribute('role', 'button');
                        header.setAttribute('aria-expanded', !isCollapsed);
                        header.setAttribute('aria-controls', `collapsible-content-${index}`);
                        content.setAttribute('id', `collapsible-content-${index}`);
                        
                        console.log(`Section ${index} initialized:`, isCollapsed ? 'collapsed' : 'expanded');
                    } else {
                        console.warn(`Section ${index} missing required elements`);
                    }
                });
                
                console.log('All collapsible sections initialized successfully');
            };
            
            // Update document library content periodically
            const updateLibraryContent = () => {
                const libraryContainer = document.getElementById('document-library-content');
                if (libraryContainer) {
                    console.log('Library content update requested');
                }
            };
            
            // Pagination functionality
            window.changePage = function(page, filterType, searchQuery) {
                console.log('Changing page to:', page, 'Filter:', filterType, 'Search:', searchQuery);
                
                // Find filter buttons by their text content
                const buttons = Array.from(document.querySelectorAll('button'));
                let targetButton = null;
                
                switch(filterType) {
                    case 'all':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'All');
                        break;
                    case 'pdf':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'PDF');
                        break;
                    case 'excel':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'Excel');
                        break;
                    case 'word':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'Word');
                        break;
                    case 'recent':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'Recent');
                        break;
                    case 'analyzed':
                        targetButton = buttons.find(btn => btn.textContent.trim() === 'Analyzed');
                        break;
                }
                
                // Update search input if needed
                const searchInput = document.querySelector('input[placeholder*="Search documents"]');
                if (searchInput && searchQuery !== searchInput.value) {
                    searchInput.value = searchQuery;
                    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                
                // Trigger the filter button click
                if (targetButton) {
                    targetButton.click();
                } else {
                    console.warn('Could not find filter button for:', filterType);
                }
            };
            
            
            // Initialize sections and filters
            initializeCollapsibleSections();
            filterDocuments();
            
            
            // Re-initialize sections after delays to ensure all elements are loaded
            setTimeout(() => {
                console.log('Re-initializing after 500ms delay');
                initializeCollapsibleSections();
            }, 500);
            
            setTimeout(() => {
                console.log('Re-initializing after 1000ms delay');
                initializeCollapsibleSections();
            }, 1000);
            
            setTimeout(() => {
                console.log('Re-initializing after 2000ms delay');
                initializeCollapsibleSections();
            }, 2000);
        """
        
        with gr.Blocks(
            title=UI_TAB_TITLE,
            theme=gr.themes.Soft(primary_hue=slate),
            css=modern_css,
            head='<link rel="icon" type="image/x-icon" href="/favicon.ico?v=1752512250"><link rel="shortcut icon" type="image/x-icon" href="/favicon.ico?v=1752512250">',
        ) as blocks:
            
            # Modern Header
            with gr.Row(elem_classes=["header-container"]):
                with gr.Column(scale=1, elem_classes=["header-logo"]):
                    gr.Image(
                        value=str(INTERNAL_LOGO),
                        label=None,
                        show_label=False,
                        container=False,
                        height=150, # Increased from 100 to 150 for better prominence 
                        width=450, # Increased from 300 to 450 for better readability
                        elem_classes=["alpine-logo-img"]
                    )
                with gr.Column(scale=2):
                    # Add JavaScript for collapsible functionality
                    gr.HTML("""
                    <script>
                    // Enhanced Document Organization JavaScript Functions with Event Delegation
                    function toggleSection(header) {
                        const section = header.parentElement;
                        const icon = header.querySelector('.collapsible-icon');
                        const content = section.querySelector('.collapsible-content');
                        
                        if (!section || !icon || !content) {
                            console.warn('toggleSection: required elements not found', {section, icon, content, header});
                            return;
                        }
                        
                        console.log('Toggling section:', section, 'Current collapsed state:', section.classList.contains('collapsed'));
                        
                        // Prevent double-clicking during animation
                        if (section.classList.contains('expanding') || section.classList.contains('collapsing')) {
                            return;
                        }
                        
                        const isCollapsing = !section.classList.contains('collapsed');
                        
                        if (isCollapsing) {
                            // Collapsing the section
                            section.classList.add('collapsing');
                            section.classList.remove('expanding');
                            
                            // Update icon immediately
                            icon.textContent = '▶';
                            
                            // Start collapse animation
                            setTimeout(() => {
                                section.classList.add('collapsed');
                                section.classList.remove('collapsing');
                            }, 400); // Match CSS transition duration
                            
                        } else {
                            // Expanding the section  
                            section.classList.add('expanding');
                            section.classList.remove('collapsing');
                            section.classList.remove('collapsed');
                            
                            // Update icon immediately
                            icon.textContent = '▼';
                            
                            // End expand animation
                            setTimeout(() => {
                                section.classList.remove('expanding');
                            }, 400); // Match CSS transition duration
                        }
                        
                        // Enhanced visual feedback with pulse effect
                        icon.style.color = '#00A3FF';
                        icon.style.textShadow = '0 0 8px rgba(0, 163, 255, 0.8)';
                        
                        setTimeout(() => {
                            icon.style.color = '';
                            icon.style.textShadow = '';
                        }, 400);
                        
                        console.log('Section toggle completed:', section.classList.contains('collapsed') ? 'collapsed' : 'expanded');
                    }
                    
                    // Global event delegation for collapsible headers
                    function setupEventDelegation() {
                        // Remove any existing event listeners to prevent duplicates
                        if (window.collapsibleHandler) {
                            document.removeEventListener('click', window.collapsibleHandler);
                        }
                        
                        // DISABLED: Commenting out second event handler for dropdown debugging  
                        window.collapsibleHandler = function(e) {
                            // ALL EVENT HANDLING DISABLED FOR DROPDOWN TESTING
                            console.log('Second event handler called but DISABLED for dropdown debugging');
                            return; // Do nothing
                            
                            /*
                            // Debug logging for dropdown issues
                            if (e.target.tagName === 'SELECT' || e.target.closest('select') || e.target.closest('[role="listbox"]') || e.target.closest('[role="combobox"]')) {
                                console.log('Dropdown click detected (handler 2), allowing default behavior');
                                return;
                            }
                            
                            // Skip if clicking on ANY form elements or Gradio components
                            if (e.target.closest('input, select, button, textarea, [role="button"], [role="listbox"], [role="combobox"], [class*="dropdown"], [class*="gradio"], [class*="svelte"]')) {
                                console.log('Form element click detected (handler 2), allowing default behavior');
                                return;
                            }
                            
                            // Check if clicked element is a collapsible header or inside one
                            const header = e.target.closest('.collapsible-header');
                            if (header) {
                                console.log('Collapsible header click detected (handler 2), preventing default');
                                e.preventDefault();
                                e.stopPropagation();
                                toggleSection(header);
                            }
                            */
                        };
                        
                        document.addEventListener('click', window.collapsibleHandler);
                    }
                    
                    // Initialize collapsible sections
                    function initializeCollapsibleSections() {
                        const sections = document.querySelectorAll('.collapsible-section');
                        console.log('Initializing collapsible sections, found:', sections.length);
                        
                        sections.forEach((section, index) => {
                            const icon = section.querySelector('.collapsible-icon');
                            const header = section.querySelector('.collapsible-header');
                            const content = section.querySelector('.collapsible-content');
                            
                            console.log(`Section ${index}:`, {
                                section: section.classList.toString(),
                                hasIcon: !!icon,
                                hasHeader: !!header,
                                hasContent: !!content
                            });
                            
                            if (icon && header && content) {
                                // Ensure proper initial state
                                if (section.classList.contains('collapsed')) {
                                    icon.textContent = '▶';
                                    // Let CSS handle the transform via .collapsed .collapsible-icon
                                } else {
                                    icon.textContent = '▼';
                                    // Let CSS handle the transform (default state)
                                }
                                
                                // Remove any inline styles that might interfere with CSS
                                icon.style.transform = '';
                                icon.style.transition = '';
                                icon.style.color = '';
                                icon.style.textShadow = '';
                                
                                // Ensure header is clickable
                                header.style.cursor = 'pointer';
                                
                                // Add aria attributes for accessibility
                                const isCollapsed = section.classList.contains('collapsed');
                                header.setAttribute('role', 'button');
                                header.setAttribute('aria-expanded', !isCollapsed);
                                header.setAttribute('aria-controls', `collapsible-content-${index}`);
                                content.setAttribute('id', `collapsible-content-${index}`);
                                
                                console.log(`Section ${index} initialized:`, isCollapsed ? 'collapsed' : 'expanded');
                            } else {
                                console.warn(`Section ${index} missing required elements`);
                            }
                        });
                        
                        console.log('All collapsible sections initialized successfully');
                    }
                    
                    // Initialize when DOM is ready
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', function() {
                            console.log('DOM Content Loaded - Setting up collapsible sections');
                            
                            
                            setupEventDelegation();
                            initializeCollapsibleSections();
                            
                            
                            // Move AI configuration controls to sidebar
                            function moveAIControlsToSidebar() {
                                // Move AI mode selector
                                const modeSelector = document.querySelector('.mode-selector');
                                const aiModeTarget = document.getElementById('ai-mode-selector');
                                if (modeSelector && aiModeTarget) {
                                    aiModeTarget.appendChild(modeSelector.parentElement);
                                }
                                
                                // Move model selection
                                const modelSelector = document.querySelector('.model-selector');
                                const modelTarget = document.getElementById('model-selector');
                                if (modelSelector && modelTarget) {
                                    modelTarget.appendChild(modelSelector.parentElement);
                                }
                                
                                // Move writing style selector
                                const writingStyleSelector = document.querySelector('.writing-style-selector');
                                const writingStyleTarget = document.getElementById('writing-style-selector');
                                if (writingStyleSelector && writingStyleTarget) {
                                    writingStyleTarget.appendChild(writingStyleSelector.parentElement);
                                }
                                
                                // Move temperature control
                                const temperatureControl = document.querySelector('.temperature-control');
                                const temperatureTarget = document.getElementById('temperature-selector');
                                if (temperatureControl && temperatureTarget) {
                                    temperatureTarget.appendChild(temperatureControl.parentElement);
                                }
                            }
                            
                            // Chat Resize Functionality
                            function initializeChatResize() {
                                const resizeHandle = document.getElementById('chat-resize-handle');
                                const chatContainer = document.querySelector('.chat-container');
                                
                                if (!resizeHandle || !chatContainer) {
                                    console.log('Chat resize elements not found, retrying...');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                resizeHandle.addEventListener('mousedown', (e) => {
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(chatContainer).height, 10);
                                    chatContainer.classList.add('resizing');
                                    
                                    // Prevent text selection during resize
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'nw-resize';
                                    
                                    e.preventDefault();
                                });
                                
                                document.addEventListener('mousemove', (e) => {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    const newHeight = startHeight + deltaY;
                                    
                                    // Apply min/max height constraints
                                    const minHeight = 300;
                                    const maxHeight = window.innerHeight - 100;
                                    const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
                                    
                                    chatContainer.style.height = constrainedHeight + 'px';
                                    
                                    // Also update the chatbot height to maintain proper scrolling
                                    const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
                                    if (chatbot) {
                                        const headerHeight = 60; // Approximate header height
                                        const inputHeight = 120; // Increased for control buttons at bottom
                                        const availableHeight = constrainedHeight - headerHeight - inputHeight;
                                        chatbot.style.maxHeight = Math.max(400, availableHeight) + 'px';
                                        chatbot.style.height = 'auto'; // Allow flex growth
                                    }
                                });
                                
                                document.addEventListener('mouseup', () => {
                                    if (isResizing) {
                                        isResizing = false;
                                        chatContainer.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        // Mark as manually resized to prevent automatic adjustment
                                        chatContainer.dataset.manuallyResized = 'true';
                                        
                                        // Save the new height to localStorage for persistence
                                        const currentHeight = chatContainer.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('chatContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height on load
                                const savedHeight = localStorage.getItem('chatContainerHeight');
                                if (savedHeight) {
                                    chatContainer.style.height = savedHeight;
                                    
                                    // Also update chatbot height
                                    const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
                                    if (chatbot) {
                                        const headerHeight = 60;
                                        const inputHeight = 120; // Increased for control buttons at bottom
                                        const containerHeight = parseInt(savedHeight, 10);
                                        const availableHeight = containerHeight - headerHeight - inputHeight;
                                        chatbot.style.maxHeight = Math.max(400, availableHeight) + 'px';
                                        chatbot.style.height = 'auto'; // Allow flex growth
                                    }
                                }
                                
                                console.log('Chat resize functionality initialized');
                                return true;
                            }
                            
                            // Internal Information Resize Functionality
                            function initializeInternalResize() {
                                const resizeHandle = document.getElementById('internal-resize-handle');
                                const container = document.querySelector('.file-management-section');
                                
                                if (!resizeHandle || !container) {
                                    console.log('Internal resize elements not found, retrying...');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                resizeHandle.addEventListener('mousedown', (e) => {
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(container).height, 10);
                                    container.classList.add('resizing');
                                    
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'nw-resize';
                                    e.preventDefault();
                                });
                                
                                document.addEventListener('mousemove', (e) => {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    const newHeight = startHeight + deltaY;
                                    const minHeight = 500; // Same as chat
                                    const maxHeight = window.innerHeight - 100;
                                    const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
                                    
                                    container.style.height = constrainedHeight + 'px';
                                });
                                
                                document.addEventListener('mouseup', () => {
                                    if (isResizing) {
                                        isResizing = false;
                                        container.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        const currentHeight = container.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('internalContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height
                                const savedHeight = localStorage.getItem('internalContainerHeight');
                                if (savedHeight) {
                                    container.style.height = savedHeight;
                                }
                                
                                console.log('Internal resize functionality initialized');
                                return true;
                            }
                            
                            // External Information Resize Functionality
                            function initializeExternalResize() {
                                const resizeHandle = document.getElementById('external-resize-handle');
                                const container = document.querySelector('.external-info-section');
                                
                                if (!resizeHandle || !container) {
                                    console.log('External resize elements not found, retrying...');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                resizeHandle.addEventListener('mousedown', (e) => {
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(container).height, 10);
                                    container.classList.add('resizing');
                                    
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'nw-resize';
                                    e.preventDefault();
                                });
                                
                                document.addEventListener('mousemove', (e) => {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    const newHeight = startHeight + deltaY;
                                    const minHeight = 500; // Same as chat
                                    const maxHeight = window.innerHeight - 100;
                                    const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
                                    
                                    container.style.height = constrainedHeight + 'px';
                                });
                                
                                document.addEventListener('mouseup', () => {
                                    if (isResizing) {
                                        isResizing = false;
                                        container.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        const currentHeight = container.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('externalContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height
                                const savedHeight = localStorage.getItem('externalContainerHeight');
                                if (savedHeight) {
                                    container.style.height = savedHeight;
                                }
                                
                                console.log('External resize functionality initialized');
                                return true;
                            }
                            
                            function initializeForumResize() {
                                const container = document.querySelector('.forum-directory-section');
                                if (!container) {
                                    console.log('Forum container not found');
                                    return false;
                                }
                                
                                const handle = container.querySelector('.forum-resize-handle');
                                if (!handle) {
                                    console.log('Forum resize handle not found');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                handle.addEventListener('mousedown', function(e) {
                                    e.preventDefault();
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(container).height, 10);
                                    
                                    container.classList.add('resizing');
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'row-resize';
                                });
                                
                                document.addEventListener('mousemove', function(e) {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    let newHeight = startHeight + deltaY;
                                    
                                    // Enforce min and max height
                                    newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
                                    
                                    container.style.height = newHeight + 'px';
                                });
                                
                                document.addEventListener('mouseup', function(e) {
                                    if (isResizing) {
                                        isResizing = false;
                                        container.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        const currentHeight = container.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('forumContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height
                                const savedHeight = localStorage.getItem('forumContainerHeight');
                                if (savedHeight) {
                                    container.style.height = savedHeight;
                                }
                                
                                console.log('Forum resize functionality initialized');
                                return true;
                            }
                            
                            function initializeCveResize() {
                                const container = document.querySelector('.cve-tracking-section');
                                if (!container) {
                                    console.log('CVE container not found');
                                    return false;
                                }
                                
                                const handle = container.querySelector('.cve-resize-handle');
                                if (!handle) {
                                    console.log('CVE resize handle not found');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                handle.addEventListener('mousedown', function(e) {
                                    e.preventDefault();
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(container).height, 10);
                                    
                                    container.classList.add('resizing');
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'row-resize';
                                });
                                
                                document.addEventListener('mousemove', function(e) {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    let newHeight = startHeight + deltaY;
                                    
                                    // Enforce min and max height
                                    newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
                                    
                                    container.style.height = newHeight + 'px';
                                });
                                
                                document.addEventListener('mouseup', function(e) {
                                    if (isResizing) {
                                        isResizing = false;
                                        container.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        const currentHeight = container.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('cveContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height
                                const savedHeight = localStorage.getItem('cveContainerHeight');
                                if (savedHeight) {
                                    container.style.height = savedHeight;
                                }
                                
                                console.log('CVE resize functionality initialized');
                                return true;
                            }
                            
                            function initializeMitreResize() {
                                const container = document.querySelector('.mitre-attack-section');
                                if (!container) {
                                    console.log('MITRE container not found');
                                    return false;
                                }
                                
                                const handle = container.querySelector('.mitre-resize-handle');
                                if (!handle) {
                                    console.log('MITRE resize handle not found');
                                    return false;
                                }
                                
                                let isResizing = false;
                                let startY = 0;
                                let startHeight = 0;
                                
                                handle.addEventListener('mousedown', function(e) {
                                    e.preventDefault();
                                    isResizing = true;
                                    startY = e.clientY;
                                    startHeight = parseInt(window.getComputedStyle(container).height, 10);
                                    
                                    container.classList.add('resizing');
                                    document.body.style.userSelect = 'none';
                                    document.body.style.cursor = 'row-resize';
                                });
                                
                                document.addEventListener('mousemove', function(e) {
                                    if (!isResizing) return;
                                    
                                    const deltaY = e.clientY - startY;
                                    let newHeight = startHeight + deltaY;
                                    
                                    // Enforce min and max height
                                    newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
                                    
                                    container.style.height = newHeight + 'px';
                                });
                                
                                document.addEventListener('mouseup', function(e) {
                                    if (isResizing) {
                                        isResizing = false;
                                        container.classList.remove('resizing');
                                        document.body.style.userSelect = '';
                                        document.body.style.cursor = '';
                                        
                                        const currentHeight = container.style.height;
                                        if (currentHeight) {
                                            localStorage.setItem('mitreContainerHeight', currentHeight);
                                        }
                                    }
                                });
                                
                                // Restore saved height
                                const savedHeight = localStorage.getItem('mitreContainerHeight');
                                if (savedHeight) {
                                    container.style.height = savedHeight;
                                }
                                
                                console.log('MITRE resize functionality initialized');
                                return true;
                            }
                            
                            // Debug Document Management section visibility
                            function debugDocumentManagement() {
                                const docSection = document.querySelector('.file-management-section');
                                const uploadButton = document.getElementById('upload-files');
                                const fileList = document.querySelector('.file-list-display');
                                
                                console.log('Document Management Debug:');
                                console.log('- Section found:', !!docSection);
                                console.log('- Upload button found:', !!uploadButton);
                                console.log('- File list found:', !!fileList);
                                
                                if (docSection) {
                                    console.log('- Section visible:', window.getComputedStyle(docSection).display !== 'none');
                                    console.log('- Section height:', window.getComputedStyle(docSection).height);
                                    console.log('- Section position:', docSection.getBoundingClientRect());
                                    
                                    // Force visibility if hidden
                                    docSection.style.display = 'block';
                                    docSection.style.visibility = 'visible';
                                    docSection.style.opacity = '1';
                                }
                            }
                            
                            // Re-initialize after delays to handle dynamically loaded content
                            setTimeout(() => {
                                initializeCollapsibleSections();
                                moveAIControlsToSidebar();
                                initializeChatResize();
                                initializeInternalResize();
                                initializeExternalResize();
                                initializeCveResize();
                                initializeMitreResize();
                                debugDocumentManagement();
                            }, 500);
                            setTimeout(() => {
                                initializeCollapsibleSections();
                                moveAIControlsToSidebar();
                                initializeChatResize();
                                initializeInternalResize();
                                initializeExternalResize();
                                initializeCveResize();
                                initializeMitreResize();
                                debugDocumentManagement();
                            }, 1000);
                            setTimeout(() => {
                                initializeCollapsibleSections();
                                moveAIControlsToSidebar();
                                initializeChatResize();
                                initializeInternalResize();
                                initializeExternalResize();
                                initializeCveResize();
                                initializeMitreResize();
                                debugDocumentManagement();
                            }, 2000);
                        });
                    } else {
                        // DOM already loaded
                        console.log('DOM already loaded - Setting up collapsible sections immediately');
                        
                        
                        setupEventDelegation();
                        initializeCollapsibleSections();
                        
                        
                        // Move AI configuration controls to sidebar
                        function moveAIControlsToSidebar() {
                            // Move AI mode selector
                            const modeSelector = document.querySelector('.mode-selector');
                            const aiModeTarget = document.getElementById('ai-mode-selector');
                            if (modeSelector && aiModeTarget) {
                                aiModeTarget.appendChild(modeSelector.parentElement);
                            }
                            
                            // Move model selection
                            const modelSelector = document.querySelector('.model-selector');
                            const modelTarget = document.getElementById('model-selector');
                            if (modelSelector && modelTarget) {
                                modelTarget.appendChild(modelSelector.parentElement);
                            }
                            
                            // Move writing style selector
                            const writingStyleSelector = document.querySelector('.writing-style-selector');
                            const writingStyleTarget = document.getElementById('writing-style-selector');
                            if (writingStyleSelector && writingStyleTarget) {
                                writingStyleTarget.appendChild(writingStyleSelector.parentElement);
                            }
                            
                            // Move temperature control
                            const temperatureControl = document.querySelector('.temperature-control');
                            const temperatureTarget = document.getElementById('temperature-selector');
                            if (temperatureControl && temperatureTarget) {
                                temperatureTarget.appendChild(temperatureControl.parentElement);
                            }
                        }
                        
                        // Chat Resize Functionality
                        function initializeChatResize() {
                            const resizeHandle = document.getElementById('chat-resize-handle');
                            const chatContainer = document.querySelector('.chat-container');
                            
                            if (!resizeHandle || !chatContainer) {
                                console.log('Chat resize elements not found, retrying...');
                                return false;
                            }
                            
                            let isResizing = false;
                            let startY = 0;
                            let startHeight = 0;
                            
                            resizeHandle.addEventListener('mousedown', (e) => {
                                isResizing = true;
                                startY = e.clientY;
                                startHeight = parseInt(window.getComputedStyle(chatContainer).height, 10);
                                chatContainer.classList.add('resizing');
                                
                                // Prevent text selection during resize
                                document.body.style.userSelect = 'none';
                                document.body.style.cursor = 'nw-resize';
                                
                                e.preventDefault();
                            });
                            
                            document.addEventListener('mousemove', (e) => {
                                if (!isResizing) return;
                                
                                const deltaY = e.clientY - startY;
                                const newHeight = startHeight + deltaY;
                                
                                // Apply min/max height constraints
                                const minHeight = 300;
                                const maxHeight = window.innerHeight - 100;
                                const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
                                
                                chatContainer.style.height = constrainedHeight + 'px';
                                
                                // Also update the chatbot height to maintain proper scrolling
                                const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
                                if (chatbot) {
                                    const headerHeight = 60; // Approximate header height
                                    const inputHeight = 80; // Approximate input area height
                                    const availableHeight = constrainedHeight - headerHeight - inputHeight;
                                    chatbot.style.height = Math.max(980, availableHeight) + 'px';
                                }
                            });
                            
                            document.addEventListener('mouseup', () => {
                                if (isResizing) {
                                    isResizing = false;
                                    chatContainer.classList.remove('resizing');
                                    document.body.style.userSelect = '';
                                    document.body.style.cursor = '';
                                    
                                    // Save the new height to localStorage for persistence
                                    const currentHeight = chatContainer.style.height;
                                    if (currentHeight) {
                                        localStorage.setItem('chatContainerHeight', currentHeight);
                                    }
                                }
                            });
                            
                            // Restore saved height on load
                            const savedHeight = localStorage.getItem('chatContainerHeight');
                            if (savedHeight) {
                                chatContainer.style.height = savedHeight;
                                
                                // Also update chatbot height
                                const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
                                if (chatbot) {
                                    const headerHeight = 60;
                                    const inputHeight = 80;
                                    const containerHeight = parseInt(savedHeight, 10);
                                    const availableHeight = containerHeight - headerHeight - inputHeight;
                                    chatbot.style.height = Math.max(980, availableHeight) + 'px';
                                }
                            }
                            
                            console.log('Chat resize functionality initialized');
                            return true;
                        }
                        
                        // Debug Document Management section visibility
                        function debugDocumentManagement() {
                            const docSection = document.querySelector('.file-management-section');
                            const uploadButton = document.getElementById('upload-files');
                            const fileList = document.querySelector('.file-list-display');
                            
                            console.log('Document Management Debug:');
                            console.log('- Section found:', !!docSection);
                            console.log('- Upload button found:', !!uploadButton);
                            console.log('- File list found:', !!fileList);
                            
                            if (docSection) {
                                console.log('- Section visible:', window.getComputedStyle(docSection).display !== 'none');
                                console.log('- Section height:', window.getComputedStyle(docSection).height);
                                console.log('- Section position:', docSection.getBoundingClientRect());
                                
                                // Force visibility if hidden
                                docSection.style.display = 'block';
                                docSection.style.visibility = 'visible';
                                docSection.style.opacity = '1';
                            }
                        }
                        
                        // Remove Fake API Button - Comprehensive approach
                        function removeFakeApiButton() {
                            // Find and remove all potential fake API buttons
                            const selectors = [
                                'button:contains("Fake API")',
                                'button[value="Fake API"]',
                                'input[value="Fake API"]',
                                'button[id*="fake"]',
                                'button[class*="fake"]',
                                '*[text*="Fake API"]',
                                'a[href*="api"]',
                                'button:contains("API")',
                                'button:contains("api")',
                                '.api-button',
                                '.use-api',
                                '.api-link'
                            ];
                            
                            // Use custom jQuery-like contains selector
                            function getElementsByText(str, tag = '*') {
                                return Array.prototype.slice.call(document.querySelectorAll(tag))
                                    .filter(el => el.textContent && el.textContent.toLowerCase().includes(str.toLowerCase()));
                            }
                            
                            // Remove buttons containing "Fake API" text
                            const fakeApiButtons = getElementsByText('Fake API', 'button');
                            fakeApiButtons.forEach(btn => {
                                console.log('Found and removing Fake API button:', btn);
                                btn.style.display = 'none';
                                btn.style.visibility = 'hidden';
                                btn.style.opacity = '0';
                                btn.style.position = 'absolute';
                                btn.style.left = '-9999px';
                                btn.style.top = '-9999px';
                                btn.remove();
                            });
                            
                            // Remove any API-related buttons
                            const apiButtons = getElementsByText('API', 'button');
                            apiButtons.forEach(btn => {
                                if (btn.textContent.includes('API') && !btn.textContent.includes('SEND') && !btn.textContent.includes('MESSAGE')) {
                                    console.log('Found and removing API button:', btn);
                                    btn.style.display = 'none';
                                    btn.remove();
                                }
                            });
                            
                            console.log('Fake API button removal completed');
                        }
                        
                        // Set up MutationObserver to continuously remove fake API buttons
                        function setupFakeApiButtonWatcher() {
                            const observer = new MutationObserver(function(mutations) {
                                mutations.forEach(function(mutation) {
                                    if (mutation.type === 'childList') {
                                        mutation.addedNodes.forEach(function(node) {
                                            if (node.nodeType === 1) { // Element node
                                                // Check if the added node is a fake API button
                                                if (node.textContent && node.textContent.includes('Fake API')) {
                                                    console.log('Dynamically added Fake API button detected and removed:', node);
                                                    node.remove();
                                                }
                                                // Check if any child elements contain fake API buttons
                                                const fakeButtons = node.querySelectorAll ? node.querySelectorAll('*') : [];
                                                Array.from(fakeButtons).forEach(btn => {
                                                    if (btn.textContent && btn.textContent.includes('Fake API')) {
                                                        console.log('Child Fake API button detected and removed:', btn);
                                                        btn.remove();
                                                    }
                                                });
                                            }
                                        });
                                    }
                                });
                            });
                            
                            // Start observing
                            observer.observe(document.body, {
                                childList: true,
                                subtree: true
                            });
                            
                            console.log('Fake API button watcher started');
                        }
                        
                        // Re-initialize after delays
                        setTimeout(() => {
                            initializeCollapsibleSections();
                            moveAIControlsToSidebar();
                            initializeChatResize();
                            debugDocumentManagement();
                            removeFakeApiButton();
                            setupFakeApiButtonWatcher();
                        }, 500);
                        setTimeout(() => {
                            initializeCollapsibleSections();
                            moveAIControlsToSidebar();
                            initializeChatResize();
                            debugDocumentManagement();
                            removeFakeApiButton();
                        }, 1000);
                        // Initialize immediately, then again after delay for robustness
                        initializeResponsiveChatContainer();
                        initializeFilterButtons(); // ADDED: Set button defaults immediately
                        initializeChatInputKeyHandler(); // ADDED: Enable Enter key for sending messages
                        
                        setTimeout(() => {
                            initializeCollapsibleSections();
                            moveAIControlsToSidebar();
                            initializeChatResize();
                            debugDocumentManagement();
                            removeFakeApiButton();
                            initializeFilterButtons();
                            initializeResponsiveChatContainer(); // Run again after other components load
                            initializeChatInputKeyHandler(); // Run again after other components load
                        }, 1000); // IMPROVED: Reduced delay from 2000ms to 1000ms
                    }
                    
                    // Filter button active state management
                    function initializeFilterButtons() {
                        // Set initial active states
                        // Default: "All" button active in Document Library Actions
                        const allButton = Array.from(document.querySelectorAll('.filter-btn')).find(btn => btn.textContent.trim().startsWith('All'));
                        if (allButton) {
                            allButton.classList.add('filter-active');
                        }
                        
                        // Mode selection is now handled by radio buttons, not filter buttons
                        
                        // Add click listeners to all filter buttons
                        document.addEventListener('click', function(e) {
                            if (e.target.classList.contains('filter-btn')) {
                                // Helper function to check if button text starts with any of the given prefixes
                                const startsWithAny = (text, prefixes) => prefixes.some(prefix => text.startsWith(prefix));
                                
                                // Determine which section this button belongs to
                                const buttonText = e.target.textContent.trim();
                                const isDocumentLibraryButton = startsWithAny(buttonText, ['All', 'PDF', 'Excel', 'Word', 'Recent', 'Updated', 'Used in Chat', 'Other']);
                                // Mode buttons are now radio buttons, not filter buttons
                                const isModeButton = false;
                                
                                if (isDocumentLibraryButton) {
                                    // Remove filter-active class from Document Library buttons only
                                    document.querySelectorAll('.filter-btn').forEach(btn => {
                                        if (startsWithAny(btn.textContent.trim(), ['All', 'PDF', 'Excel', 'Word', 'Recent', 'Updated', 'Used in Chat', 'Other'])) {
                                            btn.classList.remove('filter-active');
                                        }
                                    });
                                // Mode selection is now handled by radio buttons, not filter buttons
                                
                                // Add filter-active class to clicked button
                                e.target.classList.add('filter-active');
                            }
                        });
                    }
                    
                    // Enable Enter key to send messages (Shift+Enter for new lines)
                    function initializeChatInputKeyHandler() {
                        // Find the chat input textarea
                        const chatInputTextarea = document.querySelector('.chat-input-textbox textarea');
                        if (chatInputTextarea) {
                            chatInputTextarea.addEventListener('keydown', function(e) {
                                if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
                                    e.preventDefault(); // Stop default new line behavior
                                    // Find and click the send button
                                    const sendButton = document.querySelector('.send-button');
                                    if (sendButton) {
                                        sendButton.click();
                                    }
                                }
                                // Shift+Enter, Ctrl+Enter, Alt+Enter still create new lines
                            });
                            console.log('Chat input Enter key handler initialized');
                        } else {
                            console.warn('Chat input textarea not found for Enter key handler');
                        }
                    }
                    
                    // Make chat container responsive to content size
                    function initializeResponsiveChatContainer() {
                        function adjustChatContainerHeight() {
                            const chatContainer = document.querySelector('.chat-container');
                            const chatMessages = document.querySelector('.chat-messages');
                            const chatInterface = document.querySelector('.chat-interface');
                            
                            // Skip adjustment if container was manually resized
                            if (chatContainer && chatContainer.dataset.manuallyResized === 'true') {
                                return;
                            }
                            
                            if (chatContainer && chatMessages) {
                                // Calculate content height
                                const messagesHeight = chatMessages.scrollHeight;
                                const controlsHeight = 120; // Approximate height for input controls
                                const padding = 32; // Container padding
                                const totalContentHeight = messagesHeight + controlsHeight + padding;
                                
                                // Set container height based on content, respecting min/max limits
                                const minHeight = 500;  // IMPROVED: Better minimum
                                const maxHeight = window.innerHeight - 200;  // IMPROVED: Use more viewport space
                                const newHeight = Math.max(minHeight, Math.min(totalContentHeight, maxHeight));
                                
                                chatContainer.style.height = newHeight + 'px';
                            }
                        }
                        
                        // Adjust on load and when content changes
                        adjustChatContainerHeight();
                        
                        // Use MutationObserver to watch for chat content changes
                        const chatMessages = document.querySelector('.chat-messages');
                        if (chatMessages) {
                            const observer = new MutationObserver(adjustChatContainerHeight);
                            observer.observe(chatMessages, { 
                                childList: true, 
                                subtree: true, 
                                characterData: true 
                            });
                        }
                        
                        // Adjust on window resize
                        window.addEventListener('resize', adjustChatContainerHeight);
                    }
                    
                    // Initialize all functions when DOM is ready
                    document.addEventListener('DOMContentLoaded', function() {
                        initializeResponsiveChatContainer();
                    });
                    
                    })(); // Close any remaining function scope
                    })(); // Close any remaining function scope
                    </script>
                    """)
                    
                    gr.HTML("""
                        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; gap: 4px; margin: 0; padding: 0;'>
                            <h1 class='header-title' style='margin: 0; padding: 0;'>Cybersecurity Intelligence</h1>
                            <p class='header-subtitle' style='margin: 0; padding: 0;'>Private AI Assistant</p>
                        </div>
                    """)
                with gr.Column(scale=1):
                    # Model Information and Document Count Display
                    def get_document_count():
                        try:
                            files = set()
                            category_counts = {
                                "financial": 0,
                                "policy": 0,
                                "compliance": 0,
                                "customer": 0,
                                "other": 0
                            }
                            
                            ingested_documents = self._ingest_service.list_ingested()
                            
                            for ingested_document in ingested_documents:
                                if (ingested_document.doc_metadata and 
                                    ingested_document.doc_metadata.get("file_name") and
                                    ingested_document.doc_metadata.get("file_name") != "[FILE NAME MISSING]"):
                                    file_name = ingested_document.doc_metadata["file_name"]
                                    files.add(file_name)
                                    
                                    # Categorize for detailed counting
                                    file_name_lower = file_name.lower()
                                    if any(term in file_name_lower for term in [
                                        'financial', 'budget', 'expense', 'revenue', 'profit', 'loss', 
                                        'income', 'balance', 'cash flow', 'quarterly', 'annual report'
                                    ]):
                                        category_counts["financial"] += 1
                                    elif any(term in file_name_lower for term in [
                                        'policy', 'procedure', 'guideline', 'manual', 'handbook', 
                                        'protocol', 'standard', 'regulation', 'code of conduct'
                                    ]):
                                        category_counts["policy"] += 1
                                    elif any(term in file_name_lower for term in [
                                        'compliance', 'audit', 'risk', 'regulatory', 'legal', 
                                        'sox', 'gdpr', 'hipaa', 'iso', 'certification'
                                    ]):
                                        category_counts["compliance"] += 1
                                    elif any(term in file_name_lower for term in [
                                        'customer', 'client', 'contact', 'crm', 'lead', 
                                        'prospect', 'account', 'sales', 'marketing'
                                    ]):
                                        category_counts["customer"] += 1
                                    else:
                                        category_counts["other"] += 1
                            
                            total_count = len(files)
                            logger.info(f"Document counts: Total={total_count}, Financial={category_counts['financial']}, "
                                      f"Policy={category_counts['policy']}, Compliance={category_counts['compliance']}, "
                                      f"Customer={category_counts['customer']}, Other={category_counts['other']}")
                            return total_count
                        except Exception as e:
                            logger.error(f"Error getting document count: {e}")
                            return 0
                    
                    def _analyze_document_types():
                        """Analyze uploaded documents to provide model recommendations."""
                        try:
                            files = self._list_ingested_files()
                            if not files:
                                return {
                                    'total_files': 0,
                                    'type_counts': {},
                                    'has_financial': False,
                                    'has_technical': False,
                                    'has_legal': False,
                                    'has_research': False
                                }
                            
                            # Document type analysis
                            type_counts = {
                                "PDF": 0,
                                "Word": 0,
                                "Excel": 0,
                                "PowerPoint": 0,
                                "Text": 0,
                                "Other": 0
                            }
                            
                            # Content type detection
                            has_financial = False
                            has_technical = False
                            has_legal = False
                            has_research = False
                            
                            for file_row in files:
                                if file_row and len(file_row) > 0:
                                    file_name = file_row[0]
                                    file_name_lower = file_name.lower()
                                    
                                    # File type counting
                                    if file_name.endswith('.pdf'):
                                        type_counts["PDF"] += 1
                                    elif file_name.endswith(('.doc', '.docx')):
                                        type_counts["Word"] += 1
                                    elif file_name.endswith(('.xls', '.xlsx', '.csv')):
                                        type_counts["Excel"] += 1
                                    elif file_name.endswith(('.ppt', '.pptx')):
                                        type_counts["PowerPoint"] += 1
                                    elif file_name.endswith(('.txt', '.md')):
                                        type_counts["Text"] += 1
                                    else:
                                        type_counts["Other"] += 1
                                    
                                    # Content type detection for model recommendations
                                    # Financial content
                                    if any(term in file_name_lower for term in [
                                        'financial', 'budget', 'expense', 'revenue', 'profit', 'loss', 
                                        'income', 'balance', 'cash flow', 'quarterly', 'annual report',
                                        'audit', 'tax', 'accounting', 'investment', 'portfolio'
                                    ]):
                                        has_financial = True
                                    
                                    # Technical content
                                    if any(term in file_name_lower for term in [
                                        'technical', 'specification', 'api', 'code', 'software', 
                                        'development', 'architecture', 'system', 'database',
                                        'algorithm', 'implementation', 'protocol', 'framework'
                                    ]):
                                        has_technical = True
                                    
                                    # Legal content
                                    if any(term in file_name_lower for term in [
                                        'legal', 'contract', 'agreement', 'terms', 'conditions',
                                        'policy', 'regulation', 'compliance', 'law', 'statute',
                                        'clause', 'liability', 'intellectual property', 'patent'
                                    ]):
                                        has_legal = True
                                    
                                    # Research content
                                    if any(term in file_name_lower for term in [
                                        'research', 'study', 'analysis', 'survey', 'report',
                                        'findings', 'data', 'statistics', 'methodology',
                                        'conclusion', 'hypothesis', 'experiment', 'trial'
                                    ]):
                                        has_research = True
                            
                            return {
                                'total_files': len(files),
                                'type_counts': type_counts,
                                'has_financial': has_financial,
                                'has_technical': has_technical,
                                'has_legal': has_legal,
                                'has_research': has_research
                            }
                            
                        except Exception as e:
                            logger.error(f"Error analyzing document types: {e}")
                            return {
                                'total_files': 0,
                                'type_counts': {},
                                'has_financial': False,
                                'has_technical': False,
                                'has_legal': False,
                                'has_research': False
                            }
                    
                    def get_feed_count():
                        try:
                            # Show the number of configured feed sources (not cached items)
                            # This reflects the actual feeds available in the system
                            return len(self._feeds_service.FEED_SOURCES)
                        except Exception as e:
                            logger.error(f"Error getting feed count: {e}")
                            return 0
                    
                    def get_model_status():
                        models = self._get_model_info()
                        doc_count = get_document_count()
                        feed_count = get_feed_count()
                        # Match the style of 'Private AI Assistant' (font-size: 18px, color: #e0e0e0, font-weight: 400)
                        return (
                            f"<div style='font-size: 18px; color: #e0e0e0; font-weight: 400; font-family: inherit; text-align: left;'>"
                            f"📄 {doc_count} Documents<br>"
                            f"📰 {feed_count} Feeds<br>"
                            f"🤖 {models['llm_model']}<br>"
                            f"🔍 {models['embedding_model']}<br>"
                            f"</div>"
                        )
                    
                    model_status = get_model_status()
                    
                    model_status_display = gr.HTML(f"""
                        <div style='display: flex; flex-direction: column; gap: 12px;'>
                            <div class='status-indicator'>{model_status}</div>
                        </div>
                    """)

            # Main Content Area - Sidebar and Chat
            with gr.Row(equal_height=True):
                # Left Sidebar - Document-Focused Design
                with gr.Column(scale=2, elem_classes=["sidebar-container"]):
                    
                    # Configuration section - Admin removed, user content always visible
                    
                    # User Configurations Content (existing functionality)
                    with gr.Group(visible=True) as user_content:
                        
                        # Document Library Actions Section with Search and Filters
                        with gr.Accordion("📚 Document Library Actions", open=True):
                            # Interactive Search Box
                            doc_search_input = gr.Textbox(
                                placeholder="🔍 Search documents...",
                                label="",
                                show_label=False,
                                elem_classes=["doc-search-input"],
                                container=False
                            )
                            
                            # Smart Grouping: Two rows of filters
                            # Get document counts for button badges
                            doc_counts = self._get_document_counts()
                            
                            gr.HTML("<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>📚 QUICK FILTERS</div>")
                            with gr.Row():
                                filter_all_btn = gr.Button(f"All ({doc_counts['all']})", elem_classes=["filter-btn"], size="sm")
                                filter_recent_btn = gr.Button(f"Recent ({doc_counts['recent']})", elem_classes=["filter-btn"], size="sm")
                                filter_updated_btn = gr.Button(f"Updated ({doc_counts['updated']})", elem_classes=["filter-btn"], size="sm")
                                filter_analyzed_btn = gr.Button(f"Used in Chat ({doc_counts['analyzed']})", elem_classes=["filter-btn"], size="sm")
                            
                            gr.HTML("<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 12px;'>📁 FILE TYPES</div>")
                            with gr.Row():
                                filter_pdf_btn = gr.Button(f"PDF ({doc_counts['pdf']})", elem_classes=["filter-btn"], size="sm")
                                filter_excel_btn = gr.Button(f"Excel ({doc_counts['excel']})", elem_classes=["filter-btn"], size="sm")
                                filter_word_btn = gr.Button(f"Word ({doc_counts['word']})", elem_classes=["filter-btn"], size="sm")
                                filter_other_btn = gr.Button(f"Other ({doc_counts['other']})", elem_classes=["filter-btn"], size="sm")
                            
                            # Status message display
                            filter_status_msg = gr.HTML(value="", elem_classes=["filter-status"])
                            
                            # Hidden state components for filters
                            current_filter_type = gr.Textbox(value="all", visible=False)
                            current_search_query = gr.Textbox(value="", visible=False)
                        
                        # Document Library Display Component
                        document_library_content = gr.HTML(
                            value=self._get_document_library_html(),
                            elem_classes=["document-library-display"]
                        )
                        
                        # Recent Documents section removed - functionality moved to Recent filter button
                        # Quick Actions section removed completely
                        
                        # AI Configuration Section (Simplified Two-Mode Selector)
                        with gr.Accordion("🤖 AI Mode Selection", open=True):
                            # Two-Mode Selection with Clear Descriptions
                            with gr.Group():
                                gr.HTML("""
                                <div style='color: #0077BE; font-weight: 600; margin-bottom: 12px; font-size: 16px;'>
                                    Select AI Assistant Mode
                                </div>
                                """)
                                
                                # Set General LLM as default for faster responses
                                default_mode = Modes.GENERAL_ASSISTANT.value  # General LLM as default
                                
                                # Add CSS for tooltips
                                gr.HTML("""
                                <style>
                                    .mode-selector .wrap {
                                        position: relative;
                                    }
                                    
                                    .mode-selector label {
                                        position: relative;
                                        cursor: pointer;
                                        padding: 8px 12px;
                                        border-radius: 6px;
                                        transition: all 0.2s ease;
                                    }
                                    
                                    .mode-selector label:hover {
                                        background-color: #f0f8ff;
                                        box-shadow: 0 2px 4px rgba(0,119,190,0.1);
                                    }
                                    
                                    .tooltip {
                                        position: absolute;
                                        background: #333;
                                        color: white;
                                        padding: 8px 12px;
                                        border-radius: 4px;
                                        font-size: 12px;
                                        white-space: nowrap;
                                        z-index: 1000;
                                        opacity: 0;
                                        visibility: hidden;
                                        transition: opacity 0.3s;
                                        bottom: 100%;
                                        left: 50%;
                                        transform: translateX(-50%);
                                        margin-bottom: 5px;
                                    }
                                    
                                    .tooltip::after {
                                        content: '';
                                        position: absolute;
                                        top: 100%;
                                        left: 50%;
                                        margin-left: -5px;
                                        border-width: 5px;
                                        border-style: solid;
                                        border-color: #333 transparent transparent transparent;
                                    }
                                    
                                    .mode-selector label:hover .tooltip {
                                        opacity: 1;
                                        visibility: visible;
                                    }
                                </style>
                                """)
                                

                                
                                gr.HTML("""
                                <script>
                                    // Dynamic Button Coloring for Mode Selection
                                    function updateModeButtonColors(activeMode) {
                                        console.log('Updating mode button colors for:', activeMode);
                                        const selectors = ['.mode-selector', '.chat-mode-selector'];
                                        
                                        selectors.forEach(selector => {
                                            const radioButtons = document.querySelectorAll(`${selector} input[type="radio"]`);
                                            const labels = document.querySelectorAll(`${selector} label`);
                                        
                                        // Force a slight delay to ensure DOM is ready
                                        setTimeout(() => {
                                            radioButtons.forEach((radio, index) => {
                                                const label = labels[index];
                                                if (label) {
                                                    // Remove existing dynamic classes
                                                    label.classList.remove('mode-active', 'mode-inactive');
                                                    
                                                    // Determine if this is the active mode
                                                    const isDocumentMode = radio.value.includes('RAG Mode');
                                                    const isGeneralMode = radio.value.includes('General LLM');
                                                    const shouldBeActive = (activeMode === 'document' && isDocumentMode) || 
                                                                          (activeMode === 'general' && isGeneralMode) ||
                                                                          radio.checked;
                                                    
                                                    console.log('Radio:', radio.value, 'Checked:', radio.checked, 'Should be active:', shouldBeActive);
                                                    
                                                    if (shouldBeActive) {
                                                        // Active mode - blue coloring
                                                        label.classList.add('mode-active');
                                                        console.log('Applied mode-active to:', radio.value);
                                                    } else {
                                                        // Inactive mode - green coloring
                                                        label.classList.add('mode-inactive');
                                                        console.log('Applied mode-inactive to:', radio.value);
                                                    }
                                                }
                                            });
                                        }, 10);
                                    }
                                    
                                    // Initialize button colors on page load
                                    function initializeModeButtonColors() {
                                        console.log('Initializing mode button colors');
                                        const selectors = ['.mode-selector', '.chat-mode-selector'];
                                        
                                        selectors.forEach(selector => {
                                            const checkedRadio = document.querySelector(`${selector} input[type="radio"]:checked`);
                                            if (checkedRadio) {
                                                console.log('Found checked radio:', checkedRadio.value);
                                                if (checkedRadio.value.includes('RAG Mode')) {
                                                    updateModeButtonColors('document');
                                                } else if (checkedRadio.value.includes('General LLM')) {
                                                    updateModeButtonColors('general');
                                                }
                                            }
                                        });
                                    }
                                    
                                    // Force button colors to persist - continuous monitoring
                                    function ensureButtonColorsPersist() {
                                        const selectors = ['.mode-selector', '.chat-mode-selector'];
                                        
                                        selectors.forEach(selector => {
                                            const checkedRadio = document.querySelector(`${selector} input[type="radio"]:checked`);
                                            if (checkedRadio) {
                                                const activeLabel = checkedRadio.nextElementSibling;
                                                if (activeLabel && !activeLabel.classList.contains('mode-active')) {
                                                    console.log('Forcing mode-active class on checked radio');
                                                    activeLabel.classList.remove('mode-inactive');
                                                    activeLabel.classList.add('mode-active');
                                                }
                                            }
                                        });
                                    }
                                    
                                    // Update description based on selected mode
                                    document.addEventListener('DOMContentLoaded', function() {
                                        const updateModeDescription = () => {
                                            const selectors = ['.mode-selector', '.chat-mode-selector'];
                                            const radioButtons = [];
                                            
                                            selectors.forEach(selector => {
                                                const buttons = document.querySelectorAll(`${selector} input[type="radio"]`);
                                                radioButtons.push(...buttons);
                                            });
                                            const docDesc = document.querySelector('.doc-mode-desc');
                                            const genDesc = document.querySelector('.general-mode-desc');
                                            
                                            radioButtons.forEach(radio => {
                                                radio.addEventListener('change', function() {
                                                    // Hide any open help sections when switching modes
                                                    const helpSections = document.querySelectorAll('[id$="-help"]');
                                                    helpSections.forEach(section => section.style.display = 'none');
                                                    
                                                    if (this.value.includes('RAG Mode')) {
                                                        docDesc.style.display = 'block';
                                                        genDesc.style.display = 'none';
                                                        updateContextualSuggestions('document');
                                                        updateModeButtonColors('document');
                                                        if (typeof toggleModeControls === 'function') {
                                                            toggleModeControls('document');
                                                        }
                                                    } else if (this.value.includes('General LLM')) {
                                                        docDesc.style.display = 'none';
                                                        genDesc.style.display = 'block';
                                                        updateContextualSuggestions('general');
                                                        updateModeButtonColors('general');
                                                        if (typeof toggleModeControls === 'function') {
                                                            toggleModeControls('general');
                                                        }
                                                    }
                                                });
                                            });
                                            
                                            // Set initial state
                                            const checkedRadio = document.querySelector('.mode-selector input[type="radio"]:checked');
                                            if (checkedRadio) {
                                                if (checkedRadio.value.includes('Document Assistant')) {
                                                    docDesc.style.display = 'block';
                                                    genDesc.style.display = 'none';
                                                    updateContextualSuggestions('document');
                                                    updateModeButtonColors('document');
                                                    if (typeof toggleModeControls === 'function') {
                                                        toggleModeControls('document');
                                                    }
                                                } else {
                                                    docDesc.style.display = 'none';
                                                    genDesc.style.display = 'block';
                                                    updateContextualSuggestions('general');
                                                    updateModeButtonColors('general');
                                                    if (typeof toggleModeControls === 'function') {
                                                        toggleModeControls('general');
                                                    }
                                                }
                                            }
                                            
                                            // Initialize button colors on page load
                                            initializeModeButtonColors();
                                            
                                            // Ensure button colors are applied after DOM is fully rendered
                                            setTimeout(() => {
                                                initializeModeButtonColors();
                                                ensureButtonColorsPersist();
                                            }, 100);
                                            
                                            // Continuous monitoring to ensure colors persist
                                            setInterval(() => {
                                                ensureButtonColorsPersist();
                                            }, 500);
                                        };
                                        
                                        // Add tooltips to radio button labels
                                        const addTooltips = () => {
                                            const labels = document.querySelectorAll('.mode-selector label');
                                            labels.forEach(label => {
                                                const input = label.querySelector('input');
                                                if (input && !label.querySelector('.tooltip')) {
                                                    const tooltip = document.createElement('div');
                                                    tooltip.className = 'tooltip';
                                                    
                                                    if (input.value.includes('Document Assistant')) {
                                                        tooltip.textContent = 'Search your documents for specific information and analysis';
                                                    } else if (input.value.includes('General LLM')) {
                                                        tooltip.textContent = 'Quick answers using AI knowledge - no document search';
                                                    }
                                                    
                                                    label.appendChild(tooltip);
                                                }
                                            });
                                        };
                                        
                                        // Call immediately and after delays to ensure DOM is ready
                                        updateModeDescription();
                                        addTooltips();
                                        setTimeout(() => {
                                            updateModeDescription();
                                            addTooltips();
                                        }, 100);
                                        setTimeout(() => {
                                            updateModeDescription();
                                            addTooltips();
                                        }, 500); // Additional delay for Gradio initialization
                                    });
                                    
                                    // Mode-specific controls visibility and functionality
                                    function toggleModeControls(mode) {
                                        const generalControls = document.querySelector('[data-testid*="general_controls"]') || 
                                                               document.querySelector('div:has(> div:contains("General LLM Tools"))');
                                        const documentControls = document.querySelector('[data-testid*="document_controls"]') ||
                                                                document.querySelector('div:has(> div:contains("Document Assistant Tools"))');
                                        
                                        if (mode === 'general') {
                                            if (generalControls) generalControls.style.display = 'block';
                                            if (documentControls) documentControls.style.display = 'none';
                                        } else if (mode === 'document') {
                                            if (generalControls) generalControls.style.display = 'none';
                                            if (documentControls) documentControls.style.display = 'block';
                                        }
                                    }
                                    
                                    // Keyboard shortcuts
                                    document.addEventListener('keydown', function(e) {
                                        // Ctrl/Cmd + 1 = Document Assistant
                                        if ((e.ctrlKey || e.metaKey) && e.key === '1') {
                                            e.preventDefault();
                                            const docRadio = document.querySelector('input[value*="Document Assistant"]');
                                            if (docRadio) {
                                                docRadio.click();
                                                showKeyboardShortcutFeedback('Document Assistant Mode');
                                            }
                                        }
                                        // Ctrl/Cmd + 2 = General Assistant  
                                        else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
                                            e.preventDefault();
                                            const genRadio = document.querySelector('input[value*="General Assistant"]');
                                            if (genRadio) {
                                                genRadio.click();
                                                showKeyboardShortcutFeedback('General Assistant Mode');
                                            }
                                        }
                                        // Ctrl/Cmd + / = Show keyboard shortcuts help
                                        else if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                                            e.preventDefault();
                                            showKeyboardShortcuts();
                                        }
                                    });
                                    
                                    function showKeyboardShortcutFeedback(mode) {
                                        // Create temporary feedback notification
                                        const feedback = document.createElement('div');
                                        feedback.style.cssText = `
                                            position: fixed; top: 20px; right: 20px; z-index: 9999;
                                            background: #4CAF50; color: white; padding: 12px 16px;
                                            border-radius: 6px; font-size: 14px; font-weight: 500;
                                            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                            transform: translateX(100%); transition: transform 0.3s ease;
                                        `;
                                        feedback.textContent = `Switched to ${mode}`;
                                        document.body.appendChild(feedback);
                                        
                                        setTimeout(() => feedback.style.transform = 'translateX(0)', 100);
                                        setTimeout(() => {
                                            feedback.style.transform = 'translateX(100%)';
                                            setTimeout(() => document.body.removeChild(feedback), 300);
                                        }, 2000);
                                    }
                                    
                                    function showKeyboardShortcuts() {
                                        // Create keyboard shortcuts modal
                                        const modal = document.createElement('div');
                                        modal.style.cssText = `
                                            position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 10000;
                                            background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
                                        `;
                                        
                                        const content = document.createElement('div');
                                        content.style.cssText = `
                                            background: white; padding: 24px; border-radius: 12px; max-width: 400px;
                                            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                                        `;
                                        
                                        content.innerHTML = `
                                            <h3 style="margin: 0 0 16px 0; color: #333;">⌨️ Keyboard Shortcuts</h3>
                                            <div style="line-height: 1.6; color: #555;">
                                                <div><strong>Ctrl/Cmd + 1</strong> - Document Assistant Mode</div>
                                                <div><strong>Ctrl/Cmd + 2</strong> - General Assistant Mode</div>
                                                <div><strong>Ctrl/Cmd + /</strong> - Show this help</div>
                                                <div style="margin-top: 12px; font-size: 13px; color: #888;">
                                                    Click anywhere outside to close
                                                </div>
                                            </div>
                                        `;
                                        
                                        modal.appendChild(content);
                                        document.body.appendChild(modal);
                                        
                                        modal.addEventListener('click', function(e) {
                                            if (e.target === modal) {
                                                document.body.removeChild(modal);
                                            }
                                        });
                                    }
                                    
                                    // Mode confirmation dialog functionality
                                    let pendingModeSwitch = null;
                                    
                                    function showModeConfirmation(targetMode) {
                                        const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
                                        if (confirmDialog) {
                                            confirmDialog.style.display = 'block';
                                            pendingModeSwitch = targetMode;
                                        }
                                    }
                                    
                                    // Handle confirmation dialog buttons
                                    document.addEventListener('click', function(e) {
                                        if (e.target.id === 'confirm-mode-switch' && pendingModeSwitch) {
                                            // Complete the mode switch
                                            toggleModeControls(pendingModeSwitch);
                                            updateModeButtonColors(pendingModeSwitch);
                                            const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
                                            if (confirmDialog) confirmDialog.style.display = 'none';
                                            pendingModeSwitch = null;
                                        } else if (e.target.id === 'cancel-mode-switch') {
                                            // Cancel the mode switch - revert radio button
                                            const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
                                            if (confirmDialog) confirmDialog.style.display = 'none';
                                            pendingModeSwitch = null;
                                        }
                                    });
                                </script>
                                """)
                                
                                # Visual indicator for active mode
                                mode_indicator = gr.HTML(
                                    value=f"<div style='text-align: center; padding: 8px; background: #e3f2fd; border-radius: 4px; margin-top: 8px;'><strong>🎯 Active Mode:</strong> {default_mode}</div>",
                                    elem_id="mode-indicator"
                                )
                        
                        # Hidden AI controls that will be moved to the AI Configuration section
                        with gr.Group(visible=False) as ai_controls:
                            
                            # Advanced Settings - Comprehensive AI Controls
                            with gr.Accordion("🎯 Context & Quality", open=False):
                                similarity_threshold = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.7,
                                    step=0.1,
                                    label="Similarity Threshold",
                                    info="Higher values = more relevant results",
                                    elem_classes=["modern-slider"]
                                )
                                response_temperature = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.1,
                                    step=0.1,
                                    label="Response Temperature",
                                    info="0 = Accurate, 1 = Creative",
                                    elem_classes=["modern-slider"]
                                )
                            
                            # Response Behavior Controls
                            with gr.Accordion("📝 Response Behavior", open=False):
                                citation_style = gr.Radio(
                                    choices=["Include Sources", "Exclude Sources", "Minimal Citations"],
                                    value="Include Sources",
                                    label="Citation Style"
                                )
                                response_length = gr.Radio(
                                    choices=["Brief", "Medium", "Detailed"],
                                    value="Medium",
                                    label="Response Length"
                                )
                                # Removed confidence indicators - system now uses deterministic mode selection
                            
                            # System Prompt Templates
                            with gr.Accordion("🤖 AI Behavior & Prompts", open=True):
                                system_prompt_templates = gr.Dropdown(
                                    choices=[
                                        "Default Assistant",
                                        "Financial Analyst",
                                        "Technical Expert", 
                                        "Research Assistant",
                                        "Document Summarizer",
                                        "Compliance Reviewer",
                                        "Custom"
                                    ],
                                    value="Default Assistant",
                                    label="Prompt Template",
                                    info="Choose AI behavior for both Document and General Assistant modes"
                                )
                                system_prompt_input = gr.Textbox(
                                    placeholder=self._system_prompt,
                                    label="Custom System Prompt",
                                    lines=4,
                                    interactive=True,
                                    info="Override default behavior",
                                    render=False,
                                )
                                system_prompt_input.render()
                                
                                # Connect mode changes to system prompt
                                #mode.change(
                                #    self._set_current_mode,
                                #    inputs=mode,
                                #    outputs=[system_prompt_input],
                                #) 
                            
                            # Reset Controls
                            reset_settings_btn = gr.Button(
                                "🔄 Reset to Defaults",
                                size="sm",
                                elem_classes=["modern-button", "secondary-button"]
                            )
                        
                        # Mode-Specific Features and Controls
                        with gr.Group() as mode_specific_controls:
                            
                            # General Assistant Mode Controls
                            with gr.Group(visible=False) as general_controls:
                                with gr.Accordion("⚡ General Assistant Tools", open=True):
                                    gr.HTML("""
                                    <div style='background: linear-gradient(135deg, #e8f5e8 0%, #f0f9ff 100%); padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #4CAF50;'>
                                        <div style='font-weight: 600; color: #4CAF50; margin-bottom: 8px;'>🚀 Quick Tools</div>
                                        <div style='font-size: 13px; color: #555;'>Optimized for instant answers and calculations</div>
                                    </div>
                                    """)
                                    
                                    # Quick calculation helper
                                    with gr.Row():
                                        calc_input = gr.Textbox(
                                            placeholder="e.g., 15% of $250,000 or 1024 * 8",
                                            label="🧮 Quick Calculator",
                                            lines=1,
                                            scale=3
                                        )
                                        calc_btn = gr.Button("Calculate", scale=1, elem_classes=["modern-button"])
                                    
                                    # Definition lookup shortcuts
                                    with gr.Row():
                                        definition_shortcuts = gr.Radio(
                                            choices=[
                                                "🔒 Security Terms", 
                                                "💰 Financial Terms", 
                                                "⚖️ Compliance Terms",
                                                "🏗️ Tech Architecture"
                                            ],
                                            label="Definition Shortcuts",
                                            interactive=True
                                        )
                                    
                                    # Quick response indicators
                                    general_status = gr.HTML(
                                        value="<div style='text-align: center; padding: 8px; background: #e8f5e8; border-radius: 4px; color: #4CAF50;'><strong>⚡ Ready for instant responses</strong></div>"
                                    )
                            
                            # Document Assistant Mode Controls  
                            with gr.Group(visible=True) as document_controls:  # Default visible since Document Assistant is default
                                with gr.Accordion("📚 Document Assistant Tools", open=True):
                                    
                                    

                                    

                                    
                                    # Document search status
                                    document_status = gr.HTML(
                                        value="<div style='text-align: center; padding: 8px; background: #e3f2fd; border-radius: 4px; color: #0077BE;'><strong>📊 Document search active</strong></div>"
                                    )
                            
                            # Mode switching confirmation dialog (initially hidden)
                            with gr.Group(visible=False) as mode_confirm_dialog:
                                gr.HTML("""
                                <div style='background: #fff3cd; border: 1px solid #ffeaa7; padding: 16px; border-radius: 8px; margin: 12px 0;'>
                                    <div style='font-weight: 600; color: #856404; margin-bottom: 8px;'>⚠️ Mode Switch Confirmation</div>
                                    <div style='color: #856404; margin-bottom: 12px;'>You have active document analysis. Switching modes may change how your queries are processed.</div>
                                    <div style='display: flex; gap: 8px;'>
                                        <button id='confirm-mode-switch' style='background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;'>Continue Switch</button>
                                        <button id='cancel-mode-switch' style='background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;'>Cancel</button>
                                    </div>
                                </div>
                                """)
                            
                            # Enhanced AI Configuration Controls (hidden, to be moved to sidebar)
                            with gr.Group(visible=False) as enhanced_ai_controls:
                                # Model Selection
                                model_selection = gr.Radio(
                                    choices=[
                                        "Foundation-Sec-8B (Local)",
                                        "GPT-3.5 Turbo (OpenAI)",
                                        "GPT-4 (OpenAI)", 

                                        "Llama 2 (Ollama)",
                                        "Claude 3 Sonnet",
                                        "Claude 3 Haiku"
                                    ],
                                    value="Foundation-Sec-8B (Local)",
                                    label="AI Model",
                                    info="Select the AI model to use for responses",
                                    elem_classes=["model-selector"]
                                )
                                
                                # Writing Style Selection (Claude Desktop style)
                                writing_style = gr.Radio(
                                    choices=[
                                        "Balanced",
                                        "Concise", 
                                        "Explanatory",
                                        "Creative",
                                        "Professional",
                                        "Casual",
                                        "Technical"
                                    ],
                                    value="Balanced",
                                    label="Writing Style",
                                    info="Adjust how the AI communicates",
                                    elem_classes=["writing-style-selector"]
                                )
                                
                                # Temperature Control (Enhanced)
                                temperature_control = gr.Slider(
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.1,
                                    step=0.05,
                                    label="Creativity Level",
                                    info="Lower = More focused, Higher = More creative",
                                    elem_classes=["temperature-control"]
                                )
                    


                # Right Side - Chat and Document Management
                with gr.Column(scale=8, elem_classes=["main-content-column"]):
                    # Chat Area - Expanded
                    with gr.Group(elem_classes=["chat-container"]):
                        with gr.Group(elem_classes=["enhanced-chat-header"]):
                            with gr.Row():
                                # Chat Title (Left)
                                with gr.Column(scale=3):
                                    gr.HTML(f"<h3 style='margin: 0; color: #0077BE; font-size: 20px;'>{CHAT_HEADER}</h3>")
                                
                                # Mode Selector (Right)
                                with gr.Column(scale=2):
                                    mode = gr.Radio(
                                        choices=[
                                            ("🤖 General LLM", Modes.GENERAL_ASSISTANT.value),
                                            ("📚 RAG Mode", Modes.DOCUMENT_ASSISTANT.value)
                                        ],
                                        value=default_mode,
                                        label="",
                                        elem_classes=["chat-mode-selector"],
                                        interactive=True
                                    )
                        
                        # Resize handle removed - fixed size chatbox
                        
                        # Custom Chat Layout - Input at Top
                        with gr.Group(elem_classes=["chat-input-top"]):
                            
                            # Message Input Box - Now at TOP
                            with gr.Row():
                                chat_input = gr.Textbox(
                                    placeholder="💡 Try: 'What CVEs affect our Exchange servers?' or 'Show me our incident response policy'",
                                    label="",
                                    show_label=False,
                                    lines=3,
                                    max_lines=5,
                                    elem_classes=["chat-input-textbox"],
                                    scale=5
                                )
                                
                            # Action Buttons - Now at TOP with input
                            with gr.Row():
                                send_btn = gr.Button("SEND MESSAGE", elem_classes=["modern-button", "send-button"], scale=1)
                                retry_btn = gr.Button("RETRY", elem_classes=["modern-button", "retry-button"], scale=1)
                                undo_btn = gr.Button("UNDO", elem_classes=["modern-button", "undo-button"], scale=1)
                                clear_btn = gr.Button("CLEAR CHAT", elem_classes=["modern-button", "clear-button"], scale=1)
                        
                        # Chat Messages Area - Middle
                        with gr.Group(elem_classes=["chat-messages"]):
                            chatbot = gr.Chatbot(
                                label="",
                                show_copy_button=True,
                                elem_id="chatbot",
                                height=None,  # FIXED: Remove hardcoded height
                                elem_classes=["main-chatbot"]
                            )
                        
                        # Fake API Button Area - Bottom (placeholder for now)
                        with gr.Group(elem_classes=["chat-bottom-area"]):
                            fake_api_btn = gr.Button(
                                "Use via API (Hidden for now)", 
                                elem_classes=["fake-api-button"], 
                                visible=False  # Hidden but preserving space
                            )
                            gr.HTML('<div style="text-align: center; color: #555; font-size: 12px; padding: 5px;">API Integration Area</div>')
                    

                    # Internal Information Section - Full Width (Matching Chat Layout)
                    with gr.Group(elem_classes=["file-management-section"]):
                        gr.HTML("<div class='file-section-title'>📁 Internal Information Repository</div>")
                        
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
                                scale=1
                            )
                            
                            # Folders Upload Button
                            folder_upload_button = gr.Button(
                                "📁 Upload Folders",
                                size="lg",
                                elem_classes=["modern-button", "folder-button"],
                                scale=1
                            )
                        
                        # Second Row: Clear All and Process Folder Buttons
                        with gr.Row():
                            clear_all_button = gr.Button(
                                "🗑️ Clear All Documents",
                                size="sm",
                                elem_classes=["modern-button", "danger-button"],
                                scale=1,
                                elem_id="clear-all-docs"
                            )
                            
                            process_folder_button = gr.Button(
                                "📁 Ingest Directory",
                                visible=False,
                                elem_classes=["modern-button", "ingest-button"],
                                size="lg",
                                scale=1
                            )
                        
                        # Server-side folder path input
                        folder_path_input = gr.Textbox(
                            label="Folder Path",
                            placeholder="Enter server folder path (e.g., C:/Users/admin/Documents/my_folder)",
                            visible=False,
                            elem_classes=["folder-path-input"]
                        )
                        
                        
                        # Status message for folder operations
                        folder_status_msg = gr.HTML(value="", elem_classes=["folder-status"])
                        
                        # Status message for clear operations
                        clear_status_msg = gr.HTML(value="", elem_classes=["clear-status"])
                        
                        # File List Display
                        gr.HTML("<div class='file-list-header'>📋 Unique Documents:</div>")
                        
                        ingested_dataset = gr.HTML(
                            value=self._format_file_list(),
                            elem_classes=["file-list-display"]
                        )
                        
                        # Add resize handle for Internal Information
                        gr.HTML('<div class="internal-resize-handle" id="internal-resize-handle"></div>')

                    # External Information Section - Full Width (Matching Chat Layout)
                    with gr.Group(elem_classes=["external-info-section"]):
                        gr.HTML("<div class='file-section-title'>Regulatory Information Feed</div>")
                        
                        # Dynamic Time Range Display
                        time_range_display = gr.HTML("<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 30 days</div>")
                        with gr.Row():
                            time_24h_btn = gr.Button("24 hours", elem_classes=["filter-btn"], size="sm")
                            time_7d_btn = gr.Button("7 days", elem_classes=["filter-btn"], size="sm")
                            time_30d_btn = gr.Button("30 days", elem_classes=["filter-btn"], size="sm")
                            time_90d_btn = gr.Button("90 days", elem_classes=["filter-btn"], size="sm")
                        
                        # Hidden state components to track current selections
                        current_feed_source = gr.Textbox(value="All", visible=False)
                        current_time_filter = gr.Textbox(value="30 days", visible=False)
                        
                        # Refresh Button
                        with gr.Row():
                            feed_refresh_btn = gr.Button(
                                "🔄 Refresh Feeds",
                                size="sm",
                                elem_classes=["modern-button", "refresh-button"],
                                scale=1
                            )
                        
                        # Feed Status Display
                        feed_status = gr.HTML(
                            "<div class='feed-status'>Loading external information...</div>",
                            elem_classes=["feed-status-display"]
                        )
                        
                        # Feed Items Display
                        # Initialize with current feeds display
                        try:
                            initial_feeds_html = self._format_feeds_display(None, 30)  # Default 30 days, All sources
                        except Exception as e:
                            initial_feeds_html = """
                            <div class='feed-content'>
                                <div style='text-align: center; color: #666; padding: 20px;'>
                                    <div>📡 No external information available</div>
                                    <div style='font-size: 12px; margin-top: 8px;'>
                                        Click the REFRESH button to load latest regulatory feeds
                                    </div>
                                </div>
                            </div>"""
                        
                        feed_display = gr.HTML(
                            value=initial_feeds_html,
                            elem_classes=["file-list-container"]
                        )
                        
                        # Add resize handle for External Information
                        gr.HTML('<div class="external-resize-handle" id="external-resize-handle"></div>')

                    # CVE Tracking Section - Dedicated Panel
                    with gr.Group(elem_classes=["cve-tracking-section"]):
                        gr.HTML("<div class='file-section-title'>Common Vulnerabilities and Exposures (CVE) Tracking</div>")
                        
                        # CVE Controls - Simplified
                        with gr.Row():
                            # Refresh Button - Centered
                            cve_refresh_btn = gr.Button(
                                "Refresh CVE Data",
                                size="sm",
                                elem_classes=["modern-button", "refresh-button"]
                            )
                        
                        # CVE Status Display
                        cve_status = gr.HTML(
                            "<div class='feed-status'>Loading CVE data...</div>",
                            elem_classes=["feed-status-display"]
                        )
                        
                        # CVE Items Display
                        try:
                            initial_cve_html = self._format_cve_display(None, "All Severities", "All Vendors")
                        except Exception as e:
                            initial_cve_html = """
                            <div class='feed-content'>
                                <div style='text-align: center; color: #666; padding: 20px;'>
                                    <div>🔍 No Microsoft Security CVE data available</div>
                                    <div style='font-size: 12px; margin-top: 8px;'>
                                        Click the REFRESH button to load latest Microsoft Security vulnerabilities
                                    </div>
                                </div>
                            </div>"""
                        
                        cve_display = gr.HTML(
                            value=initial_cve_html,
                            elem_classes=["file-list-container"]
                        )
                        
                        # Add resize handle for CVE Tracking
                        gr.HTML('<div class="cve-resize-handle" id="cve-resize-handle"></div>')

                    # MITRE ATT&CK Threat Intelligence Section
                    with gr.Group(elem_classes=["mitre-attack-section"]):
                        gr.HTML("<div class='file-section-title'>MITRE ATT&CK Threat Intelligence</div>")
                        
                        # MITRE Controls Row
                        with gr.Row():
                            # Refresh Button
                            mitre_refresh_btn = gr.Button(
                                "Refresh MITRE Data",
                                size="sm",
                                elem_classes=["modern-button", "refresh-button"],
                                scale=1
                            )
                        
                        # MITRE Status Display
                        mitre_status = gr.HTML(
                            "<div class='feed-status'>Loading MITRE ATT&CK data...</div>",
                            elem_classes=["feed-status-display"]
                        )
                        
                        # MITRE Content Display
                        try:
                            initial_mitre_html = self._format_mitre_display("Enterprise", "All Domains", None, "All Tactics", False)
                        except Exception as e:
                            initial_mitre_html = """
                            <div class='feed-content'>
                                <div style='text-align: center; color: #666; padding: 20px;'>
                                    <div>🛡️ No MITRE ATT&CK data available</div>
                                    <div style='font-size: 12px; margin-top: 8px;'>
                                        Click the REFRESH button to load latest threat intelligence
                                    </div>
                                </div>
                            </div>"""
                        
                        mitre_display = gr.HTML(
                            value=initial_mitre_html,
                            elem_classes=["file-list-container"]
                        )
                        
                        # Add resize handle for MITRE ATT&CK
                        gr.HTML('<div class="mitre-resize-handle" id="mitre-resize-handle"></div>')

                    # Forum Directory Section - Simple Panel
                    with gr.Group(elem_classes=["external-info-section"]):
                        gr.HTML("<div class='file-section-title'>Dark Web - Forums Directory</div>")
                        
                        # Simple Controls Row
                        with gr.Row():
                            # Refresh Button
                            forum_refresh_btn = gr.Button(
                                "Refresh Directory",
                                size="sm",
                                elem_classes=["modern-button", "refresh-button"],
                                scale=1
                            )
                        
                        # Forum Status Display
                        forum_status = gr.HTML(
                            "<div class='feed-status'>Loading forum directory...</div>",
                            elem_classes=["feed-status-display"]
                        )
                        
                        # Simple Forum Display
                        try:
                            initial_forums_html = self._format_simple_forum_display()
                        except Exception as e:
                            initial_forums_html = """
                            <div class='feed-content'>
                                <div style='text-align: center; color: #666; padding: 20px;'>
                                    <div>🌐 Forum directory unavailable</div>
                                    <div style='font-size: 12px; margin-top: 8px;'>
                                        Click the REFRESH button to load forum directory
                                    </div>
                                </div>
                            </div>"""
                        
                        forum_display = gr.HTML(
                            value=initial_forums_html,
                            elem_classes=["file-list-container"]
                        )
                        
                        # No resize handle for simple forum panel

            # Mode change handler for explanation update
            def update_mode_explanation(selected_mode):
                explanation = self._get_default_mode_explanation(Modes(selected_mode))
                return gr.update(value=f"<div class='mode-explanation'>{explanation}</div>")
            
            # Advanced Settings Event Handlers
            def update_system_prompt_from_template(template_name):
                if template_name == "Custom":
                    return gr.update(interactive=True, placeholder="Enter your custom system prompt...")
                else:
                    template_prompt = self._get_system_prompt_template(template_name)
                    self._set_system_prompt(template_prompt)
                    return gr.update(value=template_prompt, interactive=True)
            
            def reset_to_defaults():
                return (
                    gr.update(value=0.7),  # similarity_threshold
                    gr.update(value=0.1),  # response_temperature
                    gr.update(value="Include Sources"), # citation_style
                    gr.update(value="Medium"), # response_length
                    gr.update(value="Default Assistant"), # system_prompt_templates
                    gr.update(value=self._get_system_prompt_template("Default Assistant")) # system_prompt_input
                )
            
            system_prompt_templates.change(
                update_system_prompt_from_template,
                inputs=[system_prompt_templates],
                outputs=[system_prompt_input]
            )
            
            reset_settings_btn.click(
                reset_to_defaults,
                outputs=[
                    similarity_threshold,
                    response_temperature,
                    citation_style,
                    response_length,
                    system_prompt_templates,
                    system_prompt_input
                ]
            )
            
            # System prompt handler
            system_prompt_input.blur(
                self._set_system_prompt,
                inputs=system_prompt_input,
            )
            
            # Mode-Specific Event Handlers
            
            # General Assistant Calculator
            def handle_calculation(calc_expression):
                if not calc_expression or calc_expression.strip() == "":
                    return "Please enter a calculation (e.g., 15% of $250,000 or 1024 * 8)"
                
                try:
                    # Handle percentage calculations
                    if "%" in calc_expression and "of" in calc_expression.lower():
                        # Parse "15% of $250,000" format
                        parts = calc_expression.lower().replace("$", "").replace(",", "").split("of")
                        if len(parts) == 2:
                            percentage = float(parts[0].strip().replace("%", ""))
                            amount = float(parts[1].strip())
                            result = (percentage / 100) * amount
                            return f"💰 {percentage}% of ${amount:,.2f} = ${result:,.2f}"
                    
                    # Handle basic math expressions
                    # Remove currency symbols and commas for calculation
                    clean_expression = calc_expression.replace("$", "").replace(",", "")
                    
                    # Security: Only allow basic math operations
                    allowed_chars = set("0123456789+-*/.() ")
                    if not all(c in allowed_chars for c in clean_expression):
                        return "⚠️ Only basic math operations (+, -, *, /, %) are allowed"
                    
                    result = eval(clean_expression)
                    
                    # Format result appropriately
                    if isinstance(result, float):
                        if result.is_integer():
                            return f"🧮 {calc_expression} = {int(result):,}"
                        else:
                            return f"🧮 {calc_expression} = {result:,.2f}"
                    else:
                        return f"🧮 {calc_expression} = {result:,}"
                
                except Exception as e:
                    return f"❌ Calculation error: Please check your expression format"
            
            calc_btn.click(
                handle_calculation,
                inputs=[calc_input],
                outputs=[general_status]
            )
            
            # Definition shortcuts handler
            def handle_definition_shortcut(term_category):
                if not term_category:
                    return ""
                
                templates = {
                    "🔒 Security Terms": "Define these key cybersecurity terms: firewall, encryption, vulnerability, threat actor, zero-day exploit, and phishing",
                    "💰 Financial Terms": "Explain these banking terms: interest rate, LIBOR, credit risk, Basel III, capital adequacy ratio, and liquidity coverage ratio", 
                    "⚖️ Compliance Terms": "Define these compliance concepts: SOX, PCI DSS, GDPR, data retention, audit trail, and risk assessment",
                    "🏗️ Tech Architecture": "Explain these technical terms: API, microservices, load balancer, CDN, container, and database sharding"
                }
                
                return templates.get(term_category, "")
            
            definition_shortcuts.change(
                handle_definition_shortcut,
                inputs=[definition_shortcuts],
                outputs=[chat_input]
            )
            

            

            
            # File Upload Event Handlers
            def upload_and_refresh(files):
                if files:
                    self._upload_file(files)
                # Return updated file list, header status, and sidebar content
                updated_model_status = get_model_status()
                updated_header_html = f"""
                    <div style='display: flex; flex-direction: column; gap: 12px;'>
                        <div class='status-indicator'>{updated_model_status}</div>
                    </div>
                """
                
                # Update sidebar content
                updated_document_library = self._get_document_library_html()
                
                return (
                    self._format_file_list(), 
                    updated_header_html,
                    updated_document_library
                )
            
            def show_folder_path_input():
                """Show folder path input for server-side folder ingestion."""
                return gr.update(visible=True), gr.update(visible=True)
            
            def ingest_server_folder(folder_path):
                """Ingest a server-side folder using the ingest_folder script functionality."""
                if not folder_path or folder_path.strip() == "":
                    return (
                        self._format_file_list(),
                        "❌ Please enter a folder path",
                        self._get_document_library_html()
                    )
                
                try:
                    from pathlib import Path
                    folder_path_obj = Path(folder_path.strip())
                    
                    if not folder_path_obj.exists():
                        return (
                            self._format_file_list(),
                            "❌ Folder path does not exist",
                            self._get_document_library_html()
                        )
                    
                    if not folder_path_obj.is_dir():
                        return (
                            self._format_file_list(),
                            "❌ Path is not a directory",
                            self._get_document_library_html()
                        )
                    
                    # Use LocalIngestWorker directly for folder ingestion
                    from pathlib import Path
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
                    
                    try:
                        from ingest_folder import LocalIngestWorker
                        from internal_assistant.settings.settings import settings
                        
                        # Initialize worker
                        worker = LocalIngestWorker(
                            self._ingest_service, 
                            settings(), 
                            max_attempts=2,
                            checkpoint_file="ui_folder_ingestion_checkpoint.json"
                        )
                        
                        # Process the folder
                        worker.ingest_folder(folder_path_obj, ignored=[], resume=True)
                        status = "✅ Folder ingested successfully!"
                        
                    except ImportError as e:
                        logger.error(f"Failed to import LocalIngestWorker: {e}")
                        return (
                            self._format_file_list(),
                            f"❌ Folder ingestion not available: {str(e)}",
                            self._get_document_library_html()
                        )
                    except Exception as e:
                        logger.error(f"Folder ingestion failed: {e}")
                        return (
                            self._format_file_list(),
                            f"❌ Ingestion failed: {str(e)}",
                            self._get_document_library_html()
                        )
                    
                    # Update UI components
                    updated_model_status = get_model_status()
                    updated_header_html = f"""
                        <div style='display: flex; flex-direction: column; gap: 12px;'>
                            <div class='status-indicator'>{updated_model_status}</div>
                        </div>
                    """
                    
                    updated_document_library = self._get_document_library_html()
                    
                    return (
                        self._format_file_list(),
                        status,  # Success/error message from _ingest_folder
                        updated_document_library
                    )
                    
                except Exception as e:
                    logger.error(f"Folder ingestion error: {e}")
                    return (
                        self._format_file_list(),
                        f"❌ Error: {str(e)}",
                        self._get_document_library_html()
                    )
            
            def clear_all_documents():
                """Clear all ingested documents with confirmation."""
                try:
                    # Get all ingested documents
                    ingested_docs = self._ingest_service.list_ingested()
                    
                    if not ingested_docs:
                        return (
                            self._format_file_list(),
                            "ℹ️ No documents to clear",
                            self._get_document_library_html()
                        )
                    
                    doc_count = len(ingested_docs)
                    
                    # Delete all documents
                    failed_deletions = []
                    for doc in ingested_docs:
                        try:
                            self._ingest_service.delete(doc.doc_id)
                        except Exception as e:
                            logger.error(f"Failed to delete document {doc.doc_id}: {e}")
                            failed_deletions.append(doc.doc_id)
                    
                    # Prepare status message
                    if failed_deletions:
                        success_count = doc_count - len(failed_deletions)
                        status_msg = f"⚠️ Cleared {success_count}/{doc_count} documents. {len(failed_deletions)} failed to delete."
                    else:
                        status_msg = f"✅ Successfully cleared all {doc_count} documents"
                    
                    # Update UI components
                    updated_model_status = get_model_status()
                    updated_header_html = f"""
                        <div style='display: flex; flex-direction: column; gap: 12px;'>
                            <div class='status-indicator'>{updated_model_status}</div>
                        </div>
                    """
                    
                    updated_document_library = self._get_document_library_html()
                    
                    return (
                        self._format_file_list(),
                        status_msg,
                        updated_document_library
                    )
                    
                except Exception as e:
                    logger.error(f"Error clearing documents: {e}")
                    return (
                        self._format_file_list(),
                        f"❌ Error clearing documents: {str(e)}",
                        self._get_document_library_html()
                    )
            
            # File upload handler
            upload_button.upload(
                upload_and_refresh,
                inputs=upload_button,
                outputs=[
                    ingested_dataset, 
                    model_status_display,
                    document_library_content
                ],
            )
            
            # Folder upload handlers
            folder_upload_button.click(
                show_folder_path_input,
                outputs=[folder_path_input, process_folder_button]
            )
            
            process_folder_button.click(
                ingest_server_folder,
                inputs=[folder_path_input],
                outputs=[
                    ingested_dataset,
                    folder_status_msg,
                    document_library_content
                ]
            )
            
            # Clear all documents handler with JavaScript confirmation
            clear_all_button.click(
                clear_all_documents,
                outputs=[
                    ingested_dataset,
                    clear_status_msg,
                    document_library_content
                ],
                js="""
                function() {
                    const confirmClear = confirm('⚠️ WARNING: This will permanently delete ALL uploaded documents!\\n\\nAre you sure you want to continue?');
                    if (confirmClear) {
                        return true;  // Proceed with the clear operation
                    } else {
                        return false; // Cancel the operation
                    }
                }
                """
            )
            
            # Auto-refresh file list periodically
            def refresh_file_list():
                return self._format_file_list()
            
            # Document Library Search and Filter Event Handlers
            def handle_search(search_query):
                """Handle document search functionality."""
                filtered_content, status_msg = self._filter_documents(search_query, "all")
                return filtered_content
            
            def handle_filter(filter_type, search_query=""):
                """Handle document filtering functionality."""
                filtered_content, status_msg = self._filter_documents(search_query, filter_type.lower())
                return filtered_content
            
            # Search input event handler
            doc_search_input.change(
                handle_search,
                inputs=[doc_search_input],
                outputs=[document_library_content]
            )
            
            # Helper function for filter operations with scrolling
            def handle_filter_with_scroll(search_query, filter_type, current_filter):
                """Handle filtering with scrolling support and toggle-off functionality."""
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
                    content, status_msg = self._filter_documents(search_query, filter_type)
                    return content, status_msg, filter_type, search_query
            
            # Admin toggle functionality removed - user content is always visible
            
            # Filter button event handlers with scrolling support
            filter_all_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "all", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_pdf_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "pdf", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_excel_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "excel", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_word_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "word", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_recent_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "recent", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_analyzed_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "analyzed", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_updated_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "updated", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            filter_other_btn.click(
                lambda search_query, current_filter: handle_filter_with_scroll(search_query, "other", current_filter),
                inputs=[doc_search_input, current_filter_type],
                outputs=[document_library_content, filter_status_msg, current_filter_type, current_search_query]
            )
            
            
            # Quick Actions event handlers removed
            
            # Integrate sidebar with existing document management
            # Update sidebar when main upload functionality is used
            def sync_sidebar_with_main():
                """Synchronize sidebar with main document management."""
                return self._get_document_library_html()
            
            # Note: HTML components don't need change handlers for auto-refresh
            # The file list will update when upload/folder events trigger
            
            # === Custom Chat Event Handlers ===
            # Wire up the new custom chat interface components
            
            # Create a wrapper function for the chat that handles streaming properly
            def chat_wrapper(message, history, mode, system_prompt_input, similarity_threshold, response_temperature, citation_style, response_length):
                # Add user message to history
                if message.strip():
                    history = history + [[message, None]]
                    
                    # Get the streaming response
                    try:
                        # Log the query processing
                        logger.info(f"Using {mode} mode")
                        
                        # Use the selected mode and prompt
                        response_generator = self._chat(
                            message, 
                            history[:-1],  # Pass history without the current incomplete exchange
                            mode,  # Use user's selected mode directly - DETERMINISTIC
                            system_prompt_input,  # Use user's prompt directly
                            similarity_threshold, 
                            response_temperature, 
                            citation_style, 
                            response_length
                        )
                        
                        # Collect streaming response properly (fix for repetitive output bug)
                        full_response = ""
                        chunk_count = 0
                        max_chunks = 1000  # Enhanced limit for detailed CTI reports while maintaining stability
                        previous_length = 0
                        last_tokens = []  # Track recent tokens to detect loops
                        
                        for chunk in response_generator:
                            chunk_count += 1
                            if chunk_count > max_chunks:
                                break
                                
                            if chunk and isinstance(chunk, str):
                                # Handle cumulative streaming responses correctly
                                if len(chunk) > previous_length:
                                    # Extract only NEW content (delta) from cumulative response
                                    new_content = chunk[previous_length:]
                                    
                                    # Apply repetition detection to new content only
                                    words = new_content.split()
                                    skip_chunk = False
                                    for word in words:
                                        if len(last_tokens) > 10:
                                            if last_tokens[-5:].count(word) >= 2:
                                                skip_chunk = True
                                                break
                                        last_tokens.append(word)
                                        if len(last_tokens) > 20:
                                            last_tokens.pop(0)
                                    
                                    if skip_chunk:
                                        continue
                                        
                                    # Check for phrase repetition in new content
                                    if len(new_content) > 5 and new_content in full_response[-200:]:
                                        continue
                                        
                                    full_response += new_content
                                    previous_length = len(chunk)
                                    
                                    # Enhanced character limit for detailed CTI reports with stability
                                    if len(full_response) > 8000:
                                        break
                                elif len(chunk) <= previous_length:
                                    # Chunk is same length or shorter, use it as final response
                                    full_response = chunk
                                    break
                                    
                    except Exception as e:
                        # Handle specific token-related errors with user-friendly messages
                        error_str = str(e).lower()
                        if any(token_err in error_str for token_err in ['token', 'context length', 'max length', 'input too long', 'sequence length']):
                            if mode == Modes.DOCUMENT_ASSISTANT.value:
                                full_response = "⚠️ **Document Assistant - Request Too Large**\n\nYour query or document context is too long. Try these solutions:\n\n• **Shorter message**: Use fewer words in your question\n• **Specific documents**: Ask about particular files instead of all documents\n• **General Assistant**: Switch modes for questions that don't need document context\n• **Split query**: Break complex questions into smaller parts"
                            else:
                                full_response = "⚠️ **General Assistant - Request Too Large**\n\nYour message is too long. Please try:\n\n• **Shorter message**: Use fewer words or break into smaller questions\n• **Simpler query**: Focus on one topic at a time\n• **Multiple questions**: Ask follow-up questions instead of one long message"
                        elif 'rate limit' in error_str or 'quota' in error_str:
                            mode_name = "Document Assistant" if mode == Modes.DOCUMENT_ASSISTANT.value else "General Assistant"
                            full_response = f"⚠️ **{mode_name} - Rate Limit Reached**\n\nToo many requests have been made. Please:\n\n• **Wait a moment**: Try again in 30-60 seconds\n• **Slower pace**: Space out your questions more\n• **Check usage**: You may have reached your daily limit"
                        elif 'connection' in error_str or 'timeout' in error_str:
                            mode_name = "Document Assistant" if mode == Modes.DOCUMENT_ASSISTANT.value else "General Assistant"
                            full_response = f"⚠️ **{mode_name} - Connection Issue**\n\nUnable to reach the AI service. Please:\n\n• **Check internet**: Verify your network connection\n• **Refresh page**: Reload and try again\n• **Try again**: Wait a moment and retry your request\n• **Contact support**: If the issue persists"
                        else:
                            mode_name = "Document Assistant" if mode == Modes.DOCUMENT_ASSISTANT.value else "General Assistant"
                            full_response = f"⚠️ **{mode_name} - Unexpected Error**\n\nSomething went wrong while generating your response.\n\n**Error details**: {str(e)}\n\n**What you can try:**\n• **Rephrase**: Try asking your question differently\n• **Switch modes**: Try the other assistant mode\n• **Simpler query**: Break complex questions into parts\n• **Contact support**: If this keeps happening"
                    
                    # Basic cleanup of spacing and formatting
                    if full_response:
                        import re
                        # Only keep essential cleanup - remove excessive spacing and punctuation
                        full_response = re.sub(r'([.!?])\1{2,}', r'\1', full_response)  # Remove excessive punctuation
                        full_response = re.sub(r'\s{3,}', ' ', full_response)  # Clean up excessive spacing
                        full_response = full_response.strip()
                        
                        # ADD SOURCE ATTRIBUTION: Show which mode was actually used
                        # Determine the actual mode based on whether documents were found and used
                        has_document_sources = SOURCES_SEPARATOR in full_response
                        
                        # If we tried to use documents but found no sources, it's effectively general knowledge
                        actual_mode_used = mode
                        if mode == Modes.DOCUMENT_ASSISTANT.value:
                            if not has_document_sources:
                                # No documents were actually used, so it's general knowledge
                                actual_mode_used = Modes.GENERAL_ASSISTANT.value
                        
                        mode_indicators = {
                            Modes.GENERAL_ASSISTANT.value: "[AI] *General knowledge*",
                            Modes.DOCUMENT_ASSISTANT.value: "[DOC] *From your documents*",
                        }
                        
                        # Add mode indicator based on what was actually used
                        if actual_mode_used in mode_indicators and not has_document_sources:
                            indicator = mode_indicators[actual_mode_used]
                            # Only add indicator for modes that don't already have sources shown
                            if actual_mode_used != Modes.DOCUMENT_ASSISTANT.value:
                                full_response += f"\n\n{indicator}"
                    
                    # Update the last message with the complete response
                    # Provide mode-specific fallback message if no response generated
                    if not full_response.strip():
                        if mode == Modes.DOCUMENT_ASSISTANT.value:
                            fallback_msg = "📄 **Document Assistant - No Response Generated**\n\nI couldn't find relevant information in your documents or generate a response. Try:\n\n• **Rephrase question**: Use different keywords\n• **Check documents**: Ensure relevant files are uploaded\n• **General Assistant**: Switch modes for general knowledge questions\n• **Be specific**: Ask about particular documents or topics"
                        else:
                            fallback_msg = "🤖 **General Assistant - No Response Generated**\n\nI couldn't generate a response to your question. Try:\n\n• **Rephrase question**: Use different words or simpler language\n• **Break it down**: Ask smaller, more specific questions\n• **Document Assistant**: Switch modes if you need information from uploaded files\n• **Try again**: Sometimes rephrasing helps me understand better"
                    else:
                        fallback_msg = full_response
                    
                    history[-1][1] = fallback_msg
                
                return history, ""  # Return updated history and clear the input
            
            # Send button handler
            send_btn.click(
                fn=chat_wrapper,
                inputs=[chat_input, chatbot, mode, system_prompt_input, similarity_threshold, response_temperature, citation_style, response_length],
                outputs=[chatbot, chat_input],
                show_progress=True
            )
            
            # Enter key handler for chat input
            chat_input.submit(
                fn=chat_wrapper,
                inputs=[chat_input, chatbot, mode, system_prompt_input, similarity_threshold, response_temperature, citation_style, response_length],
                outputs=[chatbot, chat_input],
                show_progress=True
            )
            
            # Mode selection handler with indicator update
            def on_mode_change(selected_mode):
                """Update the mode indicator when mode changes"""
                if selected_mode == Modes.DOCUMENT_ASSISTANT.value:
                    mode_display = "📚 Document Assistant"
                    mode_description = "Searching your documents for answers"
                    bg_color = "#e3f2fd"
                else:
                    mode_display = "🤖 General Assistant"
                    mode_description = "Using AI knowledge without documents"
                    bg_color = "#f1f8e9"
                
                indicator_html = f"""
                <div style='text-align: center; padding: 8px; background: {bg_color}; border-radius: 4px; margin-top: 8px;'>
                    <strong>🎯 Active Mode:</strong> {mode_display}<br>
                    <small style='color: #666;'>{mode_description}</small>
                </div>
                """
                return indicator_html
            
            # Connect mode change to indicator update
            mode.change(
                fn=on_mode_change,
                inputs=[mode],
                outputs=[mode_indicator]
            )
            
            # Clear chat button handler
            def clear_chat():
                return [], ""  # Clear chatbot history and input
            
            clear_btn.click(
                fn=clear_chat,
                inputs=[],
                outputs=[chatbot, chat_input]
            )
            
            # Retry button handler (will retry last message)
            def retry_last_message(history):
                if not history:
                    return history, ""
                # Remove last bot response and return user message for retry
                if len(history) > 0:
                    last_user_message = history[-1][0] if len(history[-1]) > 0 else ""
                    return history[:-1], last_user_message
                return history, ""
            
            retry_btn.click(
                fn=retry_last_message,
                inputs=[chatbot],
                outputs=[chatbot, chat_input]
            )
            
            # Undo button handler (removes last exchange)
            undo_btn.click(
                fn=lambda history: history[:-1] if history else [],
                inputs=[chatbot],
                outputs=[chatbot]
            )
            
            # RSS Feed Event Handlers
            async def refresh_feeds():
                """Refresh RSS feeds and update display."""
                try:
                    async with self._feeds_service:
                        success = await self._feeds_service.refresh_feeds()
                    
                    if success:
                        cache_info = self._feeds_service.get_cache_info()
                        status_html = f"""
                        <div class='feed-status success' style='font-size: 16px;'>
                            [SUCCESS] Feeds refreshed • {cache_info['total_items']} items • 
                            Last updated: {datetime.now().strftime('%H:%M:%S')}
                        </div>"""
                        
                        # Get initial feed display
                        feeds_html = self._format_feeds_display()
                        
                        return status_html, feeds_html
                    else:
                        error_html = """
                        <div class='feed-status error' style='font-size: 16px;'>
                            [ERROR] Failed to refresh feeds. Check network connection.
                        </div>"""
                        return error_html, "<div class='feed-content'>No feeds available</div>"
                        
                except Exception as e:
                    logger.error(f"Error refreshing feeds: {e}")
                    error_html = f"""
                    <div class='feed-status error' style='font-size: 16px;'>
                        [ERROR] Failed to refresh feeds: {str(e)}
                    </div>"""
                    return error_html, "<div class='feed-content'>No feeds available</div>"
            
            def filter_feeds(source_filter, time_filter):
                """Filter RSS feeds based on source and time."""
                try:
                    days_filter = None
                    if time_filter == "24 hours":
                        days_filter = 1
                    elif time_filter == "7 days":
                        days_filter = 7
                    elif time_filter == "30 days":
                        days_filter = 30
                    elif time_filter == "90 days":
                        days_filter = 90
                    elif time_filter == "365 days":
                        days_filter = 365
                    
                    # Handle special dropdown entries
                    if source_filter == "All" or source_filter == "--- Individual Sources ---":
                        source = None
                    else:
                        source = source_filter
                    
                    feeds_html = self._format_feeds_display(source, days_filter)
                    return feeds_html
                    
                except Exception as e:
                    logger.error(f"Error filtering feeds: {e}")
                    return f"""<div class='feed-content error'>
                        <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                            <div>⚠️ Error filtering feeds</div>
                            <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                        </div>
                    </div>"""
            
            # Wire up RSS feed handlers
            feed_refresh_btn.click(
                fn=refresh_feeds,
                outputs=[feed_status, feed_display]
            )
            
            # Source filtering removed - always show all sources
            
            
            # Time filter button handlers with auto-refresh
            # Each time filter first refreshes feeds, then applies the time filter
            def refresh_and_filter_24h(source):
                """Refresh feeds then filter to 24 hours."""
                # Skip refresh call since it's async and would need proper handling
                return filter_feeds(source, "24 hours")  # Just filter
            
            def refresh_and_filter_7d(source):
                """Refresh feeds then filter to 7 days."""
                # Skip refresh call since it's async and would need proper handling
                return filter_feeds(source, "7 days")  # Just filter
            
            def refresh_and_filter_30d(source):
                """Refresh feeds then filter to 30 days."""
                # Skip refresh call since it's async and would need proper handling
                return filter_feeds(source, "30 days")  # Just filter
            
            def refresh_and_filter_90d(source):
                """Refresh feeds then filter to 90 days."""
                # Skip refresh call since it's async and would need proper handling
                return filter_feeds(source, "90 days")  # Just filter
            
            time_24h_btn.click(
                fn=refresh_and_filter_24h,
                inputs=[current_feed_source],
                outputs=[feed_display]
            ).then(
                lambda: ("24 hours", "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 24 hours</div>"),
                outputs=[current_time_filter, time_range_display]
            )
            
            time_7d_btn.click(
                fn=refresh_and_filter_7d,
                inputs=[current_feed_source],
                outputs=[feed_display]
            ).then(
                lambda: ("7 days", "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 7 days</div>"),
                outputs=[current_time_filter, time_range_display]
            )
            
            time_30d_btn.click(
                fn=refresh_and_filter_30d,
                inputs=[current_feed_source],
                outputs=[feed_display]
            ).then(
                lambda: ("30 days", "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 30 days</div>"),
                outputs=[current_time_filter, time_range_display]
            )
            
            time_90d_btn.click(
                fn=refresh_and_filter_90d,
                inputs=[current_feed_source],
                outputs=[feed_display]
            ).then(
                lambda: ("90 days", "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 90 days</div>"),
                outputs=[current_time_filter, time_range_display]
            )
            
            
            # CVE Tracking Event Handlers
            async def refresh_cve_data():
                """Refresh CVE data and update display."""
                try:
                    logger.info("Starting CVE data refresh")
                    
                    # Get updated CVE display
                    cve_html = self._format_cve_display(None, "All Severities", "All Vendors")
                    
                    # Count CVE items for status message
                    cve_data = self._get_cve_data()
                    cve_count = len(cve_data)
                    
                    status_message = f"Microsoft Security CVE data refreshed • {cve_count} vulnerabilities loaded"
                    status_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #4CAF50;'>
                        {status_message} • {datetime.now().strftime('%H:%M:%S')}
                    </div>"""
                    
                    logger.info(f"Microsoft Security CVE refresh completed: {cve_count} vulnerabilities displayed")
                    return status_html, cve_html
                    
                except Exception as e:
                    logger.error(f"Error refreshing CVE data: {e}")
                    error_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #f44336;'>
                        Error refreshing Microsoft Security CVE data: {str(e)}
                    </div>"""
                    fallback_html = """
                    <div class='feed-content'>
                        <div style='text-align: center; color: #666; padding: 20px;'>
                            <div>🔍 Microsoft Security CVE data unavailable</div>
                            <div style='font-size: 12px; margin-top: 8px;'>
                                Please try again later
                            </div>
                        </div>
                    </div>"""
                    return error_html, fallback_html


            # MITRE ATT&CK Event Handlers
            async def refresh_mitre_data():
                """Refresh MITRE ATT&CK data and update display."""
                try:
                    logger.info("Starting MITRE ATT&CK data refresh")
                    
                    # Get updated MITRE display
                    mitre_html = self._format_mitre_display("Enterprise", "All Domains", None, "All Tactics", False)
                    
                    # Count MITRE items for status message
                    mitre_data = self._get_mitre_data()
                    technique_count = len(mitre_data.get('techniques', []))
                    group_count = len(mitre_data.get('groups', []))
                    
                    status_message = f"MITRE ATT&CK data refreshed • {technique_count} techniques, {group_count} threat groups"
                    status_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #4CAF50;'>
                        {status_message} • {datetime.now().strftime('%H:%M:%S')}
                    </div>"""
                    
                    logger.info(f"MITRE ATT&CK refresh completed: {technique_count} techniques, {group_count} groups")
                    return status_html, mitre_html
                    
                except Exception as e:
                    logger.error(f"Error refreshing MITRE ATT&CK data: {e}")
                    error_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #f44336;'>
                        Error refreshing MITRE ATT&CK data: {str(e)}
                    </div>"""
                    fallback_html = """
                    <div class='feed-content'>
                        <div style='text-align: center; color: #666; padding: 20px;'>
                            <div>🛡️ MITRE ATT&CK data unavailable</div>
                            <div style='font-size: 12px; margin-top: 8px;'>
                                Please try again later
                            </div>
                        </div>
                    </div>"""
                    return error_html, fallback_html


            # Simple Forum Directory Event Handlers
            async def refresh_simple_forum_directory():
                """Refresh simple forum directory and update display with ALL forums."""
                try:
                    logger.info("Starting forum directory refresh - attempting to load ALL forums")
                    
                    # Try to refresh forum service cache if available
                    refreshed_from_service = False
                    try:
                        from internal_assistant.di import global_injector
                        
                        # Try simple forum service first
                        try:
                            from internal_assistant.server.feeds.simple_forum_service import SimpleForumDirectoryService
                            forum_service = global_injector.get(SimpleForumDirectoryService)
                            
                            if hasattr(forum_service, 'refresh_if_needed'):
                                async with forum_service:
                                    await forum_service.refresh_if_needed()
                                    refreshed_from_service = True
                                    logger.info("Successfully refreshed SimpleForumDirectoryService")
                        except Exception as e:
                            logger.debug(f"Could not refresh SimpleForumDirectoryService: {e}")
                        
                        # Try main forum service if simple one didn't work
                        if not refreshed_from_service:
                            try:
                                from internal_assistant.server.feeds.forum_directory_service import ForumDirectoryService
                                forum_service = global_injector.get(ForumDirectoryService)
                                
                                if hasattr(forum_service, 'refresh_if_needed'):
                                    async with forum_service:
                                        await forum_service.refresh_if_needed()
                                        refreshed_from_service = True
                                        logger.info("Successfully refreshed ForumDirectoryService")
                            except Exception as e:
                                logger.debug(f"Could not refresh ForumDirectoryService: {e}")
                                
                    except Exception as e:
                        logger.warning(f"Could not access forum services for refresh: {e}")
                    
                    # Get updated forum display with ALL forums
                    forums_html = self._format_simple_forum_display()
                    
                    # Count forums for status message
                    forum_data = self._get_simple_forum_data()
                    forum_count = len(forum_data)
                    
                    status_message = f"Forum directory refreshed • {forum_count} forums loaded"
                    if refreshed_from_service:
                        status_message += " • Updated from service"
                    else:
                        status_message += " • Using fallback data"
                        
                    status_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #4CAF50;'>
                        {status_message} • {datetime.now().strftime('%H:%M:%S')}
                    </div>"""
                    
                    logger.info(f"Forum refresh completed: {forum_count} forums displayed")
                    return status_html, forums_html
                    
                except Exception as e:
                    logger.error(f"Error refreshing forum directory: {e}")
                    error_html = f"""
                    <div class='feed-status' style='font-size: 14px; color: #f44336;'>
                        Error refreshing forum directory: {str(e)}
                    </div>"""
                    fallback_html = """
                    <div class='feed-content'>
                        <div style='text-align: center; color: #666; padding: 20px;'>
                            <div>🌐 Forum directory unavailable</div>
                            <div style='font-size: 12px; margin-top: 8px;'>
                                Please try again later
                            </div>
                        </div>
                    </div>"""
                    return error_html, fallback_html
            
            # Wire up CVE Tracking handlers
            cve_refresh_btn.click(
                fn=refresh_cve_data,
                outputs=[cve_status, cve_display]
            )
            
            
            # Wire up MITRE ATT&CK handlers
            mitre_refresh_btn.click(
                fn=refresh_mitre_data,
                outputs=[mitre_status, mitre_display]
            )
            
            
            # Wire up Forum Directory handlers
            forum_refresh_btn.click(
                fn=refresh_simple_forum_directory,
                outputs=[forum_status, forum_display]
            )

        return blocks

    def get_ui_blocks(self) -> gr.Blocks:
        if self._ui_block is None:
            self._ui_block = self._build_ui_blocks()
        return self._ui_block

    def mount_in_app(self, app: FastAPI, path: str) -> None:
        blocks = self.get_ui_blocks()
        
        logger.info("Mounting the modern gradio UI, at path=%s", path)
        gr.mount_gradio_app(app, blocks, path=path, favicon_path=AVATAR_BOT)


if __name__ == "__main__":
    ui = global_injector.get(InternalAssistantUI)
    _blocks = ui.get_ui_blocks()
    # Disable queue system to avoid Pydantic schema errors with FastAPI
    # The queue system causes compatibility issues with FastAPI's dependency injection
    logger.info("Queue system disabled to avoid Pydantic schema errors")
    _blocks.launch(debug=False, show_api=False)
