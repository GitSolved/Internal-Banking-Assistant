"""Document Service Facade

Provides clean abstraction for document management services with
batch processing, progress tracking, and intelligent caching.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from internal_assistant.server.chunks.chunks_service import Chunk, ChunksService
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.ingest.model import IngestedDoc

from .service_facade import ServiceFacade

logger = logging.getLogger(__name__)


class DocumentServiceFacade(ServiceFacade[IngestService]):
    """Facade for document management services with enhanced batch processing,
    intelligent caching, and comprehensive progress tracking.
    """

    def __init__(
        self,
        ingest_service: IngestService,
        chunks_service: ChunksService | None = None,
    ):
        super().__init__(ingest_service, "document_service")
        self.chunks_service = chunks_service
        self._processing_queue: dict[str, dict] = {}
        self._document_cache: dict[str, list[IngestedDoc]] = {}
        self._last_document_refresh = 0
        self._batch_processor = ThreadPoolExecutor(
            max_workers=3, thread_name_prefix="doc-batch"
        )

    @ServiceFacade.with_cache(ttl=30, key_func=lambda self: "ingested_files")
    def list_ingested_files(self, force_refresh: bool = False) -> list[list[str]]:
        """Get list of ingested files with intelligent caching.

        Args:
            force_refresh: If True, bypass cache and force fresh data fetch

        Returns:
            List of file names in Gradio List format
        """
        # Force cache clear if requested
        if force_refresh:
            self.clear_cache()
        try:
            logger.debug("Fetching ingested files list")

            files = set()
            total_documents = 0
            skipped_documents = 0

            ingested_documents = self.service.list_ingested()
            total_documents = len(ingested_documents)

            for ingested_document in ingested_documents:
                if ingested_document.doc_metadata is None:
                    skipped_documents += 1
                    logger.warning(
                        f"Skipping document {ingested_document.doc_id} - no metadata"
                    )
                    continue

                file_name = ingested_document.doc_metadata.get(
                    "file_name", "[FILE NAME MISSING]"
                )

                if file_name == "[FILE NAME MISSING]":
                    logger.warning(
                        f"Document {ingested_document.doc_id} has missing file name"
                    )
                    skipped_documents += 1
                    continue

                files.add(file_name)

            unique_files = len(files)
            logger.info(
                f"Document listing: {unique_files} unique files from {total_documents} total documents (skipped: {skipped_documents})"
            )

            file_list = [[file_name] for file_name in sorted(files)]
            return file_list

        except Exception as e:
            logger.error(f"Error listing ingested files: {e}")
            return [["[ERROR: Could not load files]"]]

    @ServiceFacade.with_retry(max_retries=3, base_delay=1.0)
    def bulk_ingest(self, files_to_ingest: list[tuple[str, Path]]) -> dict[str, Any]:
        """Perform bulk ingestion with progress tracking and error recovery.

        Args:
            files_to_ingest: List of (filename, path) tuples

        Returns:
            Dictionary with ingestion results and statistics
        """
        if not files_to_ingest:
            return {"success": True, "processed": 0, "errors": []}

        batch_id = f"batch_{len(self._processing_queue)}"
        logger.info(
            f"Starting bulk ingestion batch {batch_id} with {len(files_to_ingest)} files"
        )

        # Initialize progress tracking
        self._processing_queue[batch_id] = {
            "total_files": len(files_to_ingest),
            "processed_files": 0,
            "failed_files": 0,
            "start_time": time.time(),
            "errors": [],
            "status": "processing",
        }

        try:
            # Use underlying service bulk ingestion
            self.service.bulk_ingest(files_to_ingest)

            # Update progress
            self._processing_queue[batch_id].update(
                {
                    "processed_files": len(files_to_ingest),
                    "status": "completed",
                    "end_time": time.time(),
                }
            )

            # Clear document cache to force refresh
            self.clear_cache()

            logger.info(f"Bulk ingestion batch {batch_id} completed successfully")

            return {
                "success": True,
                "batch_id": batch_id,
                "processed": len(files_to_ingest),
                "errors": [],
            }

        except Exception as e:
            logger.error(f"Bulk ingestion batch {batch_id} failed: {e}")

            self._processing_queue[batch_id].update(
                {"status": "failed", "error": str(e), "end_time": time.time()}
            )

            return {
                "success": False,
                "batch_id": batch_id,
                "processed": 0,
                "errors": [str(e)],
            }

    @ServiceFacade.with_retry(max_retries=2, base_delay=1.0)
    def ingest_folder(self, folder_path: Path, **kwargs) -> tuple[list, str]:
        """Ingest entire folder with progress tracking.

        Args:
            folder_path: Path to folder to ingest
            **kwargs: Additional arguments for folder ingestion

        Returns:
            Tuple of (updated file list, status message)
        """
        try:
            if not folder_path.exists():
                return self.list_ingested_files(), "❌ Folder not found"

            logger.info(f"Starting folder ingestion for: {folder_path}")

            # Import the LocalIngestWorker
            import sys
            from pathlib import Path as PathLib

            tools_path = (
                PathLib(__file__).parent.parent.parent.parent / "tools" / "data"
            )
            sys.path.append(str(tools_path))

            try:
                from ingest_folder import LocalIngestWorker

                from internal_assistant.settings.settings import settings
            except ImportError as e:
                logger.error(f"Failed to import LocalIngestWorker: {e}")
                return (
                    self.list_ingested_files(),
                    f"❌ Folder ingestion not available: {e!s}",
                )

            # Initialize worker with UI-friendly settings
            worker = LocalIngestWorker(
                self.service,
                settings(),
                max_attempts=2,
                checkpoint_file="ui_folder_ingestion_checkpoint.json",
            )

            # Start ingestion
            worker.ingest_folder(folder_path, ignored=[], resume=True)

            # Clear cache to refresh file list
            self.clear_cache()

            logger.info(f"Folder ingestion completed successfully: {folder_path}")
            return self.list_ingested_files(), "✅ Folder ingested successfully!"

        except Exception as e:
            logger.error(f"Folder ingestion failed: {e}", exc_info=True)
            return self.list_ingested_files(), f"❌ Ingestion failed: {e!s}"

    @ServiceFacade.with_retry(max_retries=2, base_delay=0.5)
    def delete_document(self, doc_id: str) -> None:
        """Delete a single document and clear the cache.

        Args:
            doc_id: Document ID to delete

        Raises:
            Exception if deletion fails
        """
        try:
            logger.info(f"🗑️ [FACADE] Deleting document: {doc_id}")

            # Delete the document
            self.service.delete(doc_id)

            # Force clear cache immediately
            self.clear_cache()
            logger.info(f"✅ [FACADE] Document {doc_id} deleted and cache cleared")

            # Verify deletion
            import time

            time.sleep(0.3)  # Brief delay for persistence

            remaining_docs = self.service.list_ingested()
            if any(doc.doc_id == doc_id for doc in remaining_docs):
                logger.error(
                    f"❌ [FACADE] Document {doc_id} still exists after deletion!"
                )
                raise RuntimeError(
                    f"Document deletion verification failed for {doc_id}"
                )

            logger.info(f"✅ [FACADE] Deletion verified for {doc_id}")

        except Exception as e:
            logger.error(
                f"❌ [FACADE] Failed to delete document {doc_id}: {e}", exc_info=True
            )
            self.clear_cache()  # Clear cache even on failure
            raise

    @ServiceFacade.with_retry(max_retries=2, base_delay=0.5)
    def delete_all_documents(self) -> tuple[list, str]:
        """Delete all ingested documents with confirmation.

        Returns:
            Tuple of (updated file list, status message)
        """
        try:
            logger.warning("🗑️ [DELETE_ALL] Starting delete all documents operation")

            # Get list of documents to delete
            documents = self.service.list_ingested()
            document_count = len(documents)

            if document_count == 0:
                logger.info("🗑️ [DELETE_ALL] No documents to delete")
                return [], "✅ No documents to delete"

            logger.info(f"🗑️ [DELETE_ALL] Deleting {document_count} documents")

            # Delete all documents
            self.service.delete_all()

            # Force clear all caches immediately
            self.clear_cache()
            logger.info("🗑️ [DELETE_ALL] Cache cleared after delete")

            # Force a fresh fetch to verify deletion
            import time

            time.sleep(0.5)  # Brief delay to ensure persistence

            remaining_docs = self.service.list_ingested()
            if len(remaining_docs) > 0:
                logger.error(
                    f"❌ [DELETE_ALL] Deletion incomplete: {len(remaining_docs)} documents remain"
                )
                return (
                    self.list_ingested_files(force_refresh=True),
                    f"⚠️ Partial delete: {len(remaining_docs)} documents remain",
                )

            logger.info(
                f"✅ [DELETE_ALL] Successfully deleted {document_count} documents"
            )
            return [], f"✅ Successfully deleted {document_count} documents"

        except Exception as e:
            logger.error(
                f"❌ [DELETE_ALL] Failed to delete documents: {e}", exc_info=True
            )
            self.clear_cache()  # Clear cache even on failure
            return (
                self.list_ingested_files(force_refresh=True),
                f"❌ Delete failed: {e!s}",
            )

    @ServiceFacade.with_cache(
        ttl=180, key_func=lambda self, query="": f"search_chunks:{query}"
    )
    def search_chunks(self, query: str, limit: int = 10) -> list[Chunk]:
        """Search document chunks with caching.

        Args:
            query: Search query
            limit: Maximum number of chunks to return

        Returns:
            List of matching chunks
        """
        if not self.chunks_service:
            logger.warning("Chunks service not available")
            return []

        try:
            logger.debug(f"Searching chunks for query: {query}")
            chunks = self.chunks_service.retrieve_relevant(text=query, limit=limit)

            logger.info(f"Found {len(chunks)} relevant chunks for query")
            return chunks

        except Exception as e:
            logger.error(f"Chunk search failed: {e}")
            return []

    def get_processing_status(self, batch_id: str | None = None) -> dict[str, Any]:
        """Get processing status for batch operations.

        Args:
            batch_id: Specific batch ID, or None for all batches

        Returns:
            Processing status information
        """
        if batch_id:
            return self._processing_queue.get(batch_id, {"status": "not_found"})

        return {
            "active_batches": len(
                [
                    b
                    for b in self._processing_queue.values()
                    if b["status"] == "processing"
                ]
            ),
            "total_batches": len(self._processing_queue),
            "batches": self._processing_queue.copy(),
        }

    def cleanup_completed_batches(self, max_age_seconds: int = 3600) -> int:
        """Clean up old completed batch records.

        Args:
            max_age_seconds: Maximum age for keeping completed batches

        Returns:
            Number of batches cleaned up
        """
        current_time = time.time()
        cleaned_count = 0

        batch_ids_to_remove = []
        for batch_id, batch_info in self._processing_queue.items():
            if batch_info.get("status") in ["completed", "failed"]:
                end_time = batch_info.get("end_time", current_time)
                if current_time - end_time > max_age_seconds:
                    batch_ids_to_remove.append(batch_id)

        for batch_id in batch_ids_to_remove:
            del self._processing_queue[batch_id]
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old batch records")

        return cleaned_count

    def _basic_health_check(self) -> bool:
        """Basic health check for document service with timeout."""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        # Check circuit breaker first
        if self._is_circuit_breaker_open():
            logger.debug(
                f"Health check skipped - circuit breaker open for {self.service_name}"
            )
            return False

        try:
            # Use executor with timeout to prevent file I/O blocking
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="doc-health-check"
            ) as executor:
                future = executor.submit(self._perform_document_check)
                result = future.result(timeout=5)  # 5-second timeout
                return result

        except (TimeoutError, Exception) as e:
            logger.warning(f"Document service health check failed (timeout/error): {e}")
            if isinstance(e, TimeoutError):
                self._trigger_circuit_breaker()
            return False

    def _perform_document_check(self) -> bool:
        """Perform document service availability check."""
        try:
            # Lightweight check - just verify service is responsive
            documents = self.service.list_ingested()
            # Verify we got a valid response (list or dict)
            return isinstance(documents, (list, dict))
        except Exception:
            return False

    def get_service_info(self) -> dict[str, Any]:
        """Get comprehensive service information."""
        base_metrics = self.get_metrics()

        return {
            **base_metrics,
            "service_type": "document",
            "processing_batches": len(
                [
                    b
                    for b in self._processing_queue.values()
                    if b["status"] == "processing"
                ]
            ),
            "total_documents": (
                len(self.service.list_ingested()) if self._basic_health_check() else 0
            ),
            "health": self._health.value,
            "capabilities": {
                "bulk_ingestion": True,
                "folder_processing": True,
                "progress_tracking": True,
                "chunk_search": self.chunks_service is not None,
                "caching": True,
            },
        }

    def __del__(self):
        """Cleanup batch processor."""
        if hasattr(self, "_batch_processor"):
            self._batch_processor.shutdown(wait=False)
        super().__del__()
