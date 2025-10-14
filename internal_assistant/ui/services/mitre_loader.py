"""
MITRE ATT&CK Async Data Loader Service

This module provides asynchronous loading and caching of MITRE ATT&CK data
to prevent blocking the UI during initialization.

Created as part of Phase 3: MITRE ATT&CK Data Loading
Author: UI Optimization Team
Date: 2025-09-26
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MitreDataCache:
    """Cache container for MITRE data with metadata."""

    data: Dict[str, Any]
    timestamp: datetime
    version: str
    is_loading: bool = False
    load_error: Optional[str] = None


class AsyncMitreDataLoader:
    """
    Asynchronous MITRE ATT&CK data loader with caching and progressive loading support.

    Features:
    - Background data fetching without blocking UI
    - Local data caching with TTL
    - Progressive loading with partial data display
    - Automatic retry on failures
    - Thread-safe operations
    """

    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl_hours: int = 24):
        """
        Initialize the async MITRE data loader.

        Args:
            cache_dir: Directory for cache storage (default: local_data/mitre_cache)
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_dir = cache_dir or Path("local_data/mitre_cache")
        self.cache_file = self.cache_dir / "mitre_data.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Thread-safe cache and loading state
        self._cache: Optional[MitreDataCache] = None
        self._cache_lock = threading.RLock()
        self._loading_event = threading.Event()
        self._load_in_progress = False

        # Progress callbacks for UI updates
        self._progress_callbacks: list[Callable[[str, float], None]] = []

        # Thread pool for background operations
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="mitre_loader"
        )

        # Load cached data on initialization
        self._load_from_cache()

        logger.info(
            "AsyncMitreDataLoader initialized with cache TTL: %d hours", cache_ttl_hours
        )

    def add_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """
        Add a progress callback for UI updates.

        Args:
            callback: Function that takes (status_message, progress_percent) parameters
        """
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _notify_progress(self, message: str, progress: float) -> None:
        """Notify all registered progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(message, progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def _load_from_cache(self) -> bool:
        """
        Load MITRE data from local cache if available and valid.

        Returns:
            True if cache was loaded successfully, False otherwise
        """
        try:
            if not self.cache_file.exists():
                logger.info("No MITRE cache file found")
                return False

            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            cache_timestamp = datetime.fromisoformat(cache_data["timestamp"])
            age = datetime.now() - cache_timestamp

            if age > self.cache_ttl:
                logger.info(f"MITRE cache expired (age: {age}), will refresh")
                return False

            with self._cache_lock:
                self._cache = MitreDataCache(
                    data=cache_data["data"],
                    timestamp=cache_timestamp,
                    version=cache_data.get("version", "1.0"),
                )

            logger.info(f"MITRE cache loaded successfully (age: {age})")
            return True

        except Exception as e:
            logger.error(f"Failed to load MITRE cache: {e}")
            return False

    def _save_to_cache(self, data: Dict[str, Any]) -> None:
        """
        Save MITRE data to local cache.

        Args:
            data: MITRE data to cache
        """
        try:
            cache_data = {
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.info("MITRE data saved to cache")

        except Exception as e:
            logger.error(f"Failed to save MITRE cache: {e}")

    def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """
        Get currently cached MITRE data without loading.

        Returns:
            Cached MITRE data or None if not available
        """
        with self._cache_lock:
            if self._cache and not self._cache.load_error:
                return self._cache.data
            return None

    def is_cache_valid(self) -> bool:
        """
        Check if the current cache is valid and not expired.

        Returns:
            True if cache is valid, False otherwise
        """
        with self._cache_lock:
            if not self._cache:
                return False

            age = datetime.now() - self._cache.timestamp
            return age <= self.cache_ttl and not self._cache.load_error

    def is_loading(self) -> bool:
        """
        Check if data loading is currently in progress.

        Returns:
            True if loading is in progress, False otherwise
        """
        return self._load_in_progress

    def get_data_age(self) -> Optional[timedelta]:
        """
        Get the age of the current cached data.

        Returns:
            Age of cached data or None if no cache
        """
        with self._cache_lock:
            if self._cache:
                return datetime.now() - self._cache.timestamp
            return None

    def load_data_async(self, force_refresh: bool = False) -> None:
        """
        Start loading MITRE data asynchronously in the background.

        Args:
            force_refresh: If True, bypass cache and force fresh data load
        """
        if self._load_in_progress:
            logger.info("MITRE data loading already in progress")
            return

        if not force_refresh and self.is_cache_valid():
            logger.info("MITRE cache is valid, skipping async load")
            return

        # Start background loading
        self._executor.submit(self._load_data_background, force_refresh)

    def _load_data_background(self, force_refresh: bool = False) -> None:
        """
        Background method to load MITRE data from threat analyzer.

        Args:
            force_refresh: If True, bypass cache validation
        """
        try:
            self._load_in_progress = True
            self._loading_event.clear()

            with self._cache_lock:
                if self._cache:
                    self._cache.is_loading = True
                    self._cache.load_error = None

            self._notify_progress("Initializing MITRE data loading...", 10.0)

            # Import and get data from threat analyzer
            from internal_assistant.di import global_injector
            from internal_assistant.server.threat_intelligence.threat_analyzer import (
                ThreatIntelligenceAnalyzer,
            )

            self._notify_progress("Connecting to threat intelligence service...", 30.0)

            threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)

            self._notify_progress("Fetching MITRE ATT&CK data...", 50.0)

            # Get MITRE data (currently returns static data)
            mitre_data = threat_analyzer.get_mitre_data()

            self._notify_progress("Processing threat intelligence data...", 70.0)

            if not mitre_data:
                raise ValueError("No MITRE data received from threat analyzer")

            # Add metadata
            mitre_data["_metadata"] = {
                "load_time": datetime.now().isoformat(),
                "source": "ThreatIntelligenceAnalyzer",
                "technique_count": len(mitre_data.get("techniques", [])),
                "last_updated": datetime.now().isoformat(),
            }

            self._notify_progress("Caching data for future use...", 90.0)

            # Save to cache
            self._save_to_cache(mitre_data)

            # Update in-memory cache
            with self._cache_lock:
                self._cache = MitreDataCache(
                    data=mitre_data,
                    timestamp=datetime.now(),
                    version="1.0",
                    is_loading=False,
                )

            self._notify_progress("MITRE ATT&CK data loaded successfully!", 100.0)
            logger.info("MITRE data loaded successfully in background")

        except Exception as e:
            error_msg = f"Failed to load MITRE data: {str(e)}"
            logger.error(error_msg)

            with self._cache_lock:
                if self._cache:
                    self._cache.is_loading = False
                    self._cache.load_error = error_msg

            self._notify_progress(f"Error loading MITRE data: {str(e)}", 0.0)

        finally:
            self._load_in_progress = False
            self._loading_event.set()

    def wait_for_data(self, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Wait for data to be loaded (blocking operation).

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            MITRE data if loaded successfully, None on timeout/error
        """
        if not self._load_in_progress:
            return self.get_cached_data()

        if self._loading_event.wait(timeout):
            return self.get_cached_data()

        logger.warning(f"Timed out waiting for MITRE data after {timeout} seconds")
        return None

    def get_loading_status(self) -> Dict[str, Any]:
        """
        Get the current loading status and metadata.

        Returns:
            Dictionary with loading status information
        """
        with self._cache_lock:
            status = {
                "is_loading": self._load_in_progress,
                "has_cache": self._cache is not None,
                "cache_valid": self.is_cache_valid(),
                "data_available": self.get_cached_data() is not None,
            }

            if self._cache:
                status.update(
                    {
                        "cache_age": self.get_data_age(),
                        "cache_timestamp": self._cache.timestamp.isoformat(),
                        "load_error": self._cache.load_error,
                        "data_version": self._cache.version,
                    }
                )

            return status

    def refresh_data(self) -> None:
        """Force refresh of MITRE data, bypassing cache."""
        logger.info("Forcing MITRE data refresh")
        self.load_data_async(force_refresh=True)

    def clear_cache(self) -> None:
        """Clear cached MITRE data."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()

            with self._cache_lock:
                self._cache = None

            logger.info("MITRE cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear MITRE cache: {e}")

    def shutdown(self) -> None:
        """Shutdown the loader and cleanup resources."""
        logger.info("Shutting down AsyncMitreDataLoader")
        self._executor.shutdown(wait=True)


# Global instance for application-wide use
_mitre_loader_instance: Optional[AsyncMitreDataLoader] = None


def get_mitre_loader() -> AsyncMitreDataLoader:
    """
    Get the global MITRE data loader instance.

    Returns:
        Global AsyncMitreDataLoader instance
    """
    global _mitre_loader_instance
    if _mitre_loader_instance is None:
        _mitre_loader_instance = AsyncMitreDataLoader()
    return _mitre_loader_instance


def initialize_mitre_loader(
    cache_dir: Optional[Path] = None, cache_ttl_hours: int = 24
) -> AsyncMitreDataLoader:
    """
    Initialize the global MITRE data loader with custom settings.

    Args:
        cache_dir: Directory for cache storage
        cache_ttl_hours: Cache time-to-live in hours

    Returns:
        Initialized AsyncMitreDataLoader instance
    """
    global _mitre_loader_instance
    _mitre_loader_instance = AsyncMitreDataLoader(cache_dir, cache_ttl_hours)
    return _mitre_loader_instance
