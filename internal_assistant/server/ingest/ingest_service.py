import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, AnyStr, BinaryIO

from injector import inject, singleton
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.storage import StorageContext

from internal_assistant.components.embedding.embedding_component import (
    EmbeddingComponent,
)
from internal_assistant.components.ingest.ingest_component import (
    get_ingestion_component,
)
from internal_assistant.components.ingest.ingest_helper import IngestionHelper
from internal_assistant.components.llm.llm_component import LLMComponent
from internal_assistant.components.node_store.node_store_component import (
    NodeStoreComponent,
)
from internal_assistant.components.vector_store.vector_store_component import (
    VectorStoreComponent,
)
from internal_assistant.server.ingest.model import IngestedDoc
from internal_assistant.settings.settings import settings

if TYPE_CHECKING:
    from llama_index.core.storage.docstore.types import RefDocInfo

logger = logging.getLogger(__name__)


@singleton
class IngestService:
    @inject
    def __init__(
        self,
        llm_component: LLMComponent,
        vector_store_component: VectorStoreComponent,
        embedding_component: EmbeddingComponent,
        node_store_component: NodeStoreComponent,
    ) -> None:
        self.llm_service = llm_component
        self.vector_store_component = vector_store_component
        self.node_store_component = node_store_component
        self.embedding_component = embedding_component

        # Initialize storage context with health checks
        logger.info("🔧 [STORAGE_INIT] Initializing IngestService with storage verification...")
        self._initialize_storage_backends()

        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store_component.vector_store,
            docstore=node_store_component.doc_store,
            index_store=node_store_component.index_store,
        )
        node_parser = SentenceWindowNodeParser.from_defaults()

        self.ingest_component = get_ingestion_component(
            self.storage_context,
            embed_model=embedding_component.embedding_model,
            transformations=[node_parser, embedding_component.embedding_model],
            settings=settings(),
        )

        # Verify complete initialization
        self._verify_service_initialization()

    def _initialize_storage_backends(self) -> None:
        """Initialize and verify all storage backends are properly configured."""
        logger.info("🔧 [STORAGE_INIT] Starting storage backend initialization...")

        # Verify vector store
        try:
            self._verify_vector_store()
            logger.info("✅ [STORAGE_INIT] Vector store verification successful")
        except Exception as e:
            logger.error(f"❌ [STORAGE_INIT] Vector store verification failed: {e}")
            raise RuntimeError(f"Vector store initialization failed: {e}")

        # Verify document store
        try:
            self._verify_document_store()
            logger.info("✅ [STORAGE_INIT] Document store verification successful")
        except Exception as e:
            logger.error(f"❌ [STORAGE_INIT] Document store verification failed: {e}")
            raise RuntimeError(f"Document store initialization failed: {e}")

        # Verify local data directories
        try:
            self._verify_local_directories()
            logger.info("✅ [STORAGE_INIT] Local directories verification successful")
        except Exception as e:
            logger.error(f"❌ [STORAGE_INIT] Local directories verification failed: {e}")
            raise RuntimeError(f"Local directories initialization failed: {e}")

    def _verify_vector_store(self) -> None:
        """Verify vector store connectivity and configuration."""
        logger.info("🔧 [STORAGE_INIT] Verifying vector store...")

        vector_store = self.vector_store_component.vector_store

        # Check if vector store client is accessible
        if hasattr(vector_store, 'client'):
            client = vector_store.client
            logger.info(f"🔧 [STORAGE_INIT] Vector store client type: {type(client).__name__}")

            # For Qdrant, verify connection and collection
            if hasattr(client, 'get_collections'):
                try:
                    collections = client.get_collections()
                    logger.info(f"🔧 [STORAGE_INIT] Available collections: {[c.name for c in collections.collections]}")

                    # Check if our collection exists
                    collection_name = getattr(settings().qdrant, 'collection_name', 'internal_assistant_documents')
                    collection_exists = any(c.name == collection_name for c in collections.collections)

                    if collection_exists:
                        logger.info(f"✅ [STORAGE_INIT] Collection '{collection_name}' exists")

                        # Get collection info
                        collection_info = client.get_collection(collection_name)
                        logger.info(f"🔧 [STORAGE_INIT] Collection points count: {collection_info.points_count}")
                        logger.info(f"🔧 [STORAGE_INIT] Collection status: {collection_info.status}")
                    else:
                        logger.warning(f"⚠️ [STORAGE_INIT] Collection '{collection_name}' does not exist - attempting recovery")
                        self._recover_missing_collection(client, collection_name)

                except Exception as e:
                    logger.warning(f"⚠️ [STORAGE_INIT] Could not verify collections: {e}")
        else:
            logger.warning("⚠️ [STORAGE_INIT] Vector store has no accessible client")

    def _verify_document_store(self) -> None:
        """Verify document store accessibility."""
        logger.info("🔧 [STORAGE_INIT] Verifying document store...")

        doc_store = self.node_store_component.doc_store
        logger.info(f"🔧 [STORAGE_INIT] Document store type: {type(doc_store).__name__}")

        # For simple docstore, verify it's accessible
        try:
            # Test basic operation
            if hasattr(doc_store, 'get_all_ref_doc_info'):
                ref_docs = doc_store.get_all_ref_doc_info()
                doc_count = len(ref_docs) if ref_docs else 0
                logger.info(f"🔧 [STORAGE_INIT] Document store contains {doc_count} documents")
            else:
                logger.warning("⚠️ [STORAGE_INIT] Document store missing expected methods")
        except Exception as e:
            logger.error(f"❌ [STORAGE_INIT] Document store verification failed: {e}")
            raise

    def _verify_local_directories(self) -> None:
        """Verify and create necessary local data directories."""
        logger.info("🔧 [STORAGE_INIT] Verifying local data directories...")

        from internal_assistant.paths import local_data_path

        # Main local data directory
        local_data_dir = Path(str(local_data_path))
        self._ensure_directory_exists(local_data_dir, "local_data")

        # Qdrant directory
        qdrant_path = local_data_dir / "qdrant"
        self._ensure_directory_exists(qdrant_path, "qdrant")

        # Check for settings-specific paths
        try:
            app_settings = settings()
            if hasattr(app_settings, 'qdrant') and app_settings.qdrant:
                if hasattr(app_settings.qdrant, 'path'):
                    qdrant_settings_path = Path(app_settings.qdrant.path)
                    self._ensure_directory_exists(qdrant_settings_path, "qdrant_settings")
        except Exception as e:
            logger.warning(f"⚠️ [STORAGE_INIT] Could not verify settings-specific paths: {e}")

    def _ensure_directory_exists(self, directory: Path, name: str) -> None:
        """Ensure a directory exists and is writable."""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ [STORAGE_INIT] Directory '{name}' verified: {directory}")

            # Test write permissions
            test_file = directory / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                logger.info(f"✅ [STORAGE_INIT] Write permissions verified for '{name}'")
            except Exception as e:
                logger.error(f"❌ [STORAGE_INIT] No write permissions for '{name}': {e}")
                raise PermissionError(f"Cannot write to {directory}")

        except Exception as e:
            logger.error(f"❌ [STORAGE_INIT] Failed to create/verify directory '{name}': {e}")
            raise

    def _recover_missing_collection(self, client, collection_name: str) -> None:
        """Attempt to recover a missing Qdrant collection."""
        logger.info(f"🚑 [COLLECTION_RECOVERY] Starting recovery for collection: {collection_name}")

        try:
            # Get embedding dimension from the embedding settings, not vector store
            from internal_assistant.settings.settings import settings
            embedding_settings = settings().embedding
            embedding_dim = getattr(embedding_settings, 'embed_dim', 768)  # Default to 768 for nomic-embed-text

            logger.info(f"🚑 [COLLECTION_RECOVERY] Creating collection with dimension: {embedding_dim}")

            # Create collection with proper configuration
            from qdrant_client.models import Distance, VectorParams

            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE,  # Standard for text embeddings
                ),
            )

            logger.info(f"✅ [COLLECTION_RECOVERY] Successfully created collection: {collection_name}")

            # Verify creation
            collection_info = client.get_collection(collection_name)
            logger.info(f"✅ [COLLECTION_RECOVERY] Collection verified - Status: {collection_info.status}")

        except Exception as e:
            logger.error(f"❌ [COLLECTION_RECOVERY] Failed to recover collection {collection_name}: {e}")
            logger.warning(f"⚠️ [COLLECTION_RECOVERY] Collection will be created automatically on first document ingestion")

    def _verify_service_initialization(self) -> None:
        """Verify complete service initialization."""
        logger.info("🔧 [STORAGE_INIT] Verifying complete service initialization...")

        # Verify storage context
        if not self.storage_context:
            raise RuntimeError("Storage context not initialized")

        # Verify ingest component
        if not self.ingest_component:
            raise RuntimeError("Ingest component not initialized")

        # Perform storage consistency check
        self._perform_startup_consistency_check()

        logger.info("✅ [STORAGE_INIT] IngestService initialization completed successfully")
        logger.info("🚀 [STORAGE_INIT] Service ready for document operations")

    def _perform_startup_consistency_check(self) -> None:
        """Perform storage consistency check during startup."""
        logger.info("🔍 [STARTUP_CHECK] Performing storage consistency check...")

        try:
            from internal_assistant.server.ingest.storage_consistency_service import StorageConsistencyService

            consistency_service = StorageConsistencyService(self.storage_context)
            report = consistency_service.check_consistency()

            if not report.inconsistencies:
                logger.info("✅ [STARTUP_CHECK] Storage is consistent - no issues found")
                return

            logger.warning(f"⚠️ [STARTUP_CHECK] Found {len(report.inconsistencies)} storage inconsistencies")

            # Log summary
            summary = consistency_service.generate_report_summary(report)
            for line in summary.split('\n'):
                logger.info(f"📊 [STARTUP_CHECK] {line}")

            # Auto-repair non-critical issues
            if report.high_priority_issues:
                logger.info("🔧 [STARTUP_CHECK] Auto-repairing high priority issues...")
                repair_stats = consistency_service.repair_inconsistencies(report, auto_repair=True)
                logger.info(f"🔧 [STARTUP_CHECK] Repair completed: {repair_stats}")

                # Re-check after repair
                post_repair_report = consistency_service.check_consistency()
                if len(post_repair_report.inconsistencies) < len(report.inconsistencies):
                    logger.info(f"✅ [STARTUP_CHECK] Repair successful - {len(report.inconsistencies) - len(post_repair_report.inconsistencies)} issues resolved")

            if report.critical_issues:
                logger.critical(f"🚨 [STARTUP_CHECK] {len(report.critical_issues)} critical issues require manual attention")
                for issue in report.critical_issues:
                    logger.critical(f"🚨 [STARTUP_CHECK] CRITICAL: {issue.description}")

        except Exception as e:
            logger.warning(f"⚠️ [STARTUP_CHECK] Consistency check failed: {e}")
            logger.warning("⚠️ [STARTUP_CHECK] Continuing with startup...")

    def _should_replace_file(
        self, file_path: Path, file_name: str
    ) -> tuple[bool, list[IngestedDoc]]:
        """Determine if file should be replaced based on content comparison."""
        existing_docs = []

        # Find existing documents with same name
        for ingested_document in self.list_ingested():
            if (
                ingested_document.doc_metadata
                and ingested_document.doc_metadata.get("file_name") == file_name
            ):
                existing_docs.append(ingested_document)

        if not existing_docs:
            return True, []  # No existing docs, should ingest

        # Get content hash of current file
        current_hash = IngestionHelper._get_file_hash(file_path)
        if not current_hash:
            logger.warning(
                f"Could not compute hash for {file_name} - will replace to be safe"
            )
            return True, existing_docs  # Couldn't compute hash, replace to be safe

        # Check if any existing doc has the same content hash
        for doc in existing_docs:
            stored_hash = (
                doc.doc_metadata.get("content_hash") if doc.doc_metadata else None
            )
            if stored_hash == current_hash:
                logger.info(f"File {file_name} content unchanged - skipping duplicate")
                return False, existing_docs  # Same content, don't replace

        logger.info(f"File {file_name} content changed - replacing")
        return True, existing_docs  # Different content, replace

    def _ingest_data(self, file_name: str, file_data: AnyStr) -> list[IngestedDoc]:
        logger.debug("Got file data of size=%s to ingest", len(file_data))
        # llama-index mainly supports reading from files, so
        # we have to create a tmp file to read for it to work
        # delete=False to avoid a Windows 11 permission error.
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                path_to_tmp = Path(tmp.name)
                if isinstance(file_data, bytes):
                    path_to_tmp.write_bytes(file_data)
                else:
                    path_to_tmp.write_text(str(file_data))
                return self.ingest_file(file_name, path_to_tmp)
            finally:
                tmp.close()
                path_to_tmp.unlink()

    def ingest_file(self, file_name: str, file_data: Path) -> list[IngestedDoc]:
        logger.info("Ingesting file_name=%s", file_name)

        # Check for duplicates before ingesting
        should_replace, existing_docs = self._should_replace_file(file_data, file_name)

        if not should_replace:
            logger.info(f"Skipping duplicate file: {file_name}")
            return []  # Return empty list for skipped files

        # Delete existing documents if replacing
        if existing_docs:
            logger.info(
                f"Deleting {len(existing_docs)} existing documents for {file_name}"
            )
            for doc in existing_docs:
                self.delete(doc.doc_id)

        try:
            documents = self.ingest_component.ingest(file_name, file_data)
            logger.info(f"Finished ingestion file_name={file_name}")
            return [IngestedDoc.from_document(document) for document in documents]
        except Exception as e:
            logger.error(f"Failed to ingest {file_name} due to {e}", exc_info=True)
            return []

    def ingest_text(self, file_name: str, text: str) -> list[IngestedDoc]:
        logger.debug("Ingesting text data with file_name=%s", file_name)
        return self._ingest_data(file_name, text)

    def ingest_bin_data(
        self, file_name: str, raw_file_data: BinaryIO
    ) -> list[IngestedDoc]:
        logger.debug("Ingesting binary data with file_name=%s", file_name)
        file_data = raw_file_data.read()
        return self._ingest_data(file_name, file_data)

    def bulk_ingest(self, files: list[tuple[str, Path]]) -> list[IngestedDoc]:
        logger.info("📥 [BULK_INGEST] Starting bulk ingestion of %d files", len(files))
        logger.info("📥 [BULK_INGEST] File names: %s", [f[0] for f in files])

        # Get document count before bulk ingestion
        try:
            docs_before = self.list_ingested()
            logger.info("📥 [BULK_INGEST] Documents in index before bulk ingestion: %d", len(docs_before))
        except Exception as e:
            logger.warning("📥 [BULK_INGEST] Error checking docs before bulk ingestion: %s", e)
            docs_before = []

        ingested_docs = []
        successful = 0
        failed = 0
        skipped = 0

        for i, (file_name, file_data) in enumerate(files, 1):
            try:
                logger.info("📥 [BULK_INGEST] [%d/%d] Started ingesting file=%s (path: %s)",
                           i, len(files), file_name, file_data)

                # Check file exists and get size
                if file_data.exists():
                    file_size = file_data.stat().st_size
                    logger.info("📥 [BULK_INGEST] [%d/%d] File size: %d bytes", i, len(files), file_size)
                else:
                    logger.error("📥 [BULK_INGEST] [%d/%d] File does not exist: %s", i, len(files), file_data)

                documents = self.ingest_file(file_name, file_data)

                if documents:
                    ingested_docs.extend(documents)
                    successful += 1
                    logger.info("📥 [BULK_INGEST] [%d/%d] ✅ Completed ingesting file=%s (%d documents created)",
                               i, len(files), file_name, len(documents))

                    # Log document IDs for tracking
                    doc_ids = [doc.doc_id for doc in documents]
                    logger.info("📥 [BULK_INGEST] [%d/%d] Document IDs: %s", i, len(files), doc_ids)
                else:
                    skipped += 1
                    logger.info("📥 [BULK_INGEST] [%d/%d] ⏭️ Skipped duplicate file=%s", i, len(files), file_name)

            except Exception as e:
                failed += 1
                logger.error("📥 [BULK_INGEST] [%d/%d] ❌ Failed to ingest file=%s, path=%s, error: %s",
                           i, len(files), file_name, file_data, e, exc_info=True)

            # Progress report every 5 files (more frequent for debugging)
            if i % 5 == 0:
                logger.info("📥 [BULK_INGEST] Progress: %d/%d processed. Success: %d, Skipped: %d, Failed: %d",
                           i, len(files), successful, skipped, failed)

        logger.info("📥 [BULK_INGEST] Bulk ingestion processing complete! Total: %d, Success: %d, Skipped: %d, Failed: %d",
                   len(files), successful, skipped, failed)

        # Verify persistence after bulk ingestion
        try:
            logger.info("📥 [BULK_INGEST] Verifying persistence after bulk ingestion...")
            docs_after = self.list_ingested()
            logger.info("📥 [BULK_INGEST] Documents in index after bulk ingestion: %d", len(docs_after))

            new_docs_count = len(docs_after) - len(docs_before)
            expected_new_docs = len(ingested_docs)

            logger.info("📥 [BULK_INGEST] Expected new documents: %d", expected_new_docs)
            logger.info("📥 [BULK_INGEST] Actual new documents: %d", new_docs_count)

            if new_docs_count != expected_new_docs:
                logger.error("❌ [BULK_INGEST] PERSISTENCE MISMATCH: Expected %d new docs, found %d",
                           expected_new_docs, new_docs_count)
            else:
                logger.info("✅ [BULK_INGEST] Persistence verification successful: %d new documents confirmed",
                           new_docs_count)

        except Exception as e:
            logger.error("❌ [BULK_INGEST] Error verifying persistence: %s", e, exc_info=True)

        # Force index persistence after bulk operations
        try:
            logger.info("📥 [BULK_INGEST] Forcing index persistence...")
            self.ingest_component._save_index()
            logger.info("✅ [BULK_INGEST] Index persistence completed")
        except Exception as e:
            logger.error("❌ [BULK_INGEST] Error forcing index persistence: %s", e, exc_info=True)

        logger.info("📥 [BULK_INGEST] Bulk ingestion fully complete")
        return ingested_docs

    def list_ingested(self) -> list[IngestedDoc]:
        """List all ingested documents from persistent storage.

        This method reads directly from the docstore to ensure it gets
        the most up-to-date data, including documents added since server startup.
        """
        logger.info("🔍 [LIST_INGESTED] ===== STARTING LIST_INGESTED =====")
        ingested_docs: list[IngestedDoc] = []
        try:
            # CRITICAL FIX: Force docstore to reload from disk
            # SimpleDocumentStore caches ref_doc_info in memory, so we need to force reload
            docstore = self.storage_context.docstore

            # Force reload from disk if the docstore supports it
            if hasattr(docstore, 'from_persist_dir'):
                from internal_assistant.paths import local_data_path
                logger.info("📖 [LIST_INGESTED] Force-reloading docstore from disk to get fresh data")
                try:
                    # Reload the docstore from disk to get latest data
                    fresh_docstore = type(docstore).from_persist_dir(str(local_data_path))
                    docstore = fresh_docstore
                    # Update storage context with fresh docstore
                    self.storage_context.docstore = fresh_docstore
                    logger.info("✅ [LIST_INGESTED] Docstore successfully reloaded from disk")
                except Exception as e:
                    logger.warning(f"⚠️ [LIST_INGESTED] Could not reload docstore from disk: {e}")
                    # Fall back to existing docstore

            # CRITICAL FIX: Try multiple methods to get documents
            logger.info("📖 [LIST_INGESTED] Reading documents from persistent docstore")
            
            # Method 1: Try get_all_ref_doc_info (preferred method)
            ref_docs: dict[str, RefDocInfo] | None = None
            if hasattr(docstore, 'get_all_ref_doc_info'):
                ref_docs = docstore.get_all_ref_doc_info()
                logger.info(f"📖 [LIST_INGESTED] get_all_ref_doc_info() returned: {len(ref_docs) if ref_docs else 0} entries")
            
            if ref_docs and len(ref_docs) > 0:
                logger.debug(f"📖 [LIST_INGESTED] Found {len(ref_docs)} documents via ref_doc_info")
                for doc_id, ref_doc_info in ref_docs.items():
                    doc_metadata = None
                    if ref_doc_info is not None and ref_doc_info.metadata is not None:
                        doc_metadata = IngestedDoc.curate_metadata(ref_doc_info.metadata)
                        logger.debug(f"📖 [LIST_INGESTED] Processing doc {doc_id}: {doc_metadata.get('file_name', 'Unknown')}")
                    ingested_docs.append(
                        IngestedDoc(
                            object="ingest.document",
                            doc_id=doc_id,
                            doc_metadata=doc_metadata,
                        )
                    )
            else:
                # Method 2: Fallback - get documents from docstore/data
                logger.warning("⚠️ [LIST_INGESTED] ref_doc_info empty, trying alternative method via get_all_document_hashes")
                
                if hasattr(docstore, 'get_all_document_hashes'):
                    doc_hashes = docstore.get_all_document_hashes()
                    logger.debug(f"📖 [LIST_INGESTED] Found {len(doc_hashes)} documents via document hashes")
                    
                    for doc_id in doc_hashes.keys():
                        # Try to get the document from docstore
                        try:
                            doc = docstore.get_document(doc_id, raise_error=False)
                            if doc:
                                doc_metadata = IngestedDoc.curate_metadata(doc.metadata) if hasattr(doc, 'metadata') and doc.metadata else None
                                ingested_docs.append(
                                    IngestedDoc(
                                        object="ingest.document",
                                        doc_id=doc_id,
                                        doc_metadata=doc_metadata,
                                    )
                                )
                                logger.debug(f"📖 [LIST_INGESTED] Retrieved doc via docstore/data: {doc_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ [LIST_INGESTED] Could not retrieve document {doc_id}: {e}")
                            continue
                else:
                    logger.error("❌ [LIST_INGESTED] No methods available to list documents from docstore")
                    return ingested_docs
        except ValueError as e:
            logger.warning(f"Got an exception when getting list of docs: {e}", exc_info=True)
            pass

        logger.info(f"📖 [LIST_INGESTED] Returning {len(ingested_docs)} ingested documents")
        return ingested_docs

    def delete(self, doc_id: str) -> None:
        """Delete an ingested document.

        :raises ValueError: if the document does not exist
        """
        logger.info(
            "🗑️ [INGEST_SERVICE] Deleting the ingested document=%s in the doc and index store", doc_id
        )

        # Verify document exists before deletion
        try:
            existing_docs = self.list_ingested()
            doc_exists = any(doc.doc_id == doc_id for doc in existing_docs)
            logger.info(f"🗑️ [INGEST_SERVICE] Document {doc_id} exists before deletion: {doc_exists}")

            if doc_exists:
                # Find the document to log its metadata
                target_doc = next((doc for doc in existing_docs if doc.doc_id == doc_id), None)
                if target_doc and target_doc.doc_metadata:
                    file_name = target_doc.doc_metadata.get("file_name", "Unknown")
                    logger.info(f"🗑️ [INGEST_SERVICE] Deleting document: {file_name} (ID: {doc_id})")
        except Exception as e:
            logger.warning(f"🗑️ [INGEST_SERVICE] Error checking document existence: {e}")

        # Perform the deletion
        self.ingest_component.delete(doc_id)
        logger.info(f"🗑️ [INGEST_SERVICE] Deletion command sent to ingest_component for doc_id: {doc_id}")

        # Verify deletion was successful
        try:
            remaining_docs = self.list_ingested()
            doc_still_exists = any(doc.doc_id == doc_id for doc in remaining_docs)
            if doc_still_exists:
                logger.error(f"❌ [INGEST_SERVICE] DELETION FAILED: Document {doc_id} still exists after deletion!")
            else:
                logger.info(f"✅ [INGEST_SERVICE] Deletion verified: Document {doc_id} successfully removed")
        except Exception as e:
            logger.warning(f"🗑️ [INGEST_SERVICE] Error verifying deletion: {e}")

    def delete_all(self) -> int:
        """Delete all ingested documents.

        Returns:
            Number of documents deleted
        """
        logger.warning("🗑️ [INGEST_SERVICE] DELETE ALL requested - this is a destructive operation")

        try:
            # Get list of all documents
            documents = self.list_ingested()
            doc_count = len(documents)

            if doc_count == 0:
                logger.info("🗑️ [INGEST_SERVICE] No documents to delete")
                return 0

            logger.warning(f"🗑️ [INGEST_SERVICE] Deleting {doc_count} documents")

            # Delete each document
            deleted_count = 0
            failed_count = 0

            for doc in documents:
                try:
                    logger.info(f"🗑️ [INGEST_SERVICE] Deleting document {deleted_count + 1}/{doc_count}: {doc.doc_id}")
                    self.delete(doc.doc_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"❌ [INGEST_SERVICE] Failed to delete document {doc.doc_id}: {e}")
                    failed_count += 1

            # Verify all documents were deleted
            remaining_docs = self.list_ingested()
            if len(remaining_docs) > 0:
                logger.error(f"❌ [INGEST_SERVICE] DELETE ALL incomplete: {len(remaining_docs)} documents remain")
            else:
                logger.info(f"✅ [INGEST_SERVICE] DELETE ALL completed: {deleted_count} documents deleted")

            if failed_count > 0:
                logger.warning(f"⚠️ [INGEST_SERVICE] DELETE ALL had {failed_count} failures")

            return deleted_count

        except Exception as e:
            logger.error(f"❌ [INGEST_SERVICE] DELETE ALL failed: {e}", exc_info=True)
            raise
