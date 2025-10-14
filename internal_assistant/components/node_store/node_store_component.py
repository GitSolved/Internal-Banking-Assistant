import logging

from injector import inject, singleton
from llama_index.core.storage.docstore import BaseDocumentStore, SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.storage.index_store.types import BaseIndexStore

from internal_assistant.paths import local_data_path
from internal_assistant.settings.settings import Settings

logger = logging.getLogger(__name__)


@singleton
class NodeStoreComponent:
    index_store: BaseIndexStore
    doc_store: BaseDocumentStore

    @inject
    def __init__(self, settings: Settings) -> None:
        match settings.nodestore.database:
            case "simple":
                try:
                    self.index_store = SimpleIndexStore.from_persist_dir(
                        persist_dir=str(local_data_path)
                    )
                except FileNotFoundError:
                    logger.debug("Local index store not found, creating a new one")
                    self.index_store = SimpleIndexStore()

                try:
                    import os
                    import json

                    docstore_path = os.path.join(str(local_data_path), "docstore.json")
                    logger.info(f"📖 [DOCSTORE_LOAD] Loading docstore from: {docstore_path}")
                    logger.info(f"📖 [DOCSTORE_LOAD] File exists: {os.path.exists(docstore_path)}")

                    # Check if file exists and log its size
                    if os.path.exists(docstore_path):
                        file_size = os.path.getsize(docstore_path)
                        logger.info(f"📖 [DOCSTORE_LOAD] File size: {file_size} bytes")

                        # Read and inspect the raw JSON to understand structure
                        try:
                            with open(docstore_path, 'r') as f:
                                raw_data = json.load(f)
                                logger.info(f"📖 [DOCSTORE_LOAD] JSON keys in file: {list(raw_data.keys())}")

                                # Check each collection
                                for key in ["docstore/data", "docstore/metadata", "docstore/ref_doc_info"]:
                                    if key in raw_data:
                                        count = len(raw_data[key])
                                        logger.info(f"📖 [DOCSTORE_LOAD] Collection '{key}' has {count} entries in file")
                                    else:
                                        logger.warning(f"⚠️ [DOCSTORE_LOAD] Collection '{key}' MISSING from file!")
                        except Exception as e:
                            logger.error(f"❌ [DOCSTORE_LOAD] Error reading JSON file: {e}")

                    # Now load using SimpleDocumentStore
                    self.doc_store = SimpleDocumentStore.from_persist_dir(
                        persist_dir=str(local_data_path)
                    )
                    logger.info("📖 [DOCSTORE_LOAD] SimpleDocumentStore.from_persist_dir() completed")

                    # CRITICAL FIX: Verify docstore actually loaded the data
                    # Check what's in memory after loading
                    try:
                        ref_doc_info = self.doc_store.get_all_ref_doc_info()
                        doc_hashes = self.doc_store.get_all_document_hashes()

                        logger.info(f"📖 [DOCSTORE_LOAD] After loading - ref_doc_info count: {len(ref_doc_info) if ref_doc_info else 0}")
                        logger.info(f"📖 [DOCSTORE_LOAD] After loading - doc_hashes count: {len(doc_hashes) if doc_hashes else 0}")

                        # Check the internal _data structure
                        if hasattr(self.doc_store, '_data'):
                            logger.info(f"📖 [DOCSTORE_LOAD] Internal _data keys: {list(self.doc_store._data.keys())}")
                            for key in self.doc_store._data.keys():
                                logger.info(f"📖 [DOCSTORE_LOAD] Internal _data['{key}'] has {len(self.doc_store._data[key])} entries")

                        # If file had data but memory doesn't, this is the BUG!
                        if os.path.exists(docstore_path):
                            with open(docstore_path, 'r') as f:
                                raw_data = json.load(f)
                                file_has_ref_docs = "docstore/ref_doc_info" in raw_data and len(raw_data["docstore/ref_doc_info"]) > 0
                                memory_has_ref_docs = ref_doc_info and len(ref_doc_info) > 0

                                if file_has_ref_docs and not memory_has_ref_docs:
                                    logger.error("❌ [DOCSTORE_BUG] CRITICAL: File has ref_doc_info but memory doesn't!")
                                    logger.error(f"❌ [DOCSTORE_BUG] File has {len(raw_data['docstore/ref_doc_info'])} entries")
                                    logger.error("❌ [DOCSTORE_BUG] Memory has 0 entries")
                                    logger.error("❌ [DOCSTORE_BUG] SimpleDocumentStore.from_persist_dir() failed to load data!")

                                    # FALLBACK: Manually populate the docstore from file
                                    logger.info("🔧 [DOCSTORE_FIX] Attempting manual data load from file...")
                                    try:
                                        # Access the internal KV store and populate it directly
                                        if hasattr(self.doc_store, '_data'):
                                            self.doc_store._data = raw_data
                                            logger.info("✅ [DOCSTORE_FIX] Manually loaded data into docstore._data")

                                            # Re-verify
                                            ref_doc_info = self.doc_store.get_all_ref_doc_info()
                                            logger.info(f"✅ [DOCSTORE_FIX] After manual load: {len(ref_doc_info)} documents")
                                        else:
                                            logger.error("❌ [DOCSTORE_FIX] Cannot access _data attribute for manual load")
                                    except Exception as fix_error:
                                        logger.error(f"❌ [DOCSTORE_FIX] Manual load failed: {fix_error}")

                        if not ref_doc_info and not doc_hashes:
                            logger.warning("⚠️ [DOCSTORE_FIX] Docstore is empty after load - will create fresh docstore")

                            if os.path.exists(docstore_path):
                                os.remove(docstore_path)
                                logger.info("✅ [DOCSTORE_FIX] Deleted empty docstore.json")

                            # Let FileNotFoundError handler create it properly
                            raise FileNotFoundError("Empty docstore detected and removed")
                        else:
                            logger.info(f"✅ [DOCSTORE_CHECK] Docstore loaded successfully with {len(ref_doc_info)} documents")

                            # Log first few document file names for verification
                            if ref_doc_info:
                                count = 0
                                for doc_id, ref_info in ref_doc_info.items():
                                    if count < 3 and hasattr(ref_info, 'metadata') and ref_info.metadata:
                                        file_name = ref_info.metadata.get('file_name', 'Unknown')
                                        page = ref_info.metadata.get('page_label', '?')
                                        logger.info(f"✅ [DOCSTORE_CHECK] Document {count+1}: {file_name} (page {page})")
                                        count += 1

                    except FileNotFoundError:
                        # Re-raise to let outer handler create fresh docstore
                        raise
                    except Exception as e:
                        logger.error(f"❌ [DOCSTORE_LOAD] Error checking docstore state: {e}", exc_info=True)

                        if os.path.exists(docstore_path):
                            os.remove(docstore_path)
                            logger.info("✅ [DOCSTORE_FIX] Deleted potentially corrupt docstore.json")

                        # Let FileNotFoundError handler create it properly
                        raise FileNotFoundError("Docstore error detected, removed file for recreation")

                except FileNotFoundError:
                    logger.debug("Local document store not found, creating a new one")
                    self.doc_store = SimpleDocumentStore()

            case "postgres":
                try:
                    from llama_index.storage.docstore.postgres import (  # type: ignore
                        PostgresDocumentStore,
                    )
                    from llama_index.storage.index_store.postgres import (  # type: ignore
                        PostgresIndexStore,
                    )
                except ImportError:
                    raise ImportError(
                        "Postgres dependencies not found, install with `poetry install --extras storage-nodestore-postgres`"
                    ) from None

                if settings.postgres is None:
                    raise ValueError("Postgres index/doc store settings not found.")

                self.index_store = PostgresIndexStore.from_params(
                    **settings.postgres.model_dump(exclude_none=True)
                )

                self.doc_store = PostgresDocumentStore.from_params(
                    **settings.postgres.model_dump(exclude_none=True)
                )

            case _:
                # Should be unreachable
                # The settings validator should have caught this
                raise ValueError(
                    f"Database {settings.nodestore.database} not supported"
                )
