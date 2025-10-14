import asyncio
import logging
import shutil
import threading
import time
import weakref
from pathlib import Path

import psutil
import pytest

from internal_assistant.components.vector_store.vector_store_component import (
    VectorStoreComponent,
)
from internal_assistant.paths import local_data_path
from tests.fixtures.mock_injector import MockInjector

logger = logging.getLogger(__name__)

# Global registry to track all Qdrant client instances
_qdrant_clients: set[weakref.ref] = set()
_qdrant_lock = threading.Lock()
_test_mode = False
_singleton_client = None


def set_test_mode(enabled: bool):
    """Enable or disable test mode for Qdrant client management."""
    global _test_mode
    _test_mode = enabled
    logger.debug(f"Qdrant test mode: {enabled}")


def register_qdrant_client(client):
    """Register a Qdrant client for cleanup tracking."""
    if client is not None:
        with _qdrant_lock:
            _qdrant_clients.add(weakref.ref(client))
            logger.debug(f"Registered Qdrant client: {id(client)}")


def cleanup_all_qdrant_clients():
    """Close all registered Qdrant client instances."""
    global _qdrant_clients

    with _qdrant_lock:
        # Get all valid client references
        valid_clients = []
        dead_refs = []

        for client_ref in _qdrant_clients:
            client = client_ref()
            if client is not None:
                valid_clients.append(client)
            else:
                dead_refs.append(client_ref)

        # Remove dead references
        for dead_ref in dead_refs:
            _qdrant_clients.discard(dead_ref)

        # Close all valid clients - be more careful about timing and state
        for client in valid_clients:
            try:
                # Check if client is still valid before closing
                if hasattr(client, "_client") and client._client is not None:
                    # Always close in test mode to ensure proper cleanup
                    client.close()
                    logger.debug(f"Closed Qdrant client: {id(client)}")
                else:
                    logger.debug(f"Qdrant client {id(client)} already closed, skipping")
            except Exception as e:
                logger.warning(f"Error closing Qdrant client {id(client)}: {e}")

        # Clear the set after cleanup
        _qdrant_clients.clear()
        logger.debug(f"Cleaned up {len(valid_clients)} Qdrant client instances")

        # Force a small delay to ensure all clients are fully closed
        import time

        time.sleep(0.1)


def get_qdrant_test_path() -> Path:
    """Get the Qdrant path used in test configuration."""
    # Check if we're in test mode and use the test-specific path
    test_data_path = Path("local_data/tests")
    if test_data_path.exists():
        return test_data_path
    # Fallback to the standard path
    return local_data_path / "internal_assistant" / "qdrant"


def cleanup_qdrant_locks() -> None:
    """Force cleanup of Qdrant lock files to prevent conflicts."""
    try:
        # Try test path first, then fallback to standard path
        qdrant_paths = [
            get_qdrant_test_path(),
            local_data_path / "internal_assistant" / "qdrant",
            Path("local_data/tests"),
            Path("local_data/internal_assistant/qdrant"),
        ]

        for qdrant_path in qdrant_paths:
            if qdrant_path.exists():
                logger.debug(f"Cleaning up Qdrant locks in: {qdrant_path}")

                # Remove lock files
                for lock_file in qdrant_path.glob("*.lock"):
                    try:
                        lock_file.unlink()
                        logger.debug(f"Removed Qdrant lock file: {lock_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove lock file {lock_file}: {e}")

                # Also check for portalocker files
                for lock_file in qdrant_path.glob("*.portalocker"):
                    try:
                        lock_file.unlink()
                        logger.debug(f"Removed portalocker file: {lock_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove portalocker file {lock_file}: {e}"
                        )

                # Check for any other lock-like files
                for lock_file in qdrant_path.glob("*lock*"):
                    try:
                        lock_file.unlink()
                        logger.debug(f"Removed additional lock file: {lock_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove additional lock file {lock_file}: {e}"
                        )

    except Exception as e:
        logger.warning(f"Error during Qdrant lock cleanup: {e}")


def force_collection_cleanup() -> None:
    """Force cleanup of Qdrant collections to ensure isolation."""
    try:
        # Try test path first, then fallback to standard path
        qdrant_paths = [
            get_qdrant_test_path(),
            local_data_path / "internal_assistant" / "qdrant",
            Path("local_data/tests"),
            Path("local_data/internal_assistant/qdrant"),
        ]

        for qdrant_path in qdrant_paths:
            if qdrant_path.exists():
                # Remove the entire qdrant directory to ensure clean state
                shutil.rmtree(qdrant_path, ignore_errors=True)
                logger.debug(f"Forced Qdrant collection cleanup in: {qdrant_path}")
    except Exception as e:
        logger.warning(f"Error during Qdrant collection cleanup: {e}")


def kill_qdrant_processes() -> None:
    """Kill any existing Qdrant processes that might be holding locks."""
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if "qdrant" in cmdline.lower() or "python" in proc.info["name"].lower():
                    if "test" in cmdline.lower() or "pytest" in cmdline.lower():
                        logger.debug(f"Found test process: {proc.info['pid']}")
                        continue
                    logger.debug(
                        f"Terminating Qdrant-related process: {proc.info['pid']}"
                    )
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
    except Exception as e:
        logger.warning(f"Error during process cleanup: {e}")


def wait_for_lock_release(qdrant_path: Path, timeout: float = 5.0) -> bool:
    """Wait for Qdrant lock files to be released by processes."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        lock_files = list(qdrant_path.glob("*.lock"))
        if not lock_files:
            return True

        # Check if any lock files are still being held
        all_released = True
        for lock_file in lock_files:
            try:
                # Try to open the file exclusively to see if it's locked
                with open(lock_file) as f:
                    pass
            except (PermissionError, OSError):
                all_released = False
                break

        if all_released:
            return True

        time.sleep(0.1)

    return False


@pytest.fixture(autouse=True, scope="function")
async def qdrant_isolation(injector: MockInjector) -> None:
    """Force clean Qdrant state - prevents lock conflicts.

    This fixture ensures each test starts with a clean Qdrant state by:
    1. Enabling test mode
    2. Minimal pre-test cleanup to avoid interfering with running tests
    3. Thorough post-test cleanup to ensure isolation
    """
    # Enable test mode
    set_test_mode(True)

    # Pre-test setup - minimal cleanup to avoid race conditions
    logger.debug("Starting Qdrant isolation for test")

    # Only clean up obvious conflicts, don't close active clients
    try:
        # Clean up any existing lock files
        cleanup_qdrant_locks()

        # Kill any existing Qdrant processes that might be holding locks
        kill_qdrant_processes()

        # Wait for locks to be released
        await asyncio.sleep(0.1)

        logger.debug("Pre-test cleanup completed")
    except Exception as e:
        logger.warning(f"Pre-test cleanup error: {e}")

    # Yield control to the test - don't interfere during execution
    yield

    # Post-test cleanup - only after the test completes
    logger.debug("Starting post-test cleanup")

    # Small delay to ensure all operations are complete
    await asyncio.sleep(0.2)

    # Clear the entire injector cache to force recreation of all components
    try:
        injector.clear_cache()
        logger.debug("Cleared injector cache for next test")
    except Exception as e:
        logger.warning(f"Error clearing injector cache: {e}")

    # Now do thorough cleanup of all Qdrant clients
    try:
        cleanup_all_qdrant_clients()
        logger.debug("Cleaned up all Qdrant client instances")
    except Exception as e:
        logger.warning(f"Error cleaning up Qdrant clients: {e}")

    # Force collection cleanup
    try:
        force_collection_cleanup()
        logger.debug("Forced Qdrant collection cleanup")
    except Exception as e:
        logger.warning(f"Error forcing Qdrant collection cleanup: {e}")

    # Additional cleanup to ensure no lingering processes
    try:
        cleanup_qdrant_locks()
        kill_qdrant_processes()
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.warning(f"Error in additional cleanup: {e}")

    # Disable test mode
    set_test_mode(False)
    logger.debug("Completed Qdrant isolation cleanup")


@pytest.fixture(autouse=True)
def _auto_close_vector_store_client(injector: MockInjector) -> None:
    """Auto close VectorStore client after each test.

    VectorStore client (qdrant/chromadb) opens a connection the
    Database that causes issues when running tests too fast,
    so close explicitly after each test.
    """
    yield
    # Only close after the test is completely done
    try:
        vector_store = injector.get(VectorStoreComponent)
        if hasattr(vector_store, "close"):
            vector_store.close()
        # Also register the client for global cleanup
        if hasattr(vector_store, "vector_store") and hasattr(
            vector_store.vector_store, "client"
        ):
            register_qdrant_client(vector_store.vector_store.client)
    except Exception as e:
        logger.warning(f"Error in auto-close fixture: {e}")


# Monkey patch QdrantClient to track instances and prevent multiple instances in test mode
def patch_qdrant_client():
    """Patch QdrantClient to automatically register instances for cleanup and prevent multiple instances in test mode."""
    try:
        from qdrant_client import QdrantClient

        original_init = QdrantClient.__init__

        def patched_init(self, *args, **kwargs):
            global _test_mode

            # In test mode, disable singleton management entirely to avoid race conditions
            if _test_mode:
                # Just create a new client and register it for cleanup
                original_init(self, *args, **kwargs)
                register_qdrant_client(self)
                logger.debug(f"Created QdrantClient for test mode: {id(self)}")
            else:
                # Normal mode - just register for cleanup
                original_init(self, *args, **kwargs)
                register_qdrant_client(self)
                logger.debug(f"Created and registered QdrantClient: {id(self)}")

        QdrantClient.__init__ = patched_init

        logger.debug(
            "Successfully patched QdrantClient for tracking (singleton disabled in test mode)"
        )
    except ImportError:
        logger.warning("QdrantClient not available for patching")
    except Exception as e:
        logger.warning(f"Failed to patch QdrantClient: {e}")


# Apply the patch when the module is imported
patch_qdrant_client()
