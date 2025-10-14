"""
Feeds Service Facade

Provides clean abstraction for feeds and external information services
with intelligent caching, background refresh, and data aggregation.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from internal_assistant.server.feeds.feeds_service import RSSFeedService
from .service_facade import ServiceFacade, ServiceHealth

logger = logging.getLogger(__name__)


class FeedsServiceFacade(ServiceFacade[RSSFeedService]):
    """
    Facade for feeds service with enhanced caching, background refresh,
    and intelligent data aggregation.
    """

    def __init__(self, feeds_service: RSSFeedService):
        super().__init__(feeds_service, "feeds_service")
        self._feed_cache: Dict[str, Dict] = {}
        self._last_refresh_times: Dict[str, float] = {}
        self._source_metadata: Dict[str, Dict] = {}

    @ServiceFacade.with_cache(
        ttl=600, key_func=lambda self, source=None, days=None: f"feeds:{source}:{days}"
    )
    @ServiceFacade.with_retry(max_retries=2, base_delay=1.0)
    def get_feeds(
        self, source_filter: Optional[str] = None, days_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get RSS feeds with intelligent caching and filtering.

        Args:
            source_filter: Optional source filter
            days_filter: Optional days filter

        Returns:
            List of feed entries
        """
        try:
            logger.debug(
                f"Fetching feeds - source: {source_filter}, days: {days_filter}"
            )

            feeds = self.service.get_feeds(source_filter, days_filter)

            # Enhance feed data with metadata
            enhanced_feeds = []
            for feed in feeds:
                enhanced_feed = self._enhance_feed_data(feed)
                enhanced_feeds.append(enhanced_feed)

            logger.info(f"Retrieved {len(enhanced_feeds)} feeds")
            return enhanced_feeds

        except Exception as e:
            logger.error(f"Failed to get feeds: {e}")
            return []

    @ServiceFacade.with_cache(ttl=900, key_func=lambda self: "cve_data")
    @ServiceFacade.with_retry(max_retries=2, base_delay=1.0)
    def get_cve_data(self) -> List[Dict[str, Any]]:
        """
        Get CVE data with caching and enhancement.

        Returns:
            List of CVE entries with enhanced metadata
        """
        try:
            logger.debug("Fetching CVE data")

            if hasattr(self.service, "get_cve_data"):
                cve_data = self.service.get_cve_data()
            else:
                # Fallback: extract CVEs from feeds
                feeds = self.get_feeds()
                cve_data = self._extract_cves_from_feeds(feeds)

            # Enhance CVE data
            enhanced_cves = []
            for cve in cve_data:
                enhanced_cve = self._enhance_cve_data(cve)
                enhanced_cves.append(enhanced_cve)

            logger.info(f"Retrieved {len(enhanced_cves)} CVE entries")
            return enhanced_cves

        except Exception as e:
            logger.error(f"Failed to get CVE data: {e}")
            return []

    @ServiceFacade.with_cache(ttl=1800, key_func=lambda self: "mitre_data")
    @ServiceFacade.with_retry(max_retries=2, base_delay=1.0)
    def get_mitre_data(self) -> Dict[str, Any]:
        """
        Get MITRE ATT&CK data with caching.

        Returns:
            Dictionary with MITRE ATT&CK data
        """
        try:
            logger.debug("Fetching MITRE ATT&CK data")

            if hasattr(self.service, "get_mitre_data"):
                mitre_data = self.service.get_mitre_data()
            else:
                # Return empty structure if not available
                mitre_data = {
                    "techniques": [],
                    "tactics": [],
                    "groups": [],
                    "last_updated": None,
                }

            logger.info(
                f"Retrieved MITRE data with {len(mitre_data.get('techniques', []))} techniques"
            )
            return mitre_data

        except Exception as e:
            logger.error(f"Failed to get MITRE data: {e}")
            return {"techniques": [], "tactics": [], "groups": [], "error": str(e)}

    @ServiceFacade.with_cache(ttl=3600, key_func=lambda self: "forum_data")
    @ServiceFacade.with_retry(max_retries=2, base_delay=1.0)
    def get_forum_data(self) -> List[Dict[str, Any]]:
        """
        Get dark web forum directory data with caching.

        Returns:
            List of forum entries
        """
        try:
            logger.debug("Fetching forum directory data")

            if hasattr(self.service, "get_forum_data"):
                forum_data = self.service.get_forum_data()
            else:
                # Return empty list if not available
                forum_data = []

            logger.info(f"Retrieved {len(forum_data)} forum entries")
            return forum_data

        except Exception as e:
            logger.error(f"Failed to get forum data: {e}")
            return []

    @ServiceFacade.with_retry(max_retries=1, base_delay=2.0)
    def refresh_feeds(self, force: bool = False) -> Dict[str, Any]:
        """
        Refresh feeds from external sources.

        Args:
            force: Force refresh even if recently updated

        Returns:
            Refresh status and statistics
        """
        current_time = time.time()
        last_refresh = self._last_refresh_times.get("feeds", 0)

        # Don't refresh more than once every 10 minutes unless forced
        if not force and (current_time - last_refresh) < 600:
            return {
                "status": "skipped",
                "reason": "recently_refreshed",
                "last_refresh": last_refresh,
            }

        try:
            logger.info("Starting feeds refresh")
            start_time = current_time

            # Clear relevant caches
            self._clear_feeds_cache()

            # Trigger refresh if method exists
            if hasattr(self.service, "refresh_feeds"):
                refresh_result = self.service.refresh_feeds()
            else:
                refresh_result = {"status": "not_supported"}

            # Update refresh time
            self._last_refresh_times["feeds"] = current_time

            duration = time.time() - start_time
            logger.info(f"Feeds refresh completed in {duration:.2f}s")

            return {
                "status": "completed",
                "duration": duration,
                "timestamp": current_time,
                "result": refresh_result,
            }

        except Exception as e:
            logger.error(f"Feeds refresh failed: {e}")
            return {"status": "failed", "error": str(e), "timestamp": current_time}

    def get_feed_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive feed statistics.

        Returns:
            Dictionary with feed statistics
        """
        try:
            feeds = self.get_feeds()

            # Analyze feed data
            sources = {}
            total_feeds = len(feeds)
            recent_feeds = 0

            cutoff_time = datetime.now() - timedelta(hours=24)

            for feed in feeds:
                source = feed.get("source", "Unknown")
                if source not in sources:
                    sources[source] = 0
                sources[source] += 1

                # Check if recent
                published = feed.get("published")
                if published and isinstance(published, datetime):
                    if published > cutoff_time:
                        recent_feeds += 1

            return {
                "total_feeds": total_feeds,
                "recent_feeds_24h": recent_feeds,
                "unique_sources": len(sources),
                "source_breakdown": sources,
                "last_refresh": self._last_refresh_times.get("feeds", 0),
                "cache_size": len(self._cache),
            }

        except Exception as e:
            logger.error(f"Failed to get feed statistics: {e}")
            return {"error": str(e)}

    def is_feeds_cache_empty(self) -> bool:
        """
        Check if feeds cache is empty.

        Returns:
            True if cache is empty or expired
        """
        try:
            feeds = self.get_feeds()
            return len(feeds) == 0
        except Exception:
            return True

    def _enhance_feed_data(self, feed: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance feed entry with additional metadata."""
        enhanced_feed = feed.copy()

        # Add threat intelligence categorization
        title = feed.get("title", "").lower()
        content = feed.get("content", "").lower()

        # Categorize threat intelligence
        categories = []
        if any(
            word in title or word in content
            for word in ["malware", "virus", "trojan", "ransomware"]
        ):
            categories.append("malware")
        if any(
            word in title or word in content for word in ["phishing", "scam", "fraud"]
        ):
            categories.append("social_engineering")
        if any(
            word in title or word in content
            for word in ["vulnerability", "cve", "exploit"]
        ):
            categories.append("vulnerability")
        if any(
            word in title or word in content
            for word in ["breach", "hack", "compromise"]
        ):
            categories.append("incident")

        enhanced_feed["threat_categories"] = categories
        enhanced_feed["threat_score"] = len(categories)  # Simple scoring

        return enhanced_feed

    def _enhance_cve_data(self, cve: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance CVE entry with additional analysis."""
        enhanced_cve = cve.copy()

        # Extract CVE severity if not present
        if "severity" not in enhanced_cve:
            enhanced_cve["severity"] = self._determine_cve_severity(
                cve.get("description", "")
            )

        # Add banking/financial relevance score
        description = cve.get("description", "").lower()
        financial_keywords = [
            "bank",
            "financial",
            "payment",
            "credit",
            "transaction",
            "atm",
            "swift",
        ]
        relevance_score = sum(
            1 for keyword in financial_keywords if keyword in description
        )
        enhanced_cve["financial_relevance"] = relevance_score

        return enhanced_cve

    def _extract_cves_from_feeds(self, feeds: List[Dict]) -> List[Dict[str, Any]]:
        """Extract CVE references from feed data."""
        cves = []

        for feed in feeds:
            title = feed.get("title", "")
            content = feed.get("content", "")

            # Simple CVE extraction (could be enhanced with regex)
            if "cve-" in title.lower() or "cve-" in content.lower():
                cve_entry = {
                    "id": self._extract_cve_id(title + " " + content),
                    "source": feed.get("source"),
                    "title": title,
                    "description": content,
                    "published": feed.get("published"),
                    "link": feed.get("link"),
                }
                cves.append(cve_entry)

        return cves

    def _extract_cve_id(self, text: str) -> str:
        """Extract CVE ID from text."""
        import re

        match = re.search(r"CVE-\d{4}-\d{4,7}", text, re.IGNORECASE)
        return match.group(0) if match else "Unknown"

    def _determine_cve_severity(self, text: str) -> str:
        """Determine CVE severity from description text."""
        text_lower = text.lower()

        if any(
            word in text_lower
            for word in [
                "critical",
                "remote code execution",
                "rce",
                "privilege escalation",
            ]
        ):
            return "Critical"
        elif any(
            word in text_lower for word in ["high", "bypass", "injection", "overflow"]
        ):
            return "High"
        elif any(
            word in text_lower
            for word in ["medium", "moderate", "information disclosure"]
        ):
            return "Medium"
        else:
            return "Low"

    def _clear_feeds_cache(self) -> None:
        """Clear feeds-related cache entries."""
        keys_to_remove = [
            key
            for key in self._cache.keys()
            if key.startswith("feeds:")
            or key in ["cve_data", "mitre_data", "forum_data"]
        ]

        with self._lock:
            for key in keys_to_remove:
                if key in self._cache:
                    del self._cache[key]

        logger.info(f"Cleared {len(keys_to_remove)} feeds cache entries")

    def _basic_health_check(self) -> bool:
        """Basic health check for feeds service with timeout and circuit breaker."""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        # Check circuit breaker first
        if self._is_circuit_breaker_open():
            logger.debug(
                f"Health check skipped - circuit breaker open for {self.service_name}"
            )
            return False

        try:
            # Use executor with timeout to prevent network blocking
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="feeds-health-check"
            ) as executor:
                future = executor.submit(self._perform_feeds_check)
                result = future.result(
                    timeout=8
                )  # 8-second timeout for potential network calls
                return result

        except (TimeoutError, Exception) as e:
            logger.warning(f"Feeds service health check failed (timeout/error): {e}")
            if isinstance(e, TimeoutError):
                self._trigger_circuit_breaker()
            return False

    def _perform_feeds_check(self) -> bool:
        """Perform feeds service availability check."""
        try:
            # Lightweight check - get cached feeds if available, don't force refresh
            feeds = self.service.get_feeds(source_filter=None, days_filter=1)
            # Verify we got a valid response
            return isinstance(feeds, (list, dict))
        except Exception:
            return False

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information."""
        base_metrics = self.get_metrics()

        return {
            **base_metrics,
            "service_type": "feeds",
            "last_refresh": self._last_refresh_times.get("feeds", 0),
            "cache_empty": self.is_feeds_cache_empty(),
            "health": self._health.value,
            "capabilities": {
                "rss_feeds": True,
                "cve_tracking": True,
                "mitre_attack": True,
                "forum_directory": True,
                "background_refresh": True,
                "threat_categorization": True,
            },
            "statistics": self.get_feed_statistics(),
        }
