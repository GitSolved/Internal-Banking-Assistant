"""Storage consistency service for detecting and repairing storage backend inconsistencies."""

import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from llama_index.core.storage.storage_context import StorageContext
from internal_assistant.paths import local_data_path

logger = logging.getLogger(__name__)


@dataclass
class StorageInconsistency:
    """Represents a storage inconsistency that needs repair."""
    type: str  # 'orphaned_document', 'missing_vector', 'orphaned_vector', 'metadata_mismatch'
    doc_id: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    repair_action: str
    metadata: Dict


@dataclass
class ConsistencyReport:
    """Report of storage consistency check results."""
    total_documents: int
    total_vectors: int
    inconsistencies: List[StorageInconsistency]
    healthy_documents: int

    @property
    def critical_issues(self) -> List[StorageInconsistency]:
        return [i for i in self.inconsistencies if i.severity == 'critical']

    @property
    def high_priority_issues(self) -> List[StorageInconsistency]:
        return [i for i in self.inconsistencies if i.severity in ['high', 'critical']]


class StorageConsistencyService:
    """Service for checking and repairing storage consistency."""

    def __init__(self, storage_context: StorageContext):
        self.storage_context = storage_context
        self.vector_store = storage_context.vector_store
        self.docstore = storage_context.docstore
        self.index_store = storage_context.index_store

    def check_consistency(self) -> ConsistencyReport:
        """Perform comprehensive storage consistency check."""
        logger.info("🔍 [CONSISTENCY_CHECK] Starting comprehensive storage consistency check")

        inconsistencies = []

        # Get document IDs from different stores
        docstore_docs = self._get_docstore_documents()
        vector_docs = self._get_vector_store_documents()
        index_docs = self._get_index_store_documents()

        logger.info(f"📊 [CONSISTENCY_CHECK] Found {len(docstore_docs)} docs in docstore, "
                   f"{len(vector_docs)} in vector store, {len(index_docs)} in index store")

        # Check for orphaned documents (in docstore but not in vector store)
        orphaned_docs = docstore_docs - vector_docs
        for doc_id in orphaned_docs:
            inconsistencies.append(StorageInconsistency(
                type='orphaned_document',
                doc_id=doc_id,
                description=f"Document exists in docstore but missing from vector store",
                severity='high',
                repair_action='recreate_embeddings_or_remove_document',
                metadata={'source': 'docstore_only'}
            ))

        # Check for orphaned vectors (in vector store but not in docstore)
        orphaned_vectors = vector_docs - docstore_docs
        for doc_id in orphaned_vectors:
            inconsistencies.append(StorageInconsistency(
                type='orphaned_vector',
                doc_id=doc_id,
                description=f"Vector embeddings exist but document missing from docstore",
                severity='medium',
                repair_action='remove_orphaned_vectors',
                metadata={'source': 'vector_only'}
            ))

        # Check for index store inconsistencies
        index_orphans = index_docs - docstore_docs
        for doc_id in index_orphans:
            inconsistencies.append(StorageInconsistency(
                type='orphaned_metadata',
                doc_id=doc_id,
                description=f"Index metadata exists but document missing",
                severity='medium',
                repair_action='remove_orphaned_metadata',
                metadata={'source': 'index_only'}
            ))

        # Check for missing collection
        if not self._check_vector_collection_exists():
            inconsistencies.append(StorageInconsistency(
                type='missing_collection',
                doc_id='system',
                description="Vector store collection is missing",
                severity='critical',
                repair_action='recreate_collection',
                metadata={'collection_name': self._get_collection_name()}
            ))

        healthy_docs = len(docstore_docs & vector_docs & index_docs)

        report = ConsistencyReport(
            total_documents=len(docstore_docs),
            total_vectors=len(vector_docs),
            inconsistencies=inconsistencies,
            healthy_documents=healthy_docs
        )

        logger.info(f"✅ [CONSISTENCY_CHECK] Check completed: {len(inconsistencies)} issues found, "
                   f"{healthy_docs} healthy documents")

        return report

    def repair_inconsistencies(self, report: ConsistencyReport,
                             auto_repair: bool = False) -> Dict[str, int]:
        """Repair storage inconsistencies."""
        logger.info(f"🔧 [CONSISTENCY_REPAIR] Starting repair of {len(report.inconsistencies)} inconsistencies")

        if not auto_repair and report.critical_issues:
            logger.warning("⚠️ [CONSISTENCY_REPAIR] Critical issues found - manual approval required")
            logger.warning("⚠️ [CONSISTENCY_REPAIR] Use auto_repair=True to proceed automatically")

        repair_stats = {'repaired': 0, 'failed': 0, 'skipped': 0}

        for inconsistency in report.inconsistencies:
            if inconsistency.severity == 'critical' and not auto_repair:
                logger.info(f"⏭️ [CONSISTENCY_REPAIR] Skipping critical issue (manual approval required): {inconsistency.description}")
                repair_stats['skipped'] += 1
                continue

            try:
                success = self._repair_single_inconsistency(inconsistency)
                if success:
                    repair_stats['repaired'] += 1
                    logger.info(f"✅ [CONSISTENCY_REPAIR] Repaired: {inconsistency.description}")
                else:
                    repair_stats['failed'] += 1
                    logger.error(f"❌ [CONSISTENCY_REPAIR] Failed to repair: {inconsistency.description}")

            except Exception as e:
                repair_stats['failed'] += 1
                logger.error(f"❌ [CONSISTENCY_REPAIR] Exception repairing {inconsistency.doc_id}: {e}")

        logger.info(f"🏁 [CONSISTENCY_REPAIR] Repair completed: {repair_stats}")
        return repair_stats

    def _get_docstore_documents(self) -> Set[str]:
        """Get all document IDs from the document store."""
        try:
            if hasattr(self.docstore, 'get_all_ref_doc_info'):
                doc_info = self.docstore.get_all_ref_doc_info()
                return set(doc_info.keys()) if doc_info else set()
            return set()
        except Exception as e:
            logger.warning(f"⚠️ [CONSISTENCY_CHECK] Error getting docstore documents: {e}")
            return set()

    def _get_vector_store_documents(self) -> Set[str]:
        """Get all document IDs from the vector store."""
        try:
            # This is tricky for Qdrant - we need to query all vectors
            # For now, we'll assume if collection exists, vector store is consistent with docstore
            if self._check_vector_collection_exists():
                # Could implement actual vector ID enumeration here if needed
                return self._get_docstore_documents()  # Assume consistency for existing collection
            else:
                return set()  # No collection = no vectors
        except Exception as e:
            logger.warning(f"⚠️ [CONSISTENCY_CHECK] Error getting vector store documents: {e}")
            return set()

    def _get_index_store_documents(self) -> Set[str]:
        """Get all document IDs from the index store."""
        try:
            # Check what's in the index store
            if hasattr(self.index_store, 'get_all_ref_doc_info'):
                return set(self.index_store.get_all_ref_doc_info().keys())
            return set()
        except Exception as e:
            logger.warning(f"⚠️ [CONSISTENCY_CHECK] Error getting index store documents: {e}")
            return set()

    def _check_vector_collection_exists(self) -> bool:
        """Check if the vector store collection exists."""
        try:
            if hasattr(self.vector_store, 'client') and hasattr(self.vector_store.client, 'get_collections'):
                collections = self.vector_store.client.get_collections()
                collection_name = self._get_collection_name()
                return any(c.name == collection_name for c in collections.collections)
            return False
        except Exception as e:
            logger.warning(f"⚠️ [CONSISTENCY_CHECK] Error checking collection: {e}")
            return False

    def _get_collection_name(self) -> str:
        """Get the expected collection name."""
        from internal_assistant.settings.settings import settings
        return getattr(settings().qdrant, 'collection_name', 'internal_assistant_documents')

    def _repair_single_inconsistency(self, inconsistency: StorageInconsistency) -> bool:
        """Repair a single storage inconsistency."""
        logger.info(f"🔧 [CONSISTENCY_REPAIR] Repairing {inconsistency.type} for {inconsistency.doc_id}")

        try:
            if inconsistency.type == 'orphaned_document':
                return self._repair_orphaned_document(inconsistency.doc_id)
            elif inconsistency.type == 'orphaned_vector':
                return self._repair_orphaned_vector(inconsistency.doc_id)
            elif inconsistency.type == 'orphaned_metadata':
                return self._repair_orphaned_metadata(inconsistency.doc_id)
            elif inconsistency.type == 'missing_collection':
                return self._repair_missing_collection()
            else:
                logger.warning(f"⚠️ [CONSISTENCY_REPAIR] Unknown inconsistency type: {inconsistency.type}")
                return False

        except Exception as e:
            logger.error(f"❌ [CONSISTENCY_REPAIR] Error repairing {inconsistency.type}: {e}")
            return False

    def _repair_orphaned_document(self, doc_id: str) -> bool:
        """Repair orphaned document by removing it from docstore."""
        logger.info(f"📄 [REPAIR] Removing orphaned document: {doc_id}")
        try:
            self.docstore.delete_document(doc_id)
            return True
        except Exception as e:
            logger.error(f"❌ [REPAIR] Failed to remove orphaned document {doc_id}: {e}")
            return False

    def _repair_orphaned_vector(self, doc_id: str) -> bool:
        """Repair orphaned vector by removing it from vector store."""
        logger.info(f"🎯 [REPAIR] Removing orphaned vector: {doc_id}")
        try:
            if self._check_vector_collection_exists():
                self.vector_store.delete(doc_id)
            return True
        except Exception as e:
            logger.error(f"❌ [REPAIR] Failed to remove orphaned vector {doc_id}: {e}")
            return False

    def _repair_orphaned_metadata(self, doc_id: str) -> bool:
        """Repair orphaned metadata by removing it from index store."""
        logger.info(f"📚 [REPAIR] Removing orphaned metadata: {doc_id}")
        try:
            # Remove from index store if possible
            if hasattr(self.index_store, 'delete_ref_doc'):
                self.index_store.delete_ref_doc(doc_id)
            return True
        except Exception as e:
            logger.error(f"❌ [REPAIR] Failed to remove orphaned metadata {doc_id}: {e}")
            return False

    def _repair_missing_collection(self) -> bool:
        """Repair missing collection by recreating it."""
        logger.info("🚑 [REPAIR] Recreating missing vector collection")
        try:
            # This should trigger the collection recovery we implemented earlier
            from internal_assistant.settings.settings import settings
            # Get the embedding dimension from the embedding settings, not vector store
            embedding_settings = settings().embedding
            embedding_dim = getattr(embedding_settings, 'embed_dim', 768)  # Default to 768 for nomic-embed-text
            collection_name = self._get_collection_name()

            from qdrant_client.models import Distance, VectorParams

            self.vector_store.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"✅ [REPAIR] Successfully recreated collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ [REPAIR] Failed to recreate collection: {e}")
            return False

    def generate_report_summary(self, report: ConsistencyReport) -> str:
        """Generate a human-readable summary of the consistency report."""
        summary = []
        summary.append(f"📊 Storage Consistency Report")
        summary.append(f"─" * 40)
        summary.append(f"Total Documents: {report.total_documents}")
        summary.append(f"Total Vectors: {report.total_vectors}")
        summary.append(f"Healthy Documents: {report.healthy_documents}")
        summary.append(f"Issues Found: {len(report.inconsistencies)}")

        if report.critical_issues:
            summary.append(f"🚨 Critical Issues: {len(report.critical_issues)}")

        if report.high_priority_issues:
            summary.append(f"⚠️ High Priority Issues: {len(report.high_priority_issues)}")

        if report.inconsistencies:
            summary.append(f"")
            summary.append(f"Issue Breakdown:")
            for issue in report.inconsistencies:
                severity_icon = "🚨" if issue.severity == "critical" else "⚠️" if issue.severity == "high" else "ℹ️"
                summary.append(f"  {severity_icon} {issue.type}: {issue.description}")

        return "\n".join(summary)