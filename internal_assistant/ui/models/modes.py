"""
Modes Module

This module defines the assistant modes and their compatibility mappings.
Extracted from the monolithic ui.py to centralize mode management.
"""

from enum import Enum
from typing import List, Dict


class Modes(str, Enum):
    """
    Assistant operation modes.

    The Internal Assistant supports two primary modes:
    - DOCUMENT_ASSISTANT: RAG mode using uploaded documents for context
    - GENERAL_ASSISTANT: Direct LLM interaction without document context
    """

    DOCUMENT_ASSISTANT = "RAG Mode"
    GENERAL_ASSISTANT = "General LLM"

    # Deprecated modes for backward compatibility - will map to new modes
    RAG_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SEARCH_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    COMPARE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    SUMMARIZE_MODE = "RAG Mode"  # Maps to DOCUMENT_ASSISTANT
    DIRECT_CHAT = "General LLM"  # Maps to GENERAL_ASSISTANT


# List of supported modes for UI display
SUPPORTED_MODES: List[Modes] = [
    Modes.DOCUMENT_ASSISTANT,
    Modes.GENERAL_ASSISTANT,
]

# Backward compatibility mapping for legacy mode names
LEGACY_MODE_MAPPING: Dict[str, str] = {
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

    Args:
        mode: Mode string to normalize

    Returns:
        Normalized mode string (either "RAG Mode" or "General LLM")
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


def get_mode_description(mode: str) -> str:
    """
    Get a description for the given mode.

    Args:
        mode: Mode string

    Returns:
        Description of the mode
    """
    normalized = normalize_mode(mode)

    if normalized == Modes.DOCUMENT_ASSISTANT.value:
        return (
            "Use your uploaded documents for context-aware responses. "
            "The assistant will search through your documents to provide "
            "accurate, sourced information."
        )
    elif normalized == Modes.GENERAL_ASSISTANT.value:
        return (
            "Direct interaction with the language model without document context. "
            "Useful for general questions, creative tasks, and conversations "
            "that don't require specific document knowledge."
        )

    return "Unknown mode"


def is_document_mode(mode: str) -> bool:
    """
    Check if the given mode uses document context.

    Args:
        mode: Mode string to check

    Returns:
        True if mode uses documents, False otherwise
    """
    return normalize_mode(mode) == Modes.DOCUMENT_ASSISTANT.value
