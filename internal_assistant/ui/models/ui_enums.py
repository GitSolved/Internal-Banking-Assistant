"""
UI Enumerations

Extracted from ui.py to provide clean enumeration definitions.
"""

from enum import Enum


class Modes(str, Enum):
    """UI operation modes"""

    DOCUMENT_ASSISTANT = "RAG Mode"
    GENERAL_ASSISTANT = "General LLM"

    # Deprecated modes for backward compatibility
    RAG_MODE = "RAG Mode"
    SEARCH_MODE = "RAG Mode"
    COMPARE_MODE = "RAG Mode"
    SUMMARIZE_MODE = "RAG Mode"
    DIRECT_CHAT = "General LLM"


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

    if mode == Modes.DOCUMENT_ASSISTANT.value:
        return Modes.DOCUMENT_ASSISTANT.value
    elif mode == Modes.GENERAL_ASSISTANT.value:
        return Modes.GENERAL_ASSISTANT.value

    return Modes.DOCUMENT_ASSISTANT.value
