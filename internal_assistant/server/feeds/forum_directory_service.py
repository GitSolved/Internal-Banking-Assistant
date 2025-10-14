"""Forum directory service for managing security forums directory."""

import asyncio
import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from internal_assistant.server.feeds.forum_parser import ForumDirectoryParser, ForumLink
from internal_assistant.settings.settings import Settings

logger = logging.getLogger(__name__)


class ForumDirectoryService:
    """Service for managing comprehensive security forums directory."""

    # Source configuration
    TOR_TAXI_URL = "https://tor.taxi/"
    CACHE_DURATION_HOURS = 12
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 2

    # Clearnet Security Forums Directory
    CLEARNET_FORUMS = {
        "professional": [
            {
                "name": "r/netsec",
                "url": "https://reddit.com/r/netsec",
                "description": "Network security subreddit - 500K+ members",
                "focus_areas": ["research", "news", "technical discussions"],
                "access_type": "clearnet",
                "member_count": "500K+",
                "activity_level": "high",
            },
            {
                "name": "r/cybersecurity",
                "url": "https://reddit.com/r/cybersecurity",
                "description": "General cybersecurity subreddit",
                "focus_areas": ["news", "career advice", "general discussion"],
                "access_type": "clearnet",
                "member_count": "700K+",
                "activity_level": "high",
            },
            {
                "name": "r/AskNetsec",
                "url": "https://reddit.com/r/AskNetsec",
                "description": "Q&A for network security professionals",
                "focus_areas": ["questions", "advice", "troubleshooting"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "high",
            },
            {
                "name": "Security StackExchange",
                "url": "https://security.stackexchange.com",
                "description": "Q&A platform for security professionals",
                "focus_areas": ["technical questions", "best practices", "expert answers"],
                "access_type": "clearnet",
                "member_count": "300K+",
                "activity_level": "high",
            },
            {
                "name": "SANS Forums",
                "url": "https://www.sans.org/forums/",
                "description": "SANS Institute discussion forums",
                "focus_areas": ["training", "certifications", "professional development"],
                "access_type": "clearnet",
                "member_count": "50K+",
                "activity_level": "medium",
            },
            {
                "name": "OWASP Community",
                "url": "https://owasp.org/community/",
                "description": "Open Web Application Security Project forums",
                "focus_areas": ["web security", "application security", "secure coding"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "high",
            },
        ],
        "ctf_training": [
            {
                "name": "HackTheBox Forums",
                "url": "https://forum.hackthebox.com",
                "description": "Community for HTB platform users",
                "focus_areas": ["walkthroughs", "hints", "machine discussions"],
                "access_type": "clearnet",
                "member_count": "500K+",
                "activity_level": "high",
            },
            {
                "name": "TryHackMe Community",
                "url": "https://tryhackme.com/forum",
                "description": "TryHackMe learning platform community",
                "focus_areas": ["guided learning", "hints", "beginner friendly"],
                "access_type": "clearnet",
                "member_count": "1M+",
                "activity_level": "high",
            },
            {
                "name": "PentesterLab Discussions",
                "url": "https://pentesterlab.com/exercises",
                "description": "Hands-on penetration testing exercises",
                "focus_areas": ["web security", "penetration testing", "practice"],
                "access_type": "clearnet",
                "member_count": "50K+",
                "activity_level": "medium",
            },
            {
                "name": "OverTheWire",
                "url": "https://overthewire.org/wargames/",
                "description": "Security wargames and challenges",
                "focus_areas": ["linux", "cryptography", "wargames"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "medium",
            },
            {
                "name": "CTFTime Forums",
                "url": "https://ctftime.org/forums/",
                "description": "CTF event calendar and discussions",
                "focus_areas": ["ctf events", "team formation", "writeups"],
                "access_type": "clearnet",
                "member_count": "50K+",
                "activity_level": "high",
            },
        ],
        "bug_bounty": [
            {
                "name": "HackerOne Community",
                "url": "https://www.hackerone.com/community",
                "description": "Bug bounty platform community",
                "focus_areas": ["vulnerability disclosure", "bug hunting", "rewards"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "high",
            },
            {
                "name": "Bugcrowd Forum",
                "url": "https://forum.bugcrowd.com",
                "description": "Crowdsourced security testing community",
                "focus_areas": ["bug bounty", "vulnerability research", "best practices"],
                "access_type": "clearnet",
                "member_count": "50K+",
                "activity_level": "medium",
            },
            {
                "name": "Intigriti Community",
                "url": "https://www.intigriti.com/community",
                "description": "European bug bounty platform",
                "focus_areas": ["responsible disclosure", "bug hunting", "security research"],
                "access_type": "clearnet",
                "member_count": "30K+",
                "activity_level": "medium",
            },
            {
                "name": "YesWeHack Forum",
                "url": "https://www.yeswehack.com/community",
                "description": "Bug bounty and VDP platform",
                "focus_areas": ["vulnerability disclosure", "ethical hacking", "rewards"],
                "access_type": "clearnet",
                "member_count": "20K+",
                "activity_level": "medium",
            },
        ],
        "specialized": [
            {
                "name": "BleepingComputer Forums",
                "url": "https://www.bleepingcomputer.com/forums/",
                "description": "Malware removal and security help",
                "focus_areas": ["malware analysis", "incident response", "troubleshooting"],
                "access_type": "clearnet",
                "member_count": "500K+",
                "activity_level": "high",
            },
            {
                "name": "MalwareTips",
                "url": "https://malwaretips.com/forums/",
                "description": "Malware prevention and removal",
                "focus_areas": ["malware detection", "antivirus", "security tools"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "high",
            },
            {
                "name": "r/ReverseEngineering",
                "url": "https://reddit.com/r/ReverseEngineering",
                "description": "Reverse engineering community",
                "focus_areas": ["binary analysis", "debugging", "disassembly"],
                "access_type": "clearnet",
                "member_count": "200K+",
                "activity_level": "medium",
            },
            {
                "name": "Tuts4You Forum",
                "url": "https://forum.tuts4you.com",
                "description": "Reverse engineering tutorials and discussion",
                "focus_areas": ["cracking", "unpacking", "code analysis"],
                "access_type": "clearnet",
                "member_count": "50K+",
                "activity_level": "medium",
            },
            {
                "name": "Incident Response Reddit",
                "url": "https://reddit.com/r/blueteamsec",
                "description": "Blue team and incident response",
                "focus_areas": ["threat hunting", "SOC operations", "defensive security"],
                "access_type": "clearnet",
                "member_count": "100K+",
                "activity_level": "high",
            },
        ],
    }

    # Category display names and icons
    CATEGORY_CONFIG = {
        "professional": {
            "display_name": "Professional Security Forums",
            "icon": "🌐",
            "description": "High-quality, moderated security communities"
        },
        "darkweb": {
            "display_name": "Dark Web Research Forums",
            "icon": "🔒",
            "description": "Tor-based forums for threat intelligence (Tor Browser required)"
        },
        "ctf_training": {
            "display_name": "CTF & Training Platforms",
            "icon": "🎯",
            "description": "Hands-on security learning and practice"
        },
        "bug_bounty": {
            "display_name": "Bug Bounty & Disclosure",
            "icon": "💰",
            "description": "Vulnerability research and responsible disclosure"
        },
        "specialized": {
            "display_name": "Specialized Security Topics",
            "icon": "🔬",
            "description": "Malware, reverse engineering, incident response"
        },
    }

    def __init__(self, settings: Optional[Settings] = None, cache_duration_hours: int = 12):
        if settings is None:
            from internal_assistant.settings.settings import unsafe_typed_settings
            settings = unsafe_typed_settings
        self.settings = settings
        self.cache_duration_hours = cache_duration_hours
        self.forums_cache: List[ForumLink] = []  # Tor forums from Tor Taxi
        self.clearnet_forums_cache: List[Dict[str, Any]] = []  # Clearnet forums
        self.last_refresh: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.parser = ForumDirectoryParser()
        self._refresh_lock = asyncio.Lock()
        # Initialize clearnet forums on startup
        self._initialize_clearnet_forums()

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            headers={"User-Agent": "Internal Assistant Forum Directory Service/1.0"},
        )
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

    def _initialize_clearnet_forums(self) -> None:
        """Initialize clearnet forums from the static directory."""
        clearnet_forums = []

        for category, forums in self.CLEARNET_FORUMS.items():
            for forum in forums:
                forum_entry = {
                    **forum,
                    "category": category,
                    "last_verified": datetime.now(timezone.utc).isoformat(),
                }
                clearnet_forums.append(forum_entry)

        self.clearnet_forums_cache = clearnet_forums
        logger.info(f"Initialized {len(clearnet_forums)} clearnet forums across {len(self.CLEARNET_FORUMS)} categories")

    async def fetch_forum_directory(self) -> bool:
        """
        Fetch and parse forum directory from tor.taxi.

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")

        async with self._refresh_lock:
            try:
                logger.info(f"Fetching forum directory from {self.TOR_TAXI_URL}")

                # Attempt to fetch with retries
                for attempt in range(self.MAX_RETRIES + 1):
                    try:
                        async with self._session.get(self.TOR_TAXI_URL) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                break
                            else:
                                logger.warning(
                                    f"HTTP {response.status} from tor.taxi (attempt {attempt + 1})"
                                )

                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Timeout fetching tor.taxi (attempt {attempt + 1})"
                        )

                    except Exception as e:
                        logger.warning(
                            f"Error fetching tor.taxi (attempt {attempt + 1}): {e}"
                        )

                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to fetch tor.taxi after {self.MAX_RETRIES + 1} attempts"
                    )
                    return False

                # Parse the HTML content
                forums = self.parser.parse_forum_directory(html_content)

                # Update cache
                self.forums_cache = forums
                self.last_refresh = datetime.now(timezone.utc)

                logger.info(f"Successfully parsed {len(forums)} forum links")
                return True

            except Exception as e:
                logger.error(f"Error in fetch_forum_directory: {e}")
                return False

    def get_forums(
        self,
        category_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get forums with optional filtering (includes both clearnet and darkweb).

        Args:
            category_filter: Filter by category ("all", "professional", "darkweb", "ctf_training", "bug_bounty", "specialized")
            search_query: Search in forum names and descriptions
            limit: Maximum number of results

        Returns:
            List of forum dictionaries
        """
        all_forums = []

        # Add clearnet forums
        if not category_filter or category_filter.lower() in ["all", "professional", "ctf_training", "bug_bounty", "specialized"]:
            for forum in self.clearnet_forums_cache:
                if not category_filter or category_filter.lower() == "all" or forum["category"] == category_filter.lower():
                    all_forums.append(forum)

        # Add darkweb forums from Tor Taxi (only if enabled in settings)
        if (
            self.settings.forum_directory
            and self.settings.forum_directory.access_types
            and self.settings.forum_directory.access_types.darkweb
        ):
            if not category_filter or category_filter.lower() in ["all", "darkweb"]:
                for forum in self.forums_cache:
                    forum_dict = {
                        **forum.to_dict(),
                        "category": "darkweb",
                        "access_type": "tor",
                        "last_verified": (
                            self.last_refresh.isoformat() if self.last_refresh else None
                        ),
                    }
                    all_forums.append(forum_dict)

        # Apply search filter
        if search_query:
            query_lower = search_query.lower()
            all_forums = [
                f
                for f in all_forums
                if query_lower in f.get("name", "").lower()
                or query_lower in f.get("description", "").lower()
            ]

        # Apply limit
        if limit and limit > 0:
            all_forums = all_forums[:limit]

        # Add IDs for UI reference
        for i, forum in enumerate(all_forums):
            forum["id"] = f"forum_{i}"

        return all_forums

    def get_forum_categories(self) -> Dict[str, int]:
        """Get available forum categories with counts."""
        categories = {}
        for forum in self.forums_cache:
            categories[forum.category] = categories.get(forum.category, 0) + 1
        return categories

    def is_cache_valid(self) -> bool:
        """Check if the current cache is still valid."""
        if not self.last_refresh or not self.forums_cache:
            return False

        cache_age = datetime.now(timezone.utc) - self.last_refresh
        return cache_age < timedelta(hours=self.cache_duration_hours)

    async def refresh_if_needed(self) -> bool:
        """Refresh the forum directory if cache is invalid."""
        if not self.is_cache_valid():
            return await self.fetch_forum_directory()
        return True

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache status information."""
        cache_age_hours = None
        if self.last_refresh:
            cache_age = datetime.now(timezone.utc) - self.last_refresh
            cache_age_hours = cache_age.total_seconds() / 3600

        return {
            "total_forums": len(self.forums_cache),
            "categories": len(self.get_forum_categories()),
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "cache_age_hours": cache_age_hours,
            "cache_valid": self.is_cache_valid(),
            "source_url": self.TOR_TAXI_URL,
            "cache_duration_hours": self.cache_duration_hours,
        }

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        parsing_stats = self.parser.get_parsing_stats() if self.forums_cache else {}

        return {
            "service": "forum_directory",
            "status": "active" if self.forums_cache else "empty",
            "cache_info": self.get_cache_info(),
            "categories": self.get_forum_categories(),
            "parsing_stats": parsing_stats,
            "safety_features": {
                "content_filtering": True,
                "forums_only": True,
                "excluded_keywords": list(self.parser.EXCLUDED_KEYWORDS),
                "required_indicators": list(self.parser.FORUM_INDICATORS),
            },
        }

    def search_forums(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search forums by name, description, or category.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of matching forum dictionaries with relevance scores
        """
        if not query or not self.forums_cache:
            return []

        query_lower = query.lower()
        results = []

        for forum in self.forums_cache:
            relevance_score = 0

            # Exact name match gets highest score
            if query_lower == forum.name.lower():
                relevance_score = 100
            # Name contains query
            elif query_lower in forum.name.lower():
                relevance_score = 80
            # Description contains query
            elif query_lower in forum.description.lower():
                relevance_score = 60
            # Category contains query
            elif query_lower in forum.category.lower():
                relevance_score = 40

            if relevance_score > 0:
                forum_dict = forum.to_dict()
                forum_dict["relevance_score"] = relevance_score
                forum_dict["last_updated"] = (
                    self.last_refresh.isoformat() if self.last_refresh else None
                )
                results.append(forum_dict)

        # Sort by relevance score (descending) and return top results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:max_results]

    def get_forum_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get forum information by URL."""
        for forum in self.forums_cache:
            if forum.url == url:
                return forum.to_dict()
        return None

    def export_forum_list(self, format: str = "json", category_filter: Optional[str] = None) -> str:
        """
        Export forum directory to various formats.

        Args:
            format: Export format ("json", "csv", "markdown")
            category_filter: Optional category filter

        Returns:
            Exported data as string
        """
        forums = self.get_forums(category_filter=category_filter)

        if format == "json":
            return json.dumps(forums, indent=2)

        elif format == "csv":
            output = io.StringIO()
            if forums:
                fieldnames = ["name", "url", "description", "category", "access_type", "member_count", "activity_level"]
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(forums)
            return output.getvalue()

        elif format == "markdown":
            md_lines = ["# Security Forums & Communities Directory\n"]
            md_lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

            # Group by category
            categories = {}
            for forum in forums:
                cat = forum.get("category", "other")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(forum)

            # Export each category
            for category, cat_forums in categories.items():
                config = self.CATEGORY_CONFIG.get(category, {})
                display_name = config.get("display_name", category.title())
                icon = config.get("icon", "📌")

                md_lines.append(f"\n## {icon} {display_name}\n")

                for forum in cat_forums:
                    name = forum.get("name", "Unknown")
                    url = forum.get("url", "")
                    desc = forum.get("description", "")
                    access = forum.get("access_type", "clearnet")

                    access_badge = "🔒 Tor Required" if access == "tor" else "🌐 Clearnet"
                    md_lines.append(f"### {name}")
                    md_lines.append(f"**{access_badge}** | {url}\n")
                    md_lines.append(f"{desc}\n")

            return "\n".join(md_lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the service."""
        try:
            # Check if we can reach tor.taxi
            can_reach_source = False
            if self._session:
                try:
                    async with self._session.get(
                        self.TOR_TAXI_URL, timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        can_reach_source = response.status == 200
                except:
                    pass

            return {
                "service_healthy": True,
                "cache_valid": self.is_cache_valid(),
                "source_reachable": can_reach_source,
                "forums_count": len(self.forums_cache),
                "last_refresh": (
                    self.last_refresh.isoformat() if self.last_refresh else None
                ),
                "error": None,
            }

        except Exception as e:
            return {
                "service_healthy": False,
                "cache_valid": False,
                "source_reachable": False,
                "forums_count": 0,
                "last_refresh": None,
                "error": str(e),
            }
