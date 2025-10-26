from typing import Any, Literal

from llama_index.core.schema import Document
from pydantic import BaseModel, ConfigDict, Field


class IngestedDoc(BaseModel):
    object: Literal["ingest.document"]
    doc_id: str = Field(examples=["c202d5e6-7b69-4869-81cc-dd574ee8ee11"])
    doc_metadata: dict[str, Any] | None = Field(
        examples=[
            {
                "page_label": "2",
                "file_name": "Sales Report Q3 2023.pdf",
            }
        ]
    )
    # Document quality and processing status
    processing_status: Literal["indexed", "processing", "failed", "low_quality"] = Field(
        default="indexed",
        description="Current processing status of the document"
    )
    quality_score: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Document quality score (0-100) based on chunks and text extraction"
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if processing failed"
    )
    chunk_count: int = Field(
        default=0,
        ge=0,
        description="Number of chunks generated from this document"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    def curate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        """Remove unwanted metadata keys while preserving file_name for smart routing."""
        for key in ["doc_id", "window", "original_text"]:
            metadata.pop(key, None)
        return metadata

    @staticmethod
    def from_document(document: Document) -> "IngestedDoc":
        return IngestedDoc(
            object="ingest.document",
            doc_id=document.doc_id,
            doc_metadata=IngestedDoc.curate_metadata(document.metadata),
        )
