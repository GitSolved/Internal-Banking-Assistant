"""Storage management service for administrative operations and emergency recovery."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from internal_assistant.paths import local_data_path
from internal_assistant.server.ingest.storage_consistency_service import (
    StorageConsistencyService,
)

logger = logging.getLogger(__name__)


class StorageManagementService:
    """Administrative service for storage operations and emergency recovery."""

    def __init__(self, storage_context, ingest_service):
        self.storage_context = storage_context
        self.ingest_service = ingest_service
        self.consistency_service = StorageConsistencyService(storage_context)

    def emergency_clear_all_documents(self, force: bool = False) -> dict[str, int]:
        """Emergency procedure to clear all documents from all storage backends."""
        logger.warning("🚨 [EMERGENCY_CLEAR] Starting emergency document clearance")

        if not force:
            logger.error(
                "❌ [EMERGENCY_CLEAR] Emergency clear requires force=True parameter"
            )
            return {"error": 1, "cleared": 0}

        results = {"docstore": 0, "vector_store": 0, "index_store": 0, "errors": 0}

        # Clear document store
        try:
            logger.info("📄 [EMERGENCY_CLEAR] Clearing document store...")
            doc_ids = list(self.storage_context.docstore.get_all_ref_doc_info().keys())
            for doc_id in doc_ids:
                try:
                    self.storage_context.docstore.delete_document(doc_id)
                    results["docstore"] += 1
                except Exception as e:
                    logger.error(
                        f"❌ [EMERGENCY_CLEAR] Error clearing doc {doc_id}: {e}"
                    )
                    results["errors"] += 1

            logger.info(
                f"✅ [EMERGENCY_CLEAR] Cleared {results['docstore']} documents from docstore"
            )

        except Exception as e:
            logger.error(f"❌ [EMERGENCY_CLEAR] Error accessing docstore: {e}")
            results["errors"] += 1

        # Clear vector store
        try:
            logger.info("🎯 [EMERGENCY_CLEAR] Clearing vector store...")
            if hasattr(self.storage_context.vector_store, "client"):
                client = self.storage_context.vector_store.client
                collection_name = self._get_collection_name()

                # Try to delete and recreate collection (fastest way to clear)
                try:
                    client.delete_collection(collection_name)
                    logger.info(
                        f"🗑️ [EMERGENCY_CLEAR] Deleted collection: {collection_name}"
                    )

                    # Recreate empty collection
                    self._recreate_empty_collection(client, collection_name)
                    results["vector_store"] = len(doc_ids)  # Assume all were cleared

                except Exception as e:
                    logger.warning(
                        f"⚠️ [EMERGENCY_CLEAR] Collection deletion failed: {e}"
                    )
                    # Fall back to individual deletion
                    for doc_id in doc_ids:
                        try:
                            self.storage_context.vector_store.delete(doc_id)
                            results["vector_store"] += 1
                        except Exception:
                            pass  # Expected if collection is missing

        except Exception as e:
            logger.error(f"❌ [EMERGENCY_CLEAR] Error clearing vector store: {e}")
            results["errors"] += 1

        # Clear index store
        try:
            logger.info("📚 [EMERGENCY_CLEAR] Clearing index store...")
            for doc_id in doc_ids:
                try:
                    if hasattr(self.storage_context.index_store, "delete_ref_doc"):
                        self.storage_context.index_store.delete_ref_doc(doc_id)
                    results["index_store"] += 1
                except Exception:
                    pass  # Continue even if deletion fails

            logger.info(
                f"✅ [EMERGENCY_CLEAR] Cleared {results['index_store']} documents from index store"
            )

        except Exception as e:
            logger.error(f"❌ [EMERGENCY_CLEAR] Error clearing index store: {e}")
            results["errors"] += 1

        # Persist changes
        try:
            logger.info("💾 [EMERGENCY_CLEAR] Persisting clearance...")
            self._persist_all_stores()
            logger.info("✅ [EMERGENCY_CLEAR] Persistence completed")
        except Exception as e:
            logger.error(f"❌ [EMERGENCY_CLEAR] Persistence failed: {e}")
            results["errors"] += 1

        total_cleared = (
            results["docstore"] + results["vector_store"] + results["index_store"]
        )
        logger.info(
            f"🏁 [EMERGENCY_CLEAR] Emergency clearance completed: {total_cleared} documents cleared, {results['errors']} errors"
        )

        return results

    def force_recreate_collection(self) -> bool:
        """Force recreation of the Qdrant collection."""
        logger.info("🚑 [FORCE_RECREATE] Force recreating Qdrant collection")

        try:
            client = self.storage_context.vector_store.client
            collection_name = self._get_collection_name()

            # Delete existing collection if it exists
            try:
                client.delete_collection(collection_name)
                logger.info(
                    f"🗑️ [FORCE_RECREATE] Deleted existing collection: {collection_name}"
                )
            except Exception as e:
                logger.info(f"ℹ️ [FORCE_RECREATE] Collection may not exist: {e}")

            # Recreate collection
            success = self._recreate_empty_collection(client, collection_name)
            if success:
                logger.info(
                    f"✅ [FORCE_RECREATE] Successfully recreated collection: {collection_name}"
                )
                return True
            else:
                logger.error("❌ [FORCE_RECREATE] Failed to recreate collection")
                return False

        except Exception as e:
            logger.error(f"❌ [FORCE_RECREATE] Error during force recreation: {e}")
            return False

    def backup_storage_state(self, backup_name: str | None = None) -> Path:
        """Create a backup of the current storage state."""
        if backup_name is None:
            backup_name = f"storage_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_dir = Path(str(local_data_path)) / "backups" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"💾 [BACKUP] Creating storage backup: {backup_dir}")

        try:
            # Backup document store
            docstore_path = Path(str(local_data_path)) / "docstore.json"
            if docstore_path.exists():
                shutil.copy2(docstore_path, backup_dir / "docstore.json")

            # Backup index store
            index_store_path = Path(str(local_data_path)) / "index_store.json"
            if index_store_path.exists():
                shutil.copy2(index_store_path, backup_dir / "index_store.json")

            # Backup Qdrant data
            qdrant_dir = Path(str(local_data_path)) / "qdrant"
            if qdrant_dir.exists():
                shutil.copytree(qdrant_dir, backup_dir / "qdrant", dirs_exist_ok=True)

            logger.info(f"✅ [BACKUP] Backup completed: {backup_dir}")
            return backup_dir

        except Exception as e:
            logger.error(f"❌ [BACKUP] Backup failed: {e}")
            raise

    def restore_storage_state(self, backup_path: Path, force: bool = False) -> bool:
        """Restore storage state from a backup."""
        if not backup_path.exists():
            logger.error(f"❌ [RESTORE] Backup path does not exist: {backup_path}")
            return False

        if not force:
            logger.error("❌ [RESTORE] Restore requires force=True parameter")
            return False

        logger.info(f"🔄 [RESTORE] Restoring storage from backup: {backup_path}")

        try:
            # Stop any ongoing operations
            base_path = Path(str(local_data_path))

            # Restore document store
            backup_docstore = backup_path / "docstore.json"
            if backup_docstore.exists():
                shutil.copy2(backup_docstore, base_path / "docstore.json")

            # Restore index store
            backup_index = backup_path / "index_store.json"
            if backup_index.exists():
                shutil.copy2(backup_index, base_path / "index_store.json")

            # Restore Qdrant data
            backup_qdrant = backup_path / "qdrant"
            if backup_qdrant.exists():
                target_qdrant = base_path / "qdrant"
                if target_qdrant.exists():
                    shutil.rmtree(target_qdrant)
                shutil.copytree(backup_qdrant, target_qdrant)

            logger.info(f"✅ [RESTORE] Restore completed from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"❌ [RESTORE] Restore failed: {e}")
            return False

    def diagnose_storage_health(self) -> dict[str, any]:
        """Comprehensive storage health diagnosis."""
        logger.info("🔍 [DIAGNOSIS] Running comprehensive storage health diagnosis")

        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "components": {},
            "consistency_report": None,
            "recommendations": [],
        }

        # Check each storage component
        diagnosis["components"]["docstore"] = self._diagnose_docstore()
        diagnosis["components"]["vector_store"] = self._diagnose_vector_store()
        diagnosis["components"]["index_store"] = self._diagnose_index_store()

        # Run consistency check
        try:
            report = self.consistency_service.check_consistency()
            diagnosis["consistency_report"] = {
                "total_documents": report.total_documents,
                "total_vectors": report.total_vectors,
                "healthy_documents": report.healthy_documents,
                "issues_count": len(report.inconsistencies),
                "critical_issues": len(report.critical_issues),
                "high_priority_issues": len(report.high_priority_issues),
            }
        except Exception as e:
            diagnosis["consistency_report"] = {"error": str(e)}

        # Generate overall health assessment
        all_healthy = all(
            comp.get("status") == "healthy" for comp in diagnosis["components"].values()
        )
        has_critical = (
            diagnosis["consistency_report"]
            and diagnosis["consistency_report"].get("critical_issues", 0) > 0
        )

        if all_healthy and not has_critical:
            diagnosis["overall_health"] = "healthy"
        elif has_critical:
            diagnosis["overall_health"] = "critical"
        else:
            diagnosis["overall_health"] = "degraded"

        # Generate recommendations
        diagnosis["recommendations"] = self._generate_health_recommendations(diagnosis)

        logger.info(
            f"✅ [DIAGNOSIS] Health diagnosis completed: {diagnosis['overall_health']}"
        )
        return diagnosis

    def _get_collection_name(self) -> str:
        """Get the expected collection name."""
        from internal_assistant.settings.settings import settings

        return getattr(
            settings().qdrant, "collection_name", "internal_assistant_documents"
        )

    def _recreate_empty_collection(self, client, collection_name: str) -> bool:
        """Recreate an empty collection with proper configuration."""
        try:
            from qdrant_client.models import Distance, VectorParams

            from internal_assistant.settings.settings import settings

            # Get the embedding dimension from the embedding settings, not vector store
            embedding_settings = settings().embedding
            embedding_dim = getattr(
                embedding_settings, "embed_dim", 768
            )  # Default to 768 for nomic-embed-text

            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"❌ [RECREATE] Failed to recreate collection: {e}")
            return False

    def _persist_all_stores(self) -> None:
        """Persist changes to all storage backends."""
        if hasattr(self.storage_context.docstore, "persist"):
            self.storage_context.docstore.persist()

        if hasattr(self.storage_context.index_store, "persist"):
            self.storage_context.index_store.persist()

        # Vector store persistence is usually automatic

    def _diagnose_docstore(self) -> dict[str, any]:
        """Diagnose document store health."""
        try:
            doc_info = self.storage_context.docstore.get_all_ref_doc_info()
            return {
                "status": "healthy",
                "document_count": len(doc_info) if doc_info else 0,
                "accessible": True,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "accessible": False}

    def _diagnose_vector_store(self) -> dict[str, any]:
        """Diagnose vector store health."""
        try:
            client = self.storage_context.vector_store.client
            collections = client.get_collections()
            collection_name = self._get_collection_name()

            collection_exists = any(
                c.name == collection_name for c in collections.collections
            )

            if collection_exists:
                collection_info = client.get_collection(collection_name)
                return {
                    "status": "healthy",
                    "collection_exists": True,
                    "points_count": collection_info.points_count,
                    "collection_status": collection_info.status,
                }
            else:
                return {
                    "status": "degraded",
                    "collection_exists": False,
                    "issue": "Missing collection",
                }

        except Exception as e:
            return {"status": "error", "error": str(e), "accessible": False}

    def _diagnose_index_store(self) -> dict[str, any]:
        """Diagnose index store health."""
        try:
            # Basic accessibility test
            if hasattr(self.storage_context.index_store, "get_all_ref_doc_info"):
                ref_info = self.storage_context.index_store.get_all_ref_doc_info()
                return {
                    "status": "healthy",
                    "document_count": len(ref_info) if ref_info else 0,
                    "accessible": True,
                }
            else:
                return {"status": "degraded", "issue": "Limited functionality"}
        except Exception as e:
            return {"status": "error", "error": str(e), "accessible": False}

    def _generate_health_recommendations(self, diagnosis: dict[str, any]) -> list[str]:
        """Generate recommendations based on health diagnosis."""
        recommendations = []

        # Check for missing collection
        vector_status = diagnosis["components"].get("vector_store", {})
        if not vector_status.get("collection_exists", True):
            recommendations.append(
                "Run force_recreate_collection() to recreate missing vector collection"
            )

        # Check for critical consistency issues
        consistency = diagnosis.get("consistency_report", {})
        if consistency.get("critical_issues", 0) > 0:
            recommendations.append(
                "Run consistency repair to address critical storage issues"
            )

        # Check for component errors
        for component, status in diagnosis["components"].items():
            if status.get("status") == "error":
                recommendations.append(
                    f"Investigate {component} error: {status.get('error', 'Unknown error')}"
                )

        # Check for inconsistent document counts
        if consistency.get("total_documents", 0) != consistency.get("total_vectors", 0):
            recommendations.append(
                "Storage backends have inconsistent document counts - run consistency check"
            )

        if not recommendations:
            recommendations.append(
                "Storage appears healthy - no immediate action required"
            )

        return recommendations
