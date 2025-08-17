from typing import Any, Literal

from llama_index.core.schema import Document
from pydantic import BaseModel, Field, ConfigDict


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
