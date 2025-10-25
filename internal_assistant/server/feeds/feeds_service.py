"""RSS feed service for External Information functionality."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
import feedparser
from bs4 import BeautifulSoup

from internal_assistant.server.threat_intelligence.threat_analyzer import (
    SecurityRecommendation,
    ThreatIndicator,
    ThreatIntelligenceAnalyzer,
)

logger = logging.getLogger(__name__)


class FeedItem:
    """Represents a single RSS feed item."""

    def __init__(
        self,
        title: str,
        link: str,
        summary: str,
        published: datetime,
        source: str,
        guid: str,
    ):
        self.title = title
        self.link = link
        self.summary = summary
        self.published = published
        self.source = source
        self.guid = guid


class RSSFeedService:
    """Service for managing RSS feeds from regulatory and cyber threat intelligence sources."""

    FEED_SOURCES = {
        # ========================================
        # CYBER THREAT INTELLIGENCE FEEDS
        # ========================================
        # Government Cyber Alerts
        "US-CERT": "https://www.us-cert.gov/ncas/alerts.xml",
        # Security Research & Analysis
        "SANS ISC": "https://isc.sans.edu/rssfeed.xml",
        "NIST NVD": "https://nvd.nist.gov/vuln/data-feeds",
        "CISA KEV": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        # Malware Intelligence
        "ThreatFox": "https://threatfox-api.abuse.ch/export/csv/recent/",
        # ========================================
        # AI RESEARCH & DEVELOPMENT FEEDS
        # ========================================
        "DeepMind": "https://deepmind.com/blog/feed/basic/",
        # ========================================
        # AI SECURITY & ALIGNMENT FEEDS
        # ========================================
        "AI Alignment Forum": "https://www.alignmentforum.org/feed.xml",
        "ML Security": "https://mlanswered.com/feed/",
        # ========================================
        # CYBERSECURITY NEWS FEEDS
        # ========================================
        "The Hacker News": "https://thehackernews.com/feeds/posts/default",
        "Dark Reading": "https://www.darkreading.com/rss.xml",
        "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
        # ========================================
        # REGULATORY & FINANCIAL INFORMATION
        # ========================================
        "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
        "SEC": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom",
        # MITRE ATT&CK Framework (API-based, not RSS)
        # Note: MITRE ATT&CK data is accessed via dedicated API endpoints
    }

    # Enhanced source categories with clear separation
    SOURCE_CATEGORIES = {
        # ========================================
        # AI & MACHINE LEARNING
        # ========================================
        "AI Research": ["DeepMind"],
        "AI Security": ["AI Alignment Forum", "ML Security"],
        # ========================================
        # CYBERSECURITY NEWS
        # ========================================
        "Cybersecurity News": ["The Hacker News", "Dark Reading", "BleepingComputer"],
        # ========================================
        # CYBER THREAT INTELLIGENCE
        # ========================================
        "Government Alerts": ["US-CERT"],
        "Security Research": ["SANS ISC", "NIST NVD", "CISA KEV"],
        "Malware Intelligence": ["ThreatFox"],
        # ========================================
        # REGULATORY & FINANCIAL
        # ========================================
        "Regulatory": ["Federal Reserve", "SEC"],
    }

    # Enhanced priority system with clear separation
    SOURCE_PRIORITY = {
        # ========================================
        # CRITICAL CYBER THREATS (Priority 1)
        # ========================================
        "US-CERT": 1,  # Critical government cyber alerts
        # ========================================
        # HIGH PRIORITY THREATS & AI SECURITY (Priority 2)
        # ========================================
        "AI Alignment Forum": 2,  # AI safety and alignment discussions
        "The Hacker News": 2,  # Breaking cybersecurity news
        # ========================================
        # MEDIUM PRIORITY (Priority 3)
        # ========================================
        "SANS ISC": 3,  # Security research
        "NIST NVD": 3,  # Vulnerability database
        "CISA KEV": 3,  # Known exploited vulnerabilities catalog
        "DeepMind": 3,  # DeepMind research
        "ML Security": 3,  # Machine learning security
        "Dark Reading": 3,  # Cybersecurity news and analysis
        "BleepingComputer": 3,  # Technical cybersecurity news
        # ========================================
        # REGULATORY & FINANCIAL (Priority 4)
        # ========================================
        "Federal Reserve": 4,  # Federal Reserve press releases
        "SEC": 4,  # Securities and Exchange Commission filings
        # ========================================
        # INTELLIGENCE FEEDS (Priority 5)
        # ========================================
        "ThreatFox": 5,  # Malware intelligence
    }

    # Enhanced color scheme with clear visual separation
    SOURCE_COLORS = {
        # ========================================
        # CRITICAL CYBER THREATS - RED
        # ========================================
        "US-CERT": "#FF0000",  # Red for critical cyber alerts
        # ========================================
        # AI RESEARCH - TEAL/GREEN TONES
        # ========================================
        "DeepMind": "#0F9D58",  # DeepMind green
        # ========================================
        # AI SECURITY - PURPLE TONES
        # ========================================
        "AI Alignment Forum": "#9B59B6",  # Purple for AI safety
        "ML Security": "#A569BD",  # Light purple for ML security
        # ========================================
        # CYBERSECURITY NEWS - RED/ORANGE TONES
        # ========================================
        "The Hacker News": "#FF6B35",  # Orange for breaking news
        "Dark Reading": "#C0392B",  # Dark red for analysis
        "BleepingComputer": "#E67E22",  # Orange for technical news
        # ========================================
        # SECURITY RESEARCH - BLUE
        # ========================================
        "SANS ISC": "#0077BE",  # Blue for security research
        "NIST NVD": "#0077BE",  # Blue for vulnerability info
        "CISA KEV": "#0077BE",  # Blue for vulnerability tracking
        # ========================================
        # REGULATORY & FINANCIAL - GOLD/YELLOW
        # ========================================
        "Federal Reserve": "#D4AF37",  # Gold for Federal Reserve
        "SEC": "#FFA500",  # Orange for SEC filings
        # ========================================
        # INTELLIGENCE FEEDS - GREEN
        # ========================================
        "ThreatFox": "#28A745",  # Green for malware intelligence
    }

    # ========================================
    # THREAT INTELLIGENCE SOURCE CLASSIFICATION
    # ========================================
    # Sources that describe ACTIVE ADVERSARY BEHAVIOR suitable for MITRE ATT&CK analysis
    # These feeds contain threat actor TTPs (Tactics, Techniques, Procedures)
    THREAT_INTEL_SOURCES = [
        "US-CERT",  # Government cyber threat alerts with adversary behavior descriptions
        # Future additions:
        # - "CISA Alerts"
        # - "APT Campaign Reports"
        # - "Threat Actor Intelligence"
    ]

    # Sources that are NOT threats (excluded from MITRE ATT&CK Active Threats panel)
    VULNERABILITY_SOURCES = [
        "NIST NVD",  # Vulnerability database
        "CISA KEV",  # Known exploited vulnerabilities
    ]

    REGULATORY_SOURCES = [
        "Federal Reserve",  # Federal Reserve press releases and policy announcements
        "SEC",  # Securities and Exchange Commission filings and enforcement actions
    ]

    INFORMATIONAL_SOURCES = [
        "SANS ISC",  # Security research articles and podcasts
        "ThreatFox",  # Malware indicators (not campaign narratives)
    ]

    def __init__(
        self, max_items: int = 1000
    ):  # Increased for better scrolling and more sources
        self.max_items = max_items
        self.feeds_cache: list[FeedItem] = []
        self.last_refresh: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
        self.threat_analyzer = ThreatIntelligenceAnalyzer()

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._session = None

    async def fetch_feed(self, url: str, source: str) -> list[FeedItem]:
        """Fetch and parse a single RSS feed."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch {source} feed: HTTP {response.status}"
                    )
                    return []

                content = await response.text()

        except TimeoutError:
            logger.warning(f"Timeout fetching {source} feed")
            return []
        except Exception as e:
            logger.error(f"Error fetching {source} feed: {e}")
            return []

        return self._parse_feed_content(content, source)

    def _parse_feed_content(self, content: str, source: str) -> list[FeedItem]:
        """Parse RSS feed content into FeedItem objects."""
        try:
            feed = feedparser.parse(content)
            items = []

            for entry in feed.entries:
                try:
                    # Extract published date - only use valid dates, skip entries without dates
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(
                                *entry.published_parsed[:6], tzinfo=UTC
                            )
                        except (TypeError, ValueError) as e:
                            logger.warning(
                                f"Invalid published_parsed format for {getattr(entry, 'title', 'Unknown')}: {e}"
                            )
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        try:
                            published = datetime(*entry.updated_parsed[:6], tzinfo=UTC)
                        except (TypeError, ValueError) as e:
                            logger.warning(
                                f"Invalid updated_parsed format for {getattr(entry, 'title', 'Unknown')}: {e}"
                            )

                    # Skip entries without valid dates to prevent showing old content as new
                    if published is None:
                        logger.debug(
                            f"Skipping feed entry '{getattr(entry, 'title', 'Unknown')}' - no valid date found"
                        )
                        continue

                    # Clean summary text
                    summary = getattr(entry, "summary", "")
                    if summary:
                        soup = BeautifulSoup(summary, "html.parser")
                        summary = soup.get_text()[:200] + (
                            "..." if len(summary) > 200 else ""
                        )

                    item = FeedItem(
                        title=getattr(entry, "title", "No Title"),
                        link=getattr(entry, "link", ""),
                        summary=summary,
                        published=published,
                        source=source,
                        guid=getattr(entry, "id", ""),
                    )
                    items.append(item)

                except Exception as e:
                    logger.warning(f"Error parsing feed item from {source}: {e}")
                    continue

            return items

        except Exception as e:
            logger.error(f"Error parsing feed content from {source}: {e}")
            return []

    async def refresh_feeds(self) -> bool:
        """Refresh all feeds and analyze for threats."""
        # Create a new session for this refresh to avoid "Connector is closed" errors
        session_created_here = False
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            session_created_here = True

        try:
            # Fetch all feeds concurrently
            tasks = []
            for source, url in self.FEED_SOURCES.items():
                task = self.fetch_feed(url, source)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine all results
            all_items = []
            for result in results:
                if isinstance(result, list):
                    all_items.extend(result)
                else:
                    logger.warning(f"Feed fetch failed: {result}")

            # Sort by priority and limit items
            sorted_items = sorted(
                all_items,
                key=lambda x: (self.SOURCE_PRIORITY.get(x.source, 999), x.published),
                reverse=True,
            )

            self.feeds_cache = sorted_items[: self.max_items]
            self.last_refresh = datetime.now(UTC)

            logger.info(
                f"Refreshed {len(self.feeds_cache)} feed items from {len(self.FEED_SOURCES)} sources"
            )
            return True

        except Exception as e:
            logger.error(f"Error refreshing feeds: {e}")
            return False

        finally:
            # Clean up session if we created it here
            if session_created_here and self._session:
                try:
                    await self._session.close()
                    self._session = None
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")

    def get_feeds(
        self, source_filter: str | None = None, days_filter: int | None = None
    ) -> list[dict[str, Any]]:
        """Get feeds with optional filtering."""
        items = self.feeds_cache

        # Filter by source (skip filtering if "All" is specified)
        if source_filter and source_filter != "All":
            items = [item for item in items if item.source == source_filter]

        # Filter by days
        if days_filter:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_filter)
            items = [item for item in items if item.published >= cutoff_date]

        # Convert to dict format - sort intelligently
        def sort_key(item):
            priority = self.SOURCE_PRIORITY.get(item.source, 999)
            # For regulatory sources (Priority 4), show most recent first
            if priority == 4:  # Regulatory sources (Federal Reserve, SEC)
                return (
                    -item.published.timestamp(),  # Most recent first (primary sort)
                    priority,  # Priority as secondary sort
                )
            else:
                # For cyber threats, priority first, then date
                return (
                    priority,
                    -item.published.timestamp(),
                )

        sorted_items = sorted(items, key=sort_key)

        return [
            {
                "title": item.title,
                "link": item.link,
                "summary": item.summary,
                "published": item.published.isoformat(),
                "source": item.source,
                "guid": item.guid,
                "priority": self.SOURCE_PRIORITY.get(item.source, 999),
                "color": self.SOURCE_COLORS.get(item.source, "#666666"),
                "category": self._get_source_category(item.source),
            }
            for item in sorted_items
        ]

    def _get_source_category(self, source: str) -> str:
        """Get the category for a source."""
        for category, sources in self.SOURCE_CATEGORIES.items():
            if source in sources:
                return category
        return "Other"

    def get_available_sources(self) -> list[str]:
        """Get list of available feed sources."""
        sources = ["All"] + list(self.FEED_SOURCES.keys())
        return sources

    def get_source_categories(self) -> dict[str, list[str]]:
        """Get source categories."""
        return self.SOURCE_CATEGORIES.copy()

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache information."""
        return {
            "total_items": len(self.feeds_cache),
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "sources": list(self.FEED_SOURCES.keys()),
            "categories": self.SOURCE_CATEGORIES,
        }

    def analyze_threats(self) -> list[ThreatIndicator]:
        """Analyze feeds for cyber threats."""
        feed_data = []
        for item in self.feeds_cache:
            feed_data.append(
                {
                    "title": item.title,
                    "summary": item.summary,
                    "source": item.source,
                    "published": item.published,
                }
            )

        return self.threat_analyzer.analyze_feed_content(feed_data)

    def get_security_recommendations(self) -> list[SecurityRecommendation]:
        """Get security recommendations based on threat analysis."""
        threats = self.analyze_threats()
        return self.threat_analyzer.generate_security_recommendations(threats)

    def get_threat_summary(self) -> dict[str, Any]:
        """Get a summary of current threats."""
        threats = self.analyze_threats()
        recommendations = self.get_security_recommendations()

        threat_counts = {}
        for threat in threats:
            threat_type = threat.threat_type.value
            if threat_type not in threat_counts:
                threat_counts[threat_type] = 0
            threat_counts[threat_type] += 1

        return {
            "total_threats": len(threats),
            "threat_counts": threat_counts,
            "recommendations_count": len(recommendations),
            "critical_threats": len(
                [t for t in threats if t.threat_level.value == "critical"]
            ),
            "high_threats": len([t for t in threats if t.threat_level.value == "high"]),
            "banking_specific": len(
                [
                    t
                    for t in threats
                    if any(
                        kw in t.description.lower()
                        for kw in ["bank", "financial", "payment"]
                    )
                ]
            ),
        }

    def add_feed_source(
        self,
        name: str,
        url: str,
        category: str = "Custom",
        priority: int = 5,
        color: str = "#6C757D",
    ) -> bool:
        """Dynamically add a new RSS feed source at runtime."""
        try:
            # Validate URL format
            if not url.startswith(("http://", "https://")):
                raise ValueError("URL must start with http:// or https://")

            # Add to feed sources
            self.FEED_SOURCES[name] = url

            # Add to categories
            if category not in self.SOURCE_CATEGORIES:
                self.SOURCE_CATEGORIES[category] = []
            self.SOURCE_CATEGORIES[category].append(name)

            # Add priority
            self.SOURCE_PRIORITY[name] = priority

            # Add color
            self.SOURCE_COLORS[name] = color

            logger.info(
                f"Added new feed source: {name} ({url}) in category: {category}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add feed source {name}: {e}")
            return False

    def remove_feed_source(self, name: str) -> bool:
        """Remove a feed source at runtime."""
        try:
            # Remove from all dictionaries
            self.FEED_SOURCES.pop(name, None)
            self.SOURCE_PRIORITY.pop(name, None)
            self.SOURCE_COLORS.pop(name, None)

            # Remove from categories
            for category, sources in self.SOURCE_CATEGORIES.items():
                if name in sources:
                    sources.remove(name)
                    # Remove empty categories
                    if not sources:
                        self.SOURCE_CATEGORIES.pop(category, None)
                    break

            logger.info(f"Removed feed source: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove feed source {name}: {e}")
            return False

    def get_feed_health_status(self) -> dict[str, Any]:
        """Get health status of all feed sources."""
        health_status = {
            "total_sources": len(self.FEED_SOURCES),
            "categories": len(self.SOURCE_CATEGORIES),
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "cache_size": len(self.feeds_cache),
            "sources": {},
        }

        # Check each source
        for source_name, url in self.FEED_SOURCES.items():
            source_feeds = [f for f in self.feeds_cache if f.source == source_name]
            health_status["sources"][source_name] = {
                "url": url,
                "category": self._get_source_category(source_name),
                "priority": self.SOURCE_PRIORITY.get(source_name, 5),
                "feed_count": len(source_feeds),
                "latest_feed": (
                    source_feeds[0].published.isoformat() if source_feeds else None
                ),
                "status": "active" if source_feeds else "inactive",
            }

        return health_status
