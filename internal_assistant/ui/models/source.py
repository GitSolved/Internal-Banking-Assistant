"""
Source Model

This module defines the Source model for document references.
Extracted from the monolithic ui.py to centralize data models.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    """
    Model representing a document source reference.

    This model is used to track which documents were used to generate
    responses in RAG mode, enabling proper citation and verification.
    """

    file: str = Field(..., description="Name or path of the source file")

    page: str = Field(
        ..., description="Page number or section identifier within the file"
    )

    text: str = Field(..., description="Relevant text excerpt from the source")

    score: Optional[float] = Field(
        None, description="Relevance score if available from vector search"
    )

    metadata: Optional[dict] = Field(
        default_factory=dict, description="Additional metadata about the source"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "file": "security_policy.pdf",
                "page": "12",
                "text": "All access to sensitive data must be logged...",
                "score": 0.89,
                "metadata": {"category": "Policy", "last_modified": "2024-01-15"},
            }
        }

    def format_citation(self, style: str = "default") -> str:
        """
        Format the source as a citation.

        Args:
            style: Citation style to use

        Returns:
            Formatted citation string
        """
        if style == "inline":
            return f"[{self.file}, p.{self.page}]"
        elif style == "verbose":
            return (
                f"Source: {self.file} (Page {self.page})\nExcerpt: {self.text[:200]}..."
            )
        else:  # default
            return f"{self.file} - Page {self.page}"

    def to_html(self) -> str:
        """
        Convert source to HTML representation.

        Returns:
            HTML string for source display
        """
        score_html = f" (Score: {self.score:.2f})" if self.score else ""

        return f"""
        <div class="source-reference">
            <div class="source-header">
                <span class="source-file">{self.file}</span>
                <span class="source-page">Page {self.page}</span>
                <span class="source-score">{score_html}</span>
            </div>
            <div class="source-text">{self.text}</div>
        </div>
        """
