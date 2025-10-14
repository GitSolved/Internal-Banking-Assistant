"""
UI Data Models

Extracted from ui.py to provide clean data structures for UI components.
"""

from pydantic import BaseModel


class Source(BaseModel):
    """Represents a document source with metadata"""

    file: str
    page: str
    text: str

    @classmethod
    def curate_sources(cls, sources: list) -> list:
        """
        Curates and deduplicates sources

        Extracted from ui.py Source class
        """
        # TODO: Extract source curation logic from ui.py
        return sources
