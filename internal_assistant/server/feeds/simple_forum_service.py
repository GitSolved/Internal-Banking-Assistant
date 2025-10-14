"""Simple forum directory service for tor.taxi forums section."""

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SimpleForumDirectoryService:
    """Simple service for extracting forum names and onion links from tor.taxi."""

    TOR_TAXI_URL = "https://tor.taxi/"
    REQUEST_TIMEOUT = 30
    CACHE_DURATION_HOURS = 12

    def __init__(self):
        self.forums_cache: List[Dict[str, str]] = []
        self.last_refresh: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._refresh_lock = asyncio.Lock()

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            headers={"User-Agent": "Internal Assistant Forum Directory/1.0"},
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

    async def fetch_forum_directory(self) -> bool:
        """Fetch and parse forum directory from tor.taxi."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")

        async with self._refresh_lock:
            try:
                logger.info(f"Fetching forum directory from {self.TOR_TAXI_URL}")

                async with self._session.get(self.TOR_TAXI_URL) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to fetch tor.taxi: HTTP {response.status}"
                        )
                        return False

                    html_content = await response.text()

                # Parse forums from HTML
                forums = self._parse_forums_section(html_content)

                self.forums_cache = forums
                self.last_refresh = datetime.now(timezone.utc)

                logger.info(f"Successfully extracted {len(forums)} forum links")
                return True

            except Exception as e:
                logger.error(f"Error fetching forum directory: {e}")
                return False

    def _parse_forums_section(self, html_content: str) -> List[Dict[str, str]]:
        """Parse HTML to extract forum names and onion links."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            forums = []

            # Strategy 1: Look for forums section by heading
            forums_sections = self._find_forums_sections(soup)
            logger.info(f"Found {len(forums_sections)} potential forum sections")

            for i, section in enumerate(forums_sections):
                logger.info(f"Processing forum section {i+1}/{len(forums_sections)}")
                section_forums = self._extract_forums_from_section(section)
                forums.extend(section_forums)
                logger.info(f"Section {i+1} contributed {len(section_forums)} forums")

            logger.info(f"Total forums before deduplication: {len(forums)}")

            # Remove duplicates based on onion_link
            seen_links = set()
            unique_forums = []
            duplicates_removed = 0

            for forum in forums:
                onion_link = forum["onion_link"]
                # Normalize the link for comparison
                normalized_link = (
                    onion_link.lower()
                    .replace("https://", "")
                    .replace("http://", "")
                    .replace("www.", "")
                )

                if normalized_link not in seen_links:
                    seen_links.add(normalized_link)
                    unique_forums.append(forum)
                else:
                    duplicates_removed += 1
                    logger.debug(
                        f"Removed duplicate forum: {forum['name']} -> {forum['onion_link']}"
                    )

            logger.info(f"Removed {duplicates_removed} duplicate forums")
            logger.info(f"Final unique forums count: {len(unique_forums)}")

            # Log all extracted forums for debugging
            if unique_forums:
                logger.info("Successfully extracted forums:")
                for i, forum in enumerate(unique_forums, 1):
                    logger.info(f"  {i}. {forum['name']} -> {forum['onion_link']}")
            else:
                logger.warning("No forums were extracted!")

            return unique_forums

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

    def _find_forums_sections(self, soup: BeautifulSoup) -> List:
        """Find sections containing ONLY forums using surgical targeting."""
        forum_sections = []
        logger.info("Starting surgical forum section detection...")

        # Strategy 1: Look for explicit "Forums" heading and get its content
        forum_headings = soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"], string=re.compile(r"^Forums$", re.I)
        )

        logger.info(f"Found {len(forum_headings)} 'Forums' headings")

        for heading in forum_headings:
            # Get the next sibling container that contains onion links
            for sibling in heading.next_siblings:
                if hasattr(sibling, "name") and sibling.name in [
                    "div",
                    "section",
                    "ul",
                    "ol",
                    "table",
                ]:
                    onion_links = sibling.find_all("a", href=re.compile(r"\.onion"))
                    if onion_links:
                        forum_sections.append(sibling)
                        logger.info(
                            f"Found forums section with {len(onion_links)} onion links"
                        )
                        break

            # Also check parent container if it contains onion links
            parent = heading.parent
            if parent and parent.name in ["div", "section", "article"]:
                onion_links = parent.find_all("a", href=re.compile(r"\.onion"))
                if onion_links:
                    forum_sections.append(parent)
                    logger.info(
                        f"Found forums section in parent with {len(onion_links)} onion links"
                    )

        # Strategy 2: Look for sections with "Forums" in the text and onion links
        if not forum_sections:
            logger.info(
                "No explicit 'Forums' heading found, looking for forum sections..."
            )

            # Find all containers that contain both "forum" text and onion links
            all_containers = soup.find_all(["div", "section", "article", "table"])

            for container in all_containers:
                text = container.get_text().lower()
                onion_links = container.find_all("a", href=re.compile(r"\.onion"))

                # Must contain "forum" and have onion links
                if "forum" in text and onion_links:
                    # Exclude marketplace sections
                    if not any(
                        term in text
                        for term in ["market", "shop", "store", "buy", "sell", "vendor"]
                    ):
                        forum_sections.append(container)
                        logger.info(
                            f"Found forum section with {len(onion_links)} onion links"
                        )

        # Strategy 3: Last resort - look for sections with forum-like names and onion links
        if not forum_sections:
            logger.warning("No forum sections found, using last resort strategy")

            # Look for sections that contain forum names we know about
            known_forum_names = ["dread", "pitch", "germania", "endchan", "xss"]
            all_containers = soup.find_all(["div", "section", "article", "table"])

            for container in all_containers:
                text = container.get_text().lower()
                onion_links = container.find_all("a", href=re.compile(r"\.onion"))

                # Check if it contains known forum names
                has_known_forums = any(name in text for name in known_forum_names)

                if has_known_forums and onion_links:
                    forum_sections.append(container)
                    logger.info(
                        f"Found section with known forums: {len(onion_links)} onion links"
                    )

        # Remove duplicates and nested sections
        unique_sections = []
        for section in forum_sections:
            # Don't add if this section is contained within another section we already have
            is_nested = False
            for existing in unique_sections:
                if section in existing.descendants:
                    is_nested = True
                    break
                elif existing in section.descendants:
                    # Remove the existing one and add this larger one
                    unique_sections.remove(existing)
                    break

            if not is_nested:
                unique_sections.append(section)

        logger.info(f"Final forum sections count: {len(unique_sections)}")
        return unique_sections

    def _section_contains_forums(self, section) -> bool:
        """Check if section likely contains forums."""
        text = section.get_text().lower()

        # Look for forum indicators
        forum_indicators = ["forum", "discussion", "community", "board"]
        has_forum_terms = any(term in text for term in forum_indicators)

        # Must have onion links
        has_onion_links = ".onion" in text

        # Exclude marketplace terms
        market_terms = ["market", "shop", "store", "buy", "sell"]
        has_market_terms = any(term in text for term in market_terms)

        return has_forum_terms and has_onion_links and not has_market_terms

    def _extract_forums_from_section(self, section) -> List[Dict[str, str]]:
        """Extract forum data from a section with comprehensive link detection."""
        forums = []
        logger.debug(
            f"Extracting forums from section: {section.name if hasattr(section, 'name') else 'unknown'}"
        )

        # Strategy 1: Find ALL onion links using regex pattern
        onion_links = section.find_all("a", href=re.compile(r".*\.onion.*", re.I))
        logger.debug(f"Found {len(onion_links)} onion links in section")

        for link in onion_links:
            href = link.get("href", "")
            name = link.get_text(strip=True)

            if not href or not name:
                continue

            # Clean up the link - handle various URL formats
            original_href = href
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith(("http://", "https://")):
                if href.startswith("/"):
                    continue  # Skip relative links
                elif not href.startswith("http"):
                    # Might be just the onion address
                    if ".onion" in href:
                        href = "http://" + href
                    else:
                        continue

            # Clean up the name - remove extra whitespace and special chars
            name = re.sub(r"\s+", " ", name.strip())
            name = name.replace("\n", "").replace("\r", "").replace("\t", " ")

            # Skip very short names or obviously bad names
            if len(name) < 2 or name.lower() in ["link", "url", "here", "click"]:
                logger.debug(f"Skipping short/generic name: '{name}'")
                continue

            # Enhanced safety check - be more permissive for forums
            name_lower = name.lower()

            # Skip only obviously dangerous content
            dangerous_terms = ["drug", "weapon", "hack", "exploit", "card", "fraud"]
            if any(term in name_lower for term in dangerous_terms):
                logger.debug(f"Skipping dangerous content: '{name}'")
                continue

            # STRICT FORUM FILTERING - Only allow known forum names or forum-like terms
            known_forum_names = [
                "dread",
                "pitch",
                "germania",
                "endchan",
                "xss",
                "nz darknet market forum",
            ]
            forum_terms = ["forum", "discussion", "board", "community", "talk", "chat"]

            # Check if it's a known forum name
            is_known_forum = any(
                known_name in name_lower for known_name in known_forum_names
            )

            # Check if it contains forum terms
            has_forum_terms = any(term in name_lower for term in forum_terms)

            # Check for marketplace terms
            marketplace_terms = ["market", "shop", "store", "buy", "sell", "vendor"]
            has_marketplace = any(term in name_lower for term in marketplace_terms)

            # Only allow if:
            # 1. It's a known forum name, OR
            # 2. It has forum terms AND doesn't have marketplace terms
            if not is_known_forum and (not has_forum_terms or has_marketplace):
                logger.debug(
                    f"Skipping non-forum content: '{name}' (known: {is_known_forum}, forum: {has_forum_terms}, market: {has_marketplace})"
                )
                continue

            forum_data = {"name": name, "onion_link": href}
            forums.append(forum_data)
            logger.debug(f"Added forum: '{name}' -> '{href}'")

        # REMOVED: Text pattern extraction to prevent extracting too many forums
        # Only extract properly linked forums to maintain accuracy

        logger.info(f"Extracted {len(forums)} forums from section")
        return forums

    def get_forums(self) -> List[Dict[str, str]]:
        """Get the list of forums."""
        return self.forums_cache.copy()

    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.last_refresh:
            return False

        age = datetime.now(timezone.utc) - self.last_refresh
        return age < timedelta(hours=self.CACHE_DURATION_HOURS)

    async def refresh_if_needed(self) -> bool:
        """Refresh cache if needed."""
        if not self.is_cache_valid():
            return await self.fetch_forum_directory()
        return True

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "total_forums": len(self.forums_cache),
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "cache_valid": self.is_cache_valid(),
            "cache_age_hours": (
                (datetime.now(timezone.utc) - self.last_refresh).total_seconds() / 3600
                if self.last_refresh
                else None
            ),
        }
