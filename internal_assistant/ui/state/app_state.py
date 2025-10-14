"""
Application State Schema

This module defines the complete application state structure using Pydantic models
for the Internal Assistant UI. It replaces scattered state management throughout
the UI with a centralized, typed, and validated state system.

Part of Phase 2.2: State Schema Design and Implementation
Author: UI Refactoring Team
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from pydantic import BaseModel, Field, validator, root_validator

from internal_assistant.ui.models.modes import Modes, normalize_mode
from internal_assistant.ui.models.source import Source

logger = logging.getLogger(__name__)


# ============================================================================
# Core Types and Enums
# ============================================================================


class ProcessingStatus(str, Enum):
    """Processing status for various operations."""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class FilterType(str, Enum):
    """Document filter types."""

    ALL = "all"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"


class CitationStyle(str, Enum):
    """Citation style options."""

    NO_SOURCES = "No Sources"
    BULLETS = "Bullets"
    NUMBERED = "Numbered"
    FOOTNOTES = "Footnotes"


class UIMode(str, Enum):
    """UI display modes."""

    NORMAL = "normal"
    COMPACT = "compact"
    EXPANDED = "expanded"


# ============================================================================
# Chat State Models
# ============================================================================


class ChatMessage(BaseModel):
    """Individual chat message."""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the message was created"
    )
    sources: List[Source] = Field(
        default_factory=list, description="Sources used for this message"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional message metadata"
    )


class ChatState(BaseModel):
    """Chat-related state."""

    mode: str = Field(
        default=Modes.DOCUMENT_ASSISTANT.value, description="Current chat mode"
    )
    history: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="Chat message history as (user, assistant) tuples",
    )
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Structured chat messages"
    )
    system_prompt: str = Field(default="", description="Current system prompt")
    is_processing: bool = Field(
        default=False, description="Whether chat is currently processing"
    )
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.IDLE, description="Current processing status"
    )
    last_response_sources: List[Source] = Field(
        default_factory=list, description="Sources from last response"
    )
    error_message: Optional[str] = Field(
        default=None, description="Last error message if any"
    )

    @validator("mode", pre=True)
    def normalize_chat_mode(cls, v):
        """Normalize the chat mode to a valid value."""
        return normalize_mode(v)

    @validator("history", pre=True)
    def validate_history(cls, v):
        """Ensure history is a list of 2-tuples."""
        if not isinstance(v, list):
            return []
        return [
            tuple(item) if len(item) >= 2 else (item[0] if item else "", "")
            for item in v
        ]


# ============================================================================
# Document State Models
# ============================================================================


class DocumentCounts(BaseModel):
    """Document counts by type and category."""

    total: int = Field(default=0, description="Total document count")
    security_compliance: int = Field(
        default=0, description="Security & compliance documents"
    )
    policy_governance: int = Field(
        default=0, description="Policy & governance documents"
    )
    threat_intelligence: int = Field(
        default=0, description="Threat intelligence documents"
    )
    incident_response: int = Field(default=0, description="Incident response documents")
    technical_infrastructure: int = Field(
        default=0, description="Technical & infrastructure documents"
    )
    research_analysis: int = Field(
        default=0, description="Research & analysis documents"
    )

    # File type counts
    pdf_count: int = Field(default=0, description="PDF document count")
    docx_count: int = Field(default=0, description="Word document count")
    txt_count: int = Field(default=0, description="Text document count")
    other_count: int = Field(default=0, description="Other document types count")


class DocumentMetadata(BaseModel):
    """Metadata for a single document."""

    doc_id: str = Field(..., description="Document identifier")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type")
    file_size: int = Field(default=0, description="File size in bytes")
    upload_date: datetime = Field(
        default_factory=datetime.now, description="Upload timestamp"
    )
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.IDLE, description="Processing status"
    )
    blocks_count: int = Field(default=0, description="Number of text blocks")
    usage_count: int = Field(default=0, description="Number of times accessed")
    last_used: Optional[datetime] = Field(
        default=None, description="Last access timestamp"
    )
    tags: List[str] = Field(default_factory=list, description="Document tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DocumentFilter(BaseModel):
    """Document filtering configuration."""

    type: FilterType = Field(default=FilterType.ALL, description="Current filter type")
    search_query: str = Field(default="", description="Search query text")
    selected_tags: Set[str] = Field(
        default_factory=set, description="Selected tag filters"
    )
    date_range: Optional[Tuple[datetime, datetime]] = Field(
        default=None, description="Date range filter"
    )
    size_range: Optional[Tuple[int, int]] = Field(
        default=None, description="Size range filter in bytes"
    )


class DocumentState(BaseModel):
    """Document library and management state."""

    counts: DocumentCounts = Field(
        default_factory=DocumentCounts, description="Document counts"
    )
    documents: Dict[str, DocumentMetadata] = Field(
        default_factory=dict, description="Document metadata by ID"
    )
    filter: DocumentFilter = Field(
        default_factory=DocumentFilter, description="Current filters"
    )
    library_content: str = Field(
        default="", description="HTML content for document library"
    )
    selected_documents: Set[str] = Field(
        default_factory=set, description="Currently selected document IDs"
    )
    upload_status: ProcessingStatus = Field(
        default=ProcessingStatus.IDLE, description="Upload operation status"
    )
    processing_queue: List[str] = Field(
        default_factory=list, description="Documents queued for processing"
    )
    last_refresh: Optional[datetime] = Field(
        default=None, description="Last library refresh timestamp"
    )


# ============================================================================
# Settings State Models
# ============================================================================


class ModelInfo(BaseModel):
    """Information about current models."""

    llm_model: str = Field(default="Unknown", description="Current LLM model")
    embedding_model: str = Field(
        default="Unknown", description="Current embedding model"
    )
    llm_mode: str = Field(default="unknown", description="LLM provider mode")
    embedding_mode: str = Field(
        default="unknown", description="Embedding provider mode"
    )


class ChatSettings(BaseModel):
    """Chat-related settings."""

    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Response temperature"
    )
    max_tokens: int = Field(
        default=512, ge=1, le=4096, description="Maximum response tokens"
    )
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    citation_style: CitationStyle = Field(
        default=CitationStyle.BULLETS, description="Citation format style"
    )
    show_sources: bool = Field(default=True, description="Whether to show sources")


class RAGSettings(BaseModel):
    """RAG-specific settings."""

    similarity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Similarity threshold for retrieval"
    )
    max_sources: int = Field(
        default=5, ge=1, le=20, description="Maximum sources to retrieve"
    )
    chunk_overlap: int = Field(
        default=50, ge=0, le=500, description="Text chunk overlap in characters"
    )
    enable_reranking: bool = Field(default=True, description="Whether to use reranking")


class SettingsState(BaseModel):
    """Application settings state."""

    system_prompt: str = Field(default="", description="System prompt text")
    chat: ChatSettings = Field(
        default_factory=ChatSettings, description="Chat-related settings"
    )
    rag: RAGSettings = Field(
        default_factory=RAGSettings, description="RAG-specific settings"
    )
    model_info: ModelInfo = Field(
        default_factory=ModelInfo, description="Current model information"
    )
    ui_mode: UIMode = Field(default=UIMode.NORMAL, description="UI display mode")
    auto_save: bool = Field(default=True, description="Whether to auto-save settings")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")

    class Config:
        """Pydantic configuration."""

        # Disable protected namespace warnings for model_info field
        protected_namespaces = ()


# ============================================================================
# External Information State Models
# ============================================================================


class FeedItem(BaseModel):
    """Individual feed item."""

    title: str = Field(..., description="Feed item title")
    content: str = Field(default="", description="Feed item content")
    url: str = Field(..., description="Feed item URL")
    published: datetime = Field(..., description="Publication timestamp")
    source: str = Field(..., description="Feed source name")
    category: str = Field(default="general", description="Content category")
    tags: List[str] = Field(default_factory=list, description="Content tags")


class CVEInfo(BaseModel):
    """CVE vulnerability information."""

    cve_id: str = Field(..., description="CVE identifier")
    description: str = Field(default="", description="Vulnerability description")
    severity: str = Field(default="unknown", description="Severity level")
    score: Optional[float] = Field(default=None, description="CVSS score")
    published: datetime = Field(..., description="Publication date")
    modified: Optional[datetime] = Field(
        default=None, description="Last modification date"
    )
    references: List[str] = Field(default_factory=list, description="Reference URLs")


class MitreAttackInfo(BaseModel):
    """MITRE ATT&CK framework information."""

    technique_id: str = Field(..., description="MITRE technique ID")
    technique_name: str = Field(..., description="Technique name")
    tactic: str = Field(default="", description="Associated tactic")
    description: str = Field(default="", description="Technique description")
    platforms: List[str] = Field(
        default_factory=list, description="Applicable platforms"
    )
    data_sources: List[str] = Field(
        default_factory=list, description="Data sources for detection"
    )


class ExternalInfoState(BaseModel):
    """External information and feeds state."""

    feeds: List[FeedItem] = Field(default_factory=list, description="RSS feed items")
    cve_data: List[CVEInfo] = Field(
        default_factory=list, description="CVE vulnerability data"
    )
    mitre_data: List[MitreAttackInfo] = Field(
        default_factory=list, description="MITRE ATT&CK data"
    )
    feed_count: int = Field(default=0, description="Number of configured feeds")
    last_feed_refresh: Optional[datetime] = Field(
        default=None, description="Last feed refresh timestamp"
    )
    feed_refresh_status: ProcessingStatus = Field(
        default=ProcessingStatus.IDLE, description="Feed refresh status"
    )
    selected_time_range: str = Field(
        default="24h", description="Selected time range for feeds"
    )
    feed_filters: Dict[str, bool] = Field(
        default_factory=dict, description="Feed category filters"
    )
    error_messages: List[str] = Field(
        default_factory=list, description="Feed-related error messages"
    )


# ============================================================================
# UI State Models
# ============================================================================


class UIComponentState(BaseModel):
    """State for individual UI components."""

    is_visible: bool = Field(default=True, description="Whether component is visible")
    is_expanded: bool = Field(default=True, description="Whether component is expanded")
    height: Optional[int] = Field(
        default=None, description="Component height in pixels"
    )
    width: Optional[int] = Field(default=None, description="Component width in pixels")
    css_classes: List[str] = Field(
        default_factory=list, description="Active CSS classes"
    )


class UIState(BaseModel):
    """UI-specific state management."""

    current_tab: str = Field(default="chat", description="Currently active tab")
    sidebar_collapsed: bool = Field(
        default=False, description="Whether sidebar is collapsed"
    )
    theme: str = Field(default="dark", description="UI theme")
    components: Dict[str, UIComponentState] = Field(
        default_factory=dict, description="Component states"
    )
    status_messages: List[str] = Field(
        default_factory=list, description="Current status messages"
    )
    notifications: List[Dict[str, Any]] = Field(
        default_factory=list, description="Pending notifications"
    )
    modal_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Active modal state"
    )
    loading_states: Dict[str, bool] = Field(
        default_factory=dict, description="Loading states by component"
    )
    error_states: Dict[str, str] = Field(
        default_factory=dict, description="Error states by component"
    )


# ============================================================================
# Root Application State
# ============================================================================


class ApplicationState(BaseModel):
    """Root application state containing all domain states."""

    # Core state domains
    chat: ChatState = Field(default_factory=ChatState, description="Chat-related state")
    documents: DocumentState = Field(
        default_factory=DocumentState, description="Document management state"
    )
    settings: SettingsState = Field(
        default_factory=SettingsState, description="Application settings"
    )
    external: ExternalInfoState = Field(
        default_factory=ExternalInfoState, description="External information state"
    )
    ui: UIState = Field(default_factory=UIState, description="UI-specific state")

    # Global state
    app_version: str = Field(default="1.0.0", description="Application version")
    session_id: str = Field(
        default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="Current session ID",
    )
    startup_time: datetime = Field(
        default_factory=datetime.now, description="Application startup time"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last user activity timestamp"
    )

    # State metadata
    state_version: str = Field(default="2.2.0", description="State schema version")
    last_save: Optional[datetime] = Field(
        default=None, description="Last state save timestamp"
    )
    is_dirty: bool = Field(
        default=False, description="Whether state has unsaved changes"
    )

    class Config:
        """Pydantic configuration."""

        # Enable arbitrary types for complex objects
        arbitrary_types_allowed = True
        # Validate on assignment
        validate_assignment = True
        # Use enum values instead of enum objects in serialization
        use_enum_values = True
        # Disable protected namespace warnings
        protected_namespaces = ()

    @root_validator(skip_on_failure=True)
    def validate_state_consistency(cls, values):
        """Validate consistency between state domains."""
        chat_state = values.get("chat")
        settings_state = values.get("settings")

        # Ensure chat mode is consistent with available models
        if chat_state and settings_state:
            if chat_state.mode == Modes.DOCUMENT_ASSISTANT.value:
                if settings_state.model_info.llm_model == "Unknown":
                    logger.warning(
                        "Document Assistant mode selected but no LLM model configured"
                    )

        return values

    def update_activity_timestamp(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
        self.is_dirty = True

    def mark_clean(self):
        """Mark the state as clean (saved)."""
        self.is_dirty = False
        self.last_save = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current application state."""
        return {
            "session_id": self.session_id,
            "app_version": self.app_version,
            "uptime": str(datetime.now() - self.startup_time),
            "last_activity": self.last_activity.isoformat(),
            "chat": {
                "mode": self.chat.mode,
                "history_length": len(self.chat.history),
                "is_processing": self.chat.is_processing,
            },
            "documents": {
                "total_count": self.documents.counts.total,
                "selected_count": len(self.documents.selected_documents),
                "processing_queue_size": len(self.documents.processing_queue),
            },
            "settings": {
                "system_prompt_length": len(self.settings.system_prompt),
                "llm_model": self.settings.model_info.llm_model,
                "embedding_model": self.settings.model_info.embedding_model,
            },
            "external": {
                "feed_count": self.external.feed_count,
                "cve_count": len(self.external.cve_data),
                "mitre_count": len(self.external.mitre_data),
            },
            "ui": {
                "current_tab": self.ui.current_tab,
                "theme": self.ui.theme,
                "active_components": len(
                    [c for c in self.ui.components.values() if c.is_visible]
                ),
            },
            "state_metadata": {
                "version": self.state_version,
                "is_dirty": self.is_dirty,
                "last_save": self.last_save.isoformat() if self.last_save else None,
            },
        }


# ============================================================================
# State Factory Functions
# ============================================================================


def create_default_application_state() -> ApplicationState:
    """
    Create a default application state with sensible defaults.

    Returns:
        Initialized ApplicationState with default values
    """
    return ApplicationState()


def create_application_state_from_legacy(
    legacy_mode: str = None,
    legacy_history: List[Tuple[str, str]] = None,
    legacy_system_prompt: str = None,
    legacy_temperature: float = None,
    legacy_similarity: float = None,
    legacy_citation_style: str = None,
    **kwargs,
) -> ApplicationState:
    """
    Create application state from legacy scattered variables.

    Args:
        legacy_mode: Legacy mode string
        legacy_history: Legacy chat history
        legacy_system_prompt: Legacy system prompt
        legacy_temperature: Legacy temperature setting
        legacy_similarity: Legacy similarity threshold
        legacy_citation_style: Legacy citation style
        **kwargs: Additional legacy values

    Returns:
        ApplicationState initialized from legacy values
    """
    state = ApplicationState()

    # Migrate chat state
    if legacy_mode:
        state.chat.mode = normalize_mode(legacy_mode)

    if legacy_history:
        state.chat.history = legacy_history

    # Migrate settings
    if legacy_system_prompt:
        state.settings.system_prompt = legacy_system_prompt

    if legacy_temperature is not None:
        state.settings.chat.temperature = max(0.0, min(2.0, legacy_temperature))

    if legacy_similarity is not None:
        state.settings.rag.similarity_threshold = max(0.0, min(1.0, legacy_similarity))

    if legacy_citation_style:
        try:
            state.settings.chat.citation_style = CitationStyle(legacy_citation_style)
        except ValueError:
            logger.warning(f"Unknown citation style: {legacy_citation_style}")

    # Apply any additional kwargs
    for key, value in kwargs.items():
        try:
            # Use dot notation to set nested values
            keys = key.split(".")
            current = state
            for k in keys[:-1]:
                current = getattr(current, k)
            setattr(current, keys[-1], value)
        except (AttributeError, TypeError):
            logger.warning(f"Could not set legacy value: {key} = {value}")

    logger.info("ApplicationState created from legacy values")
    return state


def validate_application_state(state: ApplicationState) -> Tuple[bool, List[str]]:
    """
    Validate an application state and return validation results.

    Args:
        state: ApplicationState to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    try:
        # Re-validate the state to catch any constraint violations
        state.__class__.validate(state.dict())
    except ValidationError as e:
        errors.extend([f"Validation error: {error['msg']}" for error in e.errors()])

    # Custom business logic validation
    if state.chat.mode == Modes.DOCUMENT_ASSISTANT.value:
        if state.documents.counts.total == 0:
            errors.append("Document Assistant mode selected but no documents available")

    if state.settings.chat.temperature < 0 or state.settings.chat.temperature > 2:
        errors.append(f"Invalid temperature: {state.settings.chat.temperature}")

    if (
        state.settings.rag.similarity_threshold < 0
        or state.settings.rag.similarity_threshold > 1
    ):
        errors.append(
            f"Invalid similarity threshold: {state.settings.rag.similarity_threshold}"
        )

    return len(errors) == 0, errors


# ============================================================================
# State Migration Functions
# ============================================================================


def migrate_state_schema(
    old_state: Dict[str, Any], from_version: str, to_version: str
) -> ApplicationState:
    """
    Migrate state from one schema version to another.

    Args:
        old_state: State dictionary in old format
        from_version: Source schema version
        to_version: Target schema version

    Returns:
        Migrated ApplicationState
    """
    if from_version == to_version:
        return ApplicationState(**old_state)

    # Schema migration logic would go here
    # For now, attempt best-effort migration
    try:
        return ApplicationState(**old_state)
    except ValidationError as e:
        logger.warning(f"State migration failed: {e}")
        # Return default state if migration fails
        return create_default_application_state()


# ============================================================================
# State Serialization Helpers
# ============================================================================


def serialize_application_state(
    state: ApplicationState, include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Serialize application state to a dictionary for persistence.

    Args:
        state: ApplicationState to serialize
        include_metadata: Whether to include state metadata

    Returns:
        Serialized state dictionary
    """
    state_dict = state.dict()

    if not include_metadata:
        # Remove metadata fields for cleaner export
        metadata_fields = [
            "session_id",
            "startup_time",
            "last_activity",
            "state_version",
            "last_save",
            "is_dirty",
        ]
        for field in metadata_fields:
            state_dict.pop(field, None)

    return state_dict


def deserialize_application_state(state_dict: Dict[str, Any]) -> ApplicationState:
    """
    Deserialize application state from a dictionary.

    Args:
        state_dict: State dictionary to deserialize

    Returns:
        ApplicationState instance
    """
    try:
        return ApplicationState(**state_dict)
    except ValidationError as e:
        logger.error(f"Failed to deserialize state: {e}")
        # Return default state with error logging
        return create_default_application_state()
