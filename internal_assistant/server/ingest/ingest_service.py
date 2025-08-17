import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, AnyStr, BinaryIO

from injector import inject, singleton
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.storage import StorageContext

from internal_assistant.components.embedding.embedding_component import EmbeddingComponent
from internal_assistant.components.ingest.ingest_component import get_ingestion_component
from internal_assistant.components.ingest.ingest_helper import IngestionHelper
from internal_assistant.components.llm.llm_component import LLMComponent
from internal_assistant.components.node_store.node_store_component import NodeStoreComponent
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

    def _should_replace_file(self, file_path: Path, file_name: str) -> tuple[bool, list[IngestedDoc]]:
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
            logger.warning(f"Could not compute hash for {file_name} - will replace to be safe")
            return True, existing_docs  # Couldn't compute hash, replace to be safe
        
        # Check if any existing doc has the same content hash
        for doc in existing_docs:
            stored_hash = doc.doc_metadata.get("content_hash") if doc.doc_metadata else None
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
            logger.info(f"Deleting {len(existing_docs)} existing documents for {file_name}")
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
        logger.info("Bulk ingesting file_names: %s", [f[0] for f in files])
        ingested_docs = []
        successful = 0
        failed = 0
        skipped = 0
        
        for i, (file_name, file_data) in enumerate(files, 1):
            try:
                logger.info(f"[{i}/{len(files)}] Started ingesting file={file_name}")
                documents = self.ingest_file(file_name, file_data)
                
                if documents:
                    ingested_docs.extend(documents)
                    successful += 1
                    logger.info(f"[{i}/{len(files)}] ✓ Completed ingesting file={file_name}")
                else:
                    skipped += 1
                    logger.info(f"[{i}/{len(files)}] ⏭ Skipped duplicate file={file_name}")
                    
            except Exception as e:
                failed += 1
                logger.error(f"[{i}/{len(files)}] ✗ Failed to ingest file={file_name}, path={file_data}, error: {e}", exc_info=True)
                
            # Progress report every 10 files
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(files)} processed. Success: {successful}, Skipped: {skipped}, Failed: {failed}")
                
        logger.info(f"Bulk ingestion complete! Total: {len(files)}, Success: {successful}, Skipped: {skipped}, Failed: {failed}")
        return ingested_docs

    def list_ingested(self) -> list[IngestedDoc]:
        ingested_docs: list[IngestedDoc] = []
        try:
            docstore = self.storage_context.docstore
            ref_docs: dict[str, RefDocInfo] | None = docstore.get_all_ref_doc_info()

            if not ref_docs:
                return ingested_docs

            for doc_id, ref_doc_info in ref_docs.items():
                doc_metadata = None
                if ref_doc_info is not None and ref_doc_info.metadata is not None:
                    doc_metadata = IngestedDoc.curate_metadata(ref_doc_info.metadata)
                ingested_docs.append(
                    IngestedDoc(
                        object="ingest.document",
                        doc_id=doc_id,
                        doc_metadata=doc_metadata,
                    )
                )
        except ValueError:
            logger.warning("Got an exception when getting list of docs", exc_info=True)
            pass
        logger.debug("Found count=%s ingested documents", len(ingested_docs))
        return ingested_docs

    def delete(self, doc_id: str) -> None:
        """Delete an ingested document.

        :raises ValueError: if the document does not exist
        """
        logger.info(
            "Deleting the ingested document=%s in the doc and index store", doc_id
        )
        self.ingest_component.delete(doc_id)

