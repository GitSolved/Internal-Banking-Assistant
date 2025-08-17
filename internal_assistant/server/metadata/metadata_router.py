from fastapi import APIRouter, Depends, Request
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.components.node_store.node_store_component import NodeStoreComponent
from internal_assistant.server.ingest.model import IngestedDoc
from injector import Injector, inject
from llama_index.core.storage.docstore.types import RefDocInfo
from typing import Annotated, Dict, Any

def get_injector(request: Request) -> Injector:
    return request.state.injector

# This router exposes only non-sensitive metadata for privacy
metadata_router = APIRouter(prefix="/metadata", tags=["Metadata"])

@metadata_router.get("/files")
def list_files_metadata(injector: Annotated[Injector, Depends(get_injector)]):
    """Return file/document metadata: file names, titles, IDs, content hash, page count."""
    ingest_service: IngestService = injector.get(IngestService)
    node_store: NodeStoreComponent = injector.get(NodeStoreComponent)
    docstore = node_store.doc_store

    files_metadata = []
    for doc in ingest_service.list_ingested():
        doc_id = doc.doc_id
        doc_metadata = doc.doc_metadata or {}
        file_name = doc_metadata.get("file_name", "-")
        content_hash = doc_metadata.get("content_hash", None)

        # Compute page count: count unique page_label values among all nodes for this doc_id
        page_labels = set()
        try:
            ref_doc_info: RefDocInfo = docstore.get_ref_doc_info(doc_id)
            if ref_doc_info and hasattr(ref_doc_info, "node_ids"):
                node_ids = ref_doc_info.node_ids
                nodes = docstore.get_nodes(node_ids=node_ids)
                for node in nodes:
                    page_label = node.metadata.get("page_label")
                    if page_label is not None:
                        page_labels.add(page_label)
        except Exception:
            pass
        page_count = len(page_labels) if page_labels else None

        files_metadata.append({
            "file_name": file_name,
            "doc_id": doc_id,
            "content_hash": content_hash,
            "page_count": page_count,
        })
    return {"files": files_metadata}

@metadata_router.get("/chunks/{document_id}")
def list_chunk_metadata(document_id: str, injector: Annotated[Injector, Depends(get_injector)]):
    """Return chunk/node metadata for a given document ID."""
    node_store: NodeStoreComponent = injector.get(NodeStoreComponent)
    docstore = node_store.doc_store
    chunk_metadata = []
    try:
        ref_doc_info: RefDocInfo = docstore.get_ref_doc_info(document_id)
        if ref_doc_info and hasattr(ref_doc_info, "node_ids"):
            node_ids = ref_doc_info.node_ids
            nodes = docstore.get_nodes(node_ids=node_ids)
            for node in nodes:
                meta = dict(node.metadata) if hasattr(node, "metadata") else {}
                chunk_metadata.append({
                    "chunk_id": getattr(node, "node_id", None),
                    "position": meta.get("page_label"),
                    "length_tokens": getattr(node, "num_tokens", None),
                    "length_words": len(node.get_content().split()) if hasattr(node, "get_content") else None,
                    "file_name": meta.get("file_name"),
                    "doc_id": meta.get("doc_id"),
                    "metadata": meta,
                })
    except Exception:
        pass
    return {"chunks": chunk_metadata}
