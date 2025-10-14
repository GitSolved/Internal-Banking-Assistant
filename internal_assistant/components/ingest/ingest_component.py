"""Simplified ingest component - clean version.

SIMPLIFICATION CHANGES (2025-10-03):
- Reduced from 1,295 lines to 195 lines (85% reduction)
- Removed excessive verification/rollback code
- Removed unused BatchIngestComponent, ParallelizedIngestComponent, PipelineIngestComponent
- Simplified logging (100+ statements → ~30)
- Removed defensive programming that caused bugs
- Trust LlamaIndex's built-in persistence mechanisms
"""
import abc
import logging
import threading
from pathlib import Path
from typing import Any

from llama_index.core.data_structs import IndexDict
from llama_index.core.embeddings.utils import EmbedType
from llama_index.core.indices import VectorStoreIndex, load_index_from_storage
from llama_index.core.indices.base import BaseIndex
from llama_index.core.ingestion import run_transformations
from llama_index.core.schema import Document, TransformComponent
from llama_index.core.storage import StorageContext
from llama_index.core.storage.docstore.types import RefDocInfo

from internal_assistant.components.ingest.ingest_helper import IngestionHelper
from internal_assistant.paths import local_data_path
from internal_assistant.settings.settings import Settings

logger = logging.getLogger(__name__)

# VERSION MARKER - Change this with each fix to verify code is loaded
CODE_VERSION = "v5_DIAGNOSTIC_LOGGING_2025-10-12"
logger.info(f"🔧 [CODE_VERSION] ingest_component.py loaded: {CODE_VERSION}")
logger.info(f"🔧 [CODE_VERSION] This version includes comprehensive diagnostic logging for persistence debugging")


class BaseIngestComponent(abc.ABC):
    def __init__(
        self,
        storage_context: StorageContext,
        embed_model: EmbedType,
        transformations: list[TransformComponent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        logger.debug("Initializing ingest component: %s", type(self).__name__)
        self.storage_context = storage_context
        self.embed_model = embed_model
        self.transformations = transformations

    @abc.abstractmethod
    def ingest(self, file_name: str, file_data: Path) -> list[Document]:
        pass

    @abc.abstractmethod
    def bulk_ingest(self, files: list[tuple[str, Path]]) -> list[Document]:
        pass

    @abc.abstractmethod
    def delete(self, doc_id: str) -> None:
        pass


class BaseIngestComponentWithIndex(BaseIngestComponent, abc.ABC):
    def __init__(
        self,
        storage_context: StorageContext,
        embed_model: EmbedType,
        transformations: list[TransformComponent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(storage_context, embed_model, transformations, *args, **kwargs)
        self.show_progress = True
        self._index_thread_lock = threading.Lock()
        self._index = self._initialize_index()

    def _initialize_index(self) -> BaseIndex[IndexDict]:
        """Initialize or load index from storage."""
        try:
            # DIAGNOSTIC: Check docstore file location and contents BEFORE load
            logger.info(f"[LOAD_PATH] Storage context persist dir: {getattr(self.storage_context, 'persist_dir', 'NOT SET')}")
            logger.info(f"[LOAD_PATH] Looking for docstore.json at: {local_data_path / 'docstore.json'}")

            docstore_file = local_data_path / "docstore.json"
            if docstore_file.exists():
                logger.info(f"[LOAD_PATH] ✅ Docstore file exists, size: {docstore_file.stat().st_size} bytes")
                # Load and count entries
                import json
                try:
                    with open(docstore_file) as f:
                        data = json.load(f)
                        ref_doc_count = len(data.get("docstore/ref_doc_info", {}))
                        logger.info(f"[LOAD_PATH] Docstore contains {ref_doc_count} ref_doc_info entries in file")
                except Exception as e:
                    logger.error(f"[LOAD_PATH] Failed to read docstore.json: {e}")
            else:
                logger.warning(f"[LOAD_PATH] ❌ Docstore file DOES NOT EXIST at {docstore_file}")

            index = load_index_from_storage(
                storage_context=self.storage_context,
                store_nodes_override=True,
                show_progress=self.show_progress,
                embed_model=self.embed_model,
                transformations=self.transformations,
            )
            logger.info("Loaded existing index from storage")

            # DIAGNOSTIC: Check how many ref_doc_info entries actually loaded into memory
            loaded_count = len(index.docstore.get_all_ref_doc_info())
            logger.info(f"[LOAD_PATH] ✅ After load: index.docstore has {loaded_count} ref_doc_info entries in memory")
        except ValueError:
            logger.info("Creating new vector store index")
            index = VectorStoreIndex.from_documents(
                [],
                storage_context=self.storage_context,
                store_nodes_override=True,
                show_progress=self.show_progress,
                embed_model=self.embed_model,
                transformations=self.transformations,
            )
            index.storage_context.persist(persist_dir=str(local_data_path))
        return index

    def _save_index(self) -> None:
        """Save index to disk - matches private-gpt implementation."""
        logger.debug("Persisting the index and docstore")

        # DIAGNOSTIC: Log call stack to verify this method is being called
        import traceback
        logger.info(f"[PERSIST_CALLSTACK] _save_index() called from:")
        for line in traceback.format_stack()[-5:-1]:
            logger.info(f"[PERSIST_CALLSTACK]   {line.strip()}")

        # DIAGNOSTIC: Log docstore state BEFORE persist
        try:
            ref_doc_count_before = len(self._index.docstore.get_all_ref_doc_info())
            kvstore_before = self._index.docstore._kvstore._data
            logger.info(f"[PERSIST_DEBUG] BEFORE persist:")
            logger.info(f"[PERSIST_DEBUG]   - ref_doc_info count (API): {ref_doc_count_before}")
            logger.info(f"[PERSIST_DEBUG]   - kvstore collections: {list(kvstore_before.keys())}")
            for key in kvstore_before:
                logger.info(f"[PERSIST_DEBUG]   - {key}: {len(kvstore_before[key])} items")
        except Exception as e:
            logger.warning(f"[PERSIST_DEBUG] Could not log before-persist state: {e}")

        # DIAGNOSTIC: Log persist path
        docstore_path = local_data_path / "docstore.json"
        logger.info(f"[PERSIST_PATH] Attempting to persist to: {docstore_path.absolute()}")
        logger.info(f"[PERSIST_PATH] File exists before persist: {docstore_path.exists()}")
        if docstore_path.exists():
            logger.info(f"[PERSIST_PATH] File size before persist: {docstore_path.stat().st_size} bytes")

        # Perform the persist with exception handling
        try:
            self._index.storage_context.persist(persist_dir=str(local_data_path))
            logger.info("[PERSIST_SUCCESS] ✅ storage_context.persist() succeeded")
        except Exception as e:
            logger.error(f"[PERSIST_FAILURE] ❌ storage_context.persist() failed: {e}", exc_info=True)
            raise

        # CRITICAL FIX: Explicitly persist docstore separately
        # storage_context.persist() doesn't always persist docstore changes
        try:
            self._index.docstore.persist(persist_path=str(docstore_path))
            logger.info(f"[PERSIST_SUCCESS] ✅ Explicitly persisted docstore to {docstore_path}")
        except Exception as e:
            logger.error(f"[PERSIST_FAILURE] ❌ docstore.persist() failed: {e}", exc_info=True)
            raise

        # DIAGNOSTIC: Check file after persist
        logger.info(f"[PERSIST_PATH] File exists after persist: {docstore_path.exists()}")
        if docstore_path.exists():
            file_size = docstore_path.stat().st_size
            logger.info(f"[PERSIST_PATH] File size after persist: {file_size} bytes")
            if file_size == 0:
                logger.error(f"[PERSIST_PATH] ❌ WARNING: Docstore file is EMPTY (0 bytes)!")
        else:
            logger.error(f"[PERSIST_PATH] ❌ WARNING: Docstore file DOES NOT EXIST after persist!")

        # DIAGNOSTIC: Log docstore state AFTER persist
        try:
            ref_doc_count_after = len(self._index.docstore.get_all_ref_doc_info())
            kvstore_after = self._index.docstore._kvstore._data
            logger.info(f"[PERSIST_DEBUG] AFTER persist:")
            logger.info(f"[PERSIST_DEBUG]   - ref_doc_info count (API): {ref_doc_count_after}")
            logger.info(f"[PERSIST_DEBUG]   - kvstore collections: {list(kvstore_after.keys())}")
            for key in kvstore_after:
                logger.info(f"[PERSIST_DEBUG]   - {key}: {len(kvstore_after[key])} items")
        except Exception as e:
            logger.warning(f"[PERSIST_DEBUG] Could not log after-persist state: {e}")

        logger.debug("Persisted the index and docstore")

    def delete(self, doc_id: str) -> None:
        """Delete a document from the index.

        Handles corrupted docstores where nodes are missing ref_doc_id fields.
        Falls back to manual cleanup if standard deletion fails with KeyError.
        """
        with self._index_thread_lock:
            logger.info("Deleting document: %s", doc_id)
            try:
                # Try standard LlamaIndex deletion first
                self._index.delete_ref_doc(doc_id, delete_from_docstore=True)
                self._save_index()
                logger.info("Successfully deleted document: %s", doc_id)
            except KeyError as e:
                # Handle corrupted docstore (nodes missing ref_doc_id)
                logger.warning(
                    f"Standard deletion failed with KeyError: {e}. "
                    f"Falling back to manual cleanup for corrupted docstore."
                )

                try:
                    # Get node IDs from ref_doc_info
                    ref_doc_info = self._index.docstore.get_ref_doc_info(doc_id)
                    if not ref_doc_info:
                        logger.error(f"Document {doc_id} not found in ref_doc_info")
                        raise ValueError(f"Document {doc_id} not found")

                    node_ids = ref_doc_info.node_ids
                    logger.info(f"Manual deletion: removing {len(node_ids)} nodes for doc {doc_id}")

                    # Delete nodes from vector store
                    if node_ids:
                        try:
                            self._index.vector_store.delete_nodes(node_ids)
                            logger.info(f"Deleted {len(node_ids)} nodes from vector store")
                        except Exception as ve:
                            logger.warning(f"Vector store deletion partial failure: {ve}")

                    # Delete nodes from docstore (direct kvstore access)
                    deleted_nodes = 0
                    for node_id in node_ids:
                        try:
                            self._index.docstore._kvstore.delete(
                                node_id,
                                collection=self._index.docstore._node_collection
                            )
                            deleted_nodes += 1
                        except KeyError:
                            # Node might not exist in docstore, continue
                            logger.debug(f"Node {node_id} not in docstore (already deleted or missing)")

                    logger.info(f"Deleted {deleted_nodes}/{len(node_ids)} nodes from docstore")

                    # Delete ref_doc_info entry
                    self._index.docstore._kvstore.delete(
                        doc_id,
                        collection=self._index.docstore._ref_doc_collection
                    )
                    logger.info(f"Deleted ref_doc_info for doc {doc_id}")

                    # Persist changes
                    self._save_index()
                    logger.info(f"Successfully deleted document {doc_id} via manual cleanup")

                except Exception as cleanup_error:
                    logger.error(f"Manual cleanup failed for {doc_id}: {cleanup_error}", exc_info=True)
                    raise

            except Exception as e:
                logger.error("Failed to delete document %s: %s", doc_id, e)
                raise


class SimpleIngestComponent(BaseIngestComponentWithIndex):
    def __init__(
        self,
        storage_context: StorageContext,
        embed_model: EmbedType,
        transformations: list[TransformComponent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(storage_context, embed_model, transformations, *args, **kwargs)

    def ingest(self, file_name: str, file_data: Path) -> list[Document]:
        """Ingest a single file."""
        logger.info("Ingesting file: %s", file_name)

        if not file_data.exists():
            logger.error("File does not exist: %s", file_data)
            return []

        try:
            # Transform file to documents
            documents = IngestionHelper.transform_file_into_documents(file_name, file_data)
            logger.info("Created %d documents from %s", len(documents), file_name)

            if documents:
                # Save documents
                saved_docs = self._save_docs(documents)
                logger.info("Successfully saved %d documents from %s", len(saved_docs), file_name)
                return saved_docs
            return []

        except Exception as e:
            logger.error("Error ingesting %s: %s", file_name, e, exc_info=True)
            return []

    def bulk_ingest(self, files: list[tuple[str, Path]]) -> list[Document]:
        """Ingest multiple files."""
        saved_documents = []
        for file_name, file_data in files:
            documents = IngestionHelper.transform_file_into_documents(file_name, file_data)
            saved_documents.extend(self._save_docs(documents))
        return saved_documents

    def _save_docs(self, documents: list[Document]) -> list[Document]:
        """Save documents to index.

        CRITICAL FIX (2025-10-11): Must explicitly create ref_doc_info entries.
        LlamaIndex's insert() method does NOT automatically create ref_doc_info.
        Must use pattern: run_transformations() → insert_nodes() → set_document_hash()

        This matches private-gpt's BatchIngestComponent pattern which explicitly
        calls set_document_hash() to create ref_doc_info entries.
        """
        if not documents:
            return []

        logger.info(f"Transforming {len(documents)} documents into nodes")

        # Transform documents to nodes (handles chunking and embeddings)
        nodes = run_transformations(
            documents,
            self.transformations,
            show_progress=self.show_progress,
        )
        logger.info(f"Created {len(nodes)} nodes from {len(documents)} documents")

        with self._index_thread_lock:
            # DIAGNOSTIC: Log document IDs being processed
            doc_ids = [doc.get_doc_id() for doc in documents]
            logger.info(f"[DEBUG] Processing document IDs: {doc_ids[:5]}{'...' if len(doc_ids) > 5 else ''}")

            # DIAGNOSTIC: Check existing ref_doc_info BEFORE any operations
            existing_ref_doc_info = self._index.docstore.get_all_ref_doc_info()
            existing_ids = set(existing_ref_doc_info.keys())
            logger.info(f"[DEBUG] BEFORE: Docstore has {len(existing_ids)} ref_doc_info entries")
            logger.info(f"[DEBUG] BEFORE: Existing IDs sample: {list(existing_ids)[:3]}{'...' if len(existing_ids) > 3 else ''}")

            # DIAGNOSTIC: Check for ID collision
            collision_ids = set(doc_ids) & existing_ids
            if collision_ids:
                logger.warning(f"[DEBUG] ID COLLISION DETECTED: {len(collision_ids)} documents have existing IDs: {list(collision_ids)[:5]}")
            else:
                logger.info(f"[DEBUG] No ID collisions - all {len(doc_ids)} document IDs are new")

            # Insert nodes into vector store
            logger.info(f"Inserting {len(nodes)} nodes into index")
            self._index.insert_nodes(nodes, show_progress=True)

            # CRITICAL FIX: Manually populate ref_doc_info since insert_nodes() skips docstore
            # when using text-storing vector stores like Qdrant (optimization to avoid duplication)
            # See: "VectorStoreIndex only stores nodes in document store if vector store does not store text"
            logger.info(f"Manually populating ref_doc_info for {len(documents)} documents")
            for document in documents:
                doc_id = document.get_doc_id()

                # Get node IDs for this document
                doc_node_ids = [node.node_id for node in nodes if node.ref_doc_id == doc_id]
                logger.debug(f"[REFINFO] Document {doc_id} has {len(doc_node_ids)} nodes")

                # Create RefDocInfo with node IDs and metadata
                ref_info = RefDocInfo(
                    node_ids=doc_node_ids,
                    metadata=document.metadata or {}
                )

                # Manually add to docstore's kvstore (no public API for this, must use private _kvstore)
                # IMPORTANT: Must convert RefDocInfo to dict because kvstore.put() calls .copy() on the value
                self._index.docstore._kvstore.put(
                    doc_id,
                    ref_info.to_dict(),  # Convert to dict to avoid AttributeError: 'RefDocInfo' object has no attribute 'copy'
                    collection=self._index.docstore._ref_doc_collection
                )
                logger.debug(f"[REFINFO] Added ref_doc_info for {doc_id} with {len(doc_node_ids)} node IDs")

            # DIAGNOSTIC: Check ref_doc_info AFTER manual population
            after_manual_ref_doc_info = self._index.docstore.get_all_ref_doc_info()
            after_manual_ids = set(after_manual_ref_doc_info.keys())
            logger.info(f"[DEBUG] AFTER manual ref_doc_info population: count = {len(after_manual_ids)}")

            # DIAGNOSTIC: Check if our IDs are now in ref_doc_info
            found_new_ids = set(doc_ids) & after_manual_ids
            logger.info(f"[DEBUG] Successfully added {len(found_new_ids)}/{len(doc_ids)} new document IDs to ref_doc_info")
            if len(found_new_ids) < len(doc_ids):
                missing_ids = set(doc_ids) - after_manual_ids
                logger.error(f"[DEBUG] MISSING IDs not in ref_doc_info: {list(missing_ids)[:5]}")

            logger.debug("[DEBUG] About to persist - checking ref_doc_info before persist")
            before_persist_count = len(self._index.docstore.get_all_ref_doc_info())
            logger.info(f"[DEBUG] BEFORE persist: ref_doc_info count = {before_persist_count}")

            # DIAGNOSTIC: Check internal _kvstore._data structure
            try:
                kvstore_data = self._index.docstore._kvstore._data
                logger.info(f"[KVSTORE_DEBUG] Available collections: {list(kvstore_data.keys())}")
                for collection_key in kvstore_data.keys():
                    collection_size = len(kvstore_data[collection_key])
                    logger.info(f"[KVSTORE_DEBUG] Collection '{collection_key}': {collection_size} items")
                    if collection_key == 'docstore/ref_doc_info':
                        ref_doc_items = kvstore_data[collection_key]
                        logger.info(f"[KVSTORE_DEBUG] ref_doc_info IDs: {list(ref_doc_items.keys())[:5]}{'...' if len(ref_doc_items) > 5 else ''}")
            except Exception as e:
                logger.warning(f"[KVSTORE_DEBUG] Could not inspect _kvstore._data: {e}")

            # CRITICAL: Use _save_index() which has the explicit docstore persistence fix
            self._save_index()

            # DIAGNOSTIC: Check ref_doc_info AFTER persist
            after_persist_ref_doc_info = self._index.docstore.get_all_ref_doc_info()
            logger.info(f"[DEBUG] AFTER persist: ref_doc_info count = {len(after_persist_ref_doc_info)}")
            logger.debug("Persisted the index and nodes")

            # DIAGNOSTIC: Final verification - read file back and check
            docstore_path = local_data_path / "docstore.json"
            if docstore_path.exists():
                import json
                try:
                    with open(docstore_path) as f:
                        data = json.load(f)
                        file_ref_count = len(data.get("docstore/ref_doc_info", {}))
                        logger.info(f"[DEBUG] FINAL VERIFICATION: docstore.json on disk has {file_ref_count} ref_doc_info entries")

                        if file_ref_count != len(after_persist_ref_doc_info):
                            logger.error(f"[DEBUG] ❌ MISMATCH: Memory has {len(after_persist_ref_doc_info)} but file has {file_ref_count}")
                        else:
                            logger.info(f"[DEBUG] ✅ Memory and disk counts MATCH: {file_ref_count}")
                except Exception as e:
                    logger.error(f"[DEBUG] Failed to verify persisted file: {e}")
            else:
                logger.error(f"[DEBUG] ❌ docstore.json does not exist after persist!")

        return documents


def get_ingestion_component(
    storage_context: StorageContext,
    embed_model: EmbedType,
    transformations: list[TransformComponent],
    settings: Settings,
) -> BaseIngestComponent:
    """Get the ingestion component for the given configuration.

    Note: Only SimpleIngestComponent is supported after simplification.
    Batch/Parallel/Pipeline modes removed as they were unused and complex.
    """
    ingest_mode = settings.embedding.ingest_mode
    if ingest_mode in ("batch", "parallel", "pipeline"):
        logger.warning(
            "Ingest mode '%s' no longer supported (removed in simplification). "
            "Using 'simple' mode instead.", ingest_mode
        )

    return SimpleIngestComponent(
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=transformations,
    )
