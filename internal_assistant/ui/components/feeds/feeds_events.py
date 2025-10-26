"""Feeds Event Handlers

This module contains all event handlers for RSS feeds and threat intelligence components.
Extracted from ui.py as part of Phase 1 refactoring to decouple event handling
from UI construction.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from internal_assistant.server.feeds.feeds_service import RSSFeedService

logger = logging.getLogger(__name__)


class FeedsEventHandler:
    """Handles all feed-related events including RSS feed refresh, filtering,
    and threat intelligence updates.
    """

    def __init__(self, feeds_service: RSSFeedService, display_utility=None):
        """Initialize feeds event handler with required services.

        Args:
            feeds_service: Service for RSS feed operations
            display_utility: DisplayUtilityBuilder for formatting CVE data
        """
        self.feeds_service = feeds_service
        self.display_utility = display_utility

    async def refresh_feeds(self) -> tuple[str, str]:
        """Refresh RSS feeds and update display.
        Extracted from ui.py lines 5907-5971 (~62 lines).

        Returns:
            Tuple of (status_message, HTML string with updated feed content)
        """
        try:
            logger.info("Starting RSS feed refresh...")

            # Refresh feed data using async context manager
            async with self.feeds_service as service:
                success = await service.refresh_feeds()

                if not success:
                    error_html = """
                    <div class="no-feeds-message">
                        <h3>📡 No RSS Feeds Available</h3>
                        <p>No RSS feeds are currently configured or accessible.</p>
                        <p><strong>Possible reasons:</strong></p>
                        <ul>
                            <li>Feed sources are temporarily unavailable</li>
                            <li>Network connectivity issues</li>
                            <li>Feed URLs need to be reconfigured</li>
                        </ul>
                        <p><em>Try refreshing again in a few minutes.</em></p>
                    </div>
                    """
                    return "Failed to refresh feeds", error_html

                # Get the refreshed feeds
                feeds = service.get_feeds()

            if not feeds:
                empty_html = """
                <div class="no-feeds-message">
                    <h3>📡 No RSS Feeds Available</h3>
                    <p>No RSS feeds are currently configured or accessible.</p>
                </div>
                """
                return "No feeds available", empty_html

            # Process and format feed data
            feed_html = self._format_feeds_html(feeds)

            status_msg = f"✅ Successfully refreshed {len(feeds)} RSS feeds"
            logger.info(status_msg)
            return status_msg, feed_html

        except Exception as e:
            error_msg = f"Failed to refresh RSS feeds: {e!s}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ RSS Feed Refresh Failed</h3>
                <p><strong>Error:</strong> {e!s}</p>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check your internet connection</li>
                    <li>Verify feed URLs are accessible</li>
                    <li>Try refreshing again in a few minutes</li>
                </ul>
            </div>
            """
            return f"❌ Error: {e!s}", error_html

    def filter_cve(self, time_filter: str, cve_content: str) -> tuple[str, str, str]:
        """Filter CVE data by time period.

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)
            cve_content: Current CVE HTML content

        Returns:
            Tuple of (time_range_display_html, current_filter_state, filtered_cve_html)
        """
        try:
            logger.info(f"Filtering CVE data with time_filter={time_filter}")

            # Map time filter to days
            filter_days_map = {
                "24h": 1,
                "7d": 7,
                "30d": 30,
                "90d": 90,
            }
            days = filter_days_map.get(time_filter, 30)

            # Create time range display HTML
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "30 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

            logger.info(f"Created CVE time_range_html for {display_text}")

            # Get filtered CVE data
            filtered_cve_html = self.display_utility.format_cve_display(
                None, "All Severities", "All Vendors", days
            )

            logger.info(f"CVE filtering complete: {len(filtered_cve_html)} chars")

            return (time_range_html, display_text, filtered_cve_html)

        except Exception as e:
            logger.error(f"Error in filter_cve: {e}", exc_info=True)
            error_html = f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error filtering CVE data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{e!s}</div>
                </div>
            </div>"""
            return (
                "<div style='color: #d32f2f;'>⚠️ Filter Error</div>",
                "30 days",
                error_html,
            )

    def filter_feeds(
        self, time_filter: str, feeds_content: str
    ) -> tuple[str, str, str]:
        """Filter feeds by time period.
        Extracted from ui.py lines 5923-5961 (~38 lines).

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)
            feeds_content: Current feeds HTML content

        Returns:
            Tuple of (time_range_display_html, current_filter_state, filtered_feeds_html)
        """
        try:
            logger.info(f"Filtering feeds with time_filter={time_filter}")

            # Create time range display HTML
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "30 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

            logger.info(f"Created time_range_html: {time_range_html[:100]}")

            if not feeds_content or feeds_content.strip() == "":
                return (
                    time_range_html,
                    display_text,
                    "No feeds to filter. Please refresh feeds first.",
                )

            # Parse time filter
            filter_hours = self._parse_time_filter(time_filter)
            if filter_hours is None:
                return time_range_html, display_text, "Invalid time filter specified."

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(hours=filter_hours)

            # Actually filter the feeds by re-fetching and filtering
            feeds = self.feeds_service.get_feeds()
            if not feeds:
                return (
                    time_range_html,
                    display_text,
                    "<div class='no-content'>No feeds available to filter</div>",
                )

            # Filter feeds by publication date
            filtered_feeds = [
                feed
                for feed in feeds
                if self._is_feed_within_timeframe(feed, cutoff_date)
            ]

            if not filtered_feeds:
                empty_html = f"""
                <div class="no-feeds-message">
                    <h3>📅 No Feeds Found</h3>
                    <p>No feeds found for the last {display_text}.</p>
                    <p><em>Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}</em></p>
                </div>
                """
                return time_range_html, display_text, empty_html

            # Format filtered feeds
            filtered_html = f"""
            <div class="filtered-feeds">
                <div class="filter-info">
                    <h3>📅 Feeds filtered for last {display_text}</h3>
                    <p><em>Showing {len(filtered_feeds)} items newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}</em></p>
                </div>
                {self._format_feeds_html(filtered_feeds)}
            </div>
            """

            logger.info(
                f"Applied {time_filter} filter to feeds: {len(filtered_feeds)} items"
            )
            return time_range_html, display_text, filtered_html

        except Exception as e:
            error_msg = f"Failed to filter feeds: {e!s}"
            logger.error(error_msg)
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "30 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"
            return (
                time_range_html,
                display_text,
                f"<div class='error-message'>Filter error: {e!s}</div>",
            )

    def _is_feed_within_timeframe(
        self, feed: dict[str, Any], cutoff_date: datetime
    ) -> bool:
        """Check if feed is within the specified timeframe.

        Args:
            feed: Feed item dictionary
            cutoff_date: Cutoff datetime for filtering

        Returns:
            True if feed is newer than cutoff_date
        """
        try:
            published = feed.get("published")
            if not published:
                return True  # Include items without dates

            # Handle both string and datetime objects
            if isinstance(published, str):
                # Try ISO format first (from feeds_service.py get_feeds())
                try:
                    pub_date = datetime.fromisoformat(published)
                    # Make cutoff_date timezone-aware if pub_date is
                    if pub_date.tzinfo is not None and cutoff_date.tzinfo is None:

                        cutoff_date = cutoff_date.replace(tzinfo=UTC)
                    return pub_date >= cutoff_date
                except (ValueError, AttributeError):
                    pass

                # Try parsing other common date formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%a, %d %b %Y %H:%M:%S %Z",
                ]:
                    try:
                        pub_date = datetime.strptime(published, fmt)
                        return pub_date >= cutoff_date
                    except ValueError:
                        continue
                # If no format worked, include the item
                return True
            elif isinstance(published, datetime):
                return published >= cutoff_date
            else:
                return True
        except Exception as e:
            logger.warning(f"Error checking feed timeframe: {e}")
            return True  # Include items that cause errors

    def _parse_time_filter(self, time_filter: str) -> int | None:
        """Parse time filter string to hours.

        Args:
            time_filter: Time filter (24h, 7d, 30d, 90d)

        Returns:
            Hours as integer, or None if invalid
        """
        filter_map = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30, "90d": 24 * 90}
        return filter_map.get(time_filter.lower())

    def _get_sources_for_category(self, category: str) -> list[str] | None:
        """Map category buttons to feed sources.

        Args:
            category: Category name (e.g., "Banking Regulation", "Cybersecurity")

        Returns:
            List of source names for the category, or None for "All Sources"
        """
        category_map = {
            "All Sources": None,  # No filter = all sources
            "Banking Regulation": ["FDIC", "OCC", "Federal Reserve"],
            "Cybersecurity": [
                "US-CERT",
                "SANS ISC",
                "NIST NVD",
                "CISA KEV",
                "The Hacker News",
                "Dark Reading",
                "BleepingComputer",
                "ThreatFox",
            ],
            "AML/BSA": ["FinCEN"],
            "Securities": ["SEC", "FINRA"],
            "Consumer Protection": ["CFPB"],
            "State Regulators": ["NY DFS"],
            "International": ["Basel Committee"],
            "AI Security": ["AI Alignment Forum", "ML Security"],
            "AI Research": ["DeepMind"],
        }

        return category_map.get(category)

    def filter_by_category(self, category: str) -> str:
        """Filter feeds by source category with fixed 30-day window.

        Args:
            category: Category name (e.g., "Banking Regulation", "Cybersecurity")

        Returns:
            Combined HTML string with status header and filtered feeds
        """
        try:
            logger.info(f"Filtering feeds by category: {category}")

            sources = self._get_sources_for_category(category)

            # Fixed 30-day window for all category views
            days_filter = 30

            # Get feeds with days filter
            all_feeds = self.feeds_service.get_feeds(None, days_filter)

            # Filter by sources if category specifies sources
            if sources:
                feeds = [f for f in all_feeds if f["source"] in sources]
            else:
                # "All Sources" - no source filtering
                feeds = all_feeds

            # Format display with status header
            status_header = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 12px; margin-top: 8px; padding: 8px; background-color: #f0f8ff; border-radius: 4px;'>📊 SHOWING: {category} ({len(feeds)} items, last 30 days)</div>"

            feeds_html = self._format_feeds_html(feeds)

            combined_html = status_header + feeds_html

            logger.info(
                f"Category filter applied: {category} -> {len(feeds)} items from {len(sources) if sources else 'all'} sources"
            )

            return combined_html

        except Exception as e:
            error_msg = f"Failed to filter by category: {e!s}"
            logger.error(error_msg, exc_info=True)

            error_html = f"""
            <div class="error-message" style="padding: 20px; background-color: #ffebee; border-left: 4px solid #d32f2f; margin: 10px 0;">
                <h3 style="color: #c62828; margin: 0 0 10px 0;">⚠️ Category Filter Failed</h3>
                <p><strong>Error:</strong> {e!s}</p>
            </div>
            """

            return error_html

    def _format_feeds_html(self, feeds: list[dict[str, Any]]) -> str:
        """Format feeds data into HTML.

        Args:
            feeds: List of feed data dictionaries from RSSFeedService.get_feeds()

        Returns:
            Formatted HTML string
        """
        if not feeds:
            return "<div class='no-content'>No feed items available</div>"

        html_parts = ["<div class='feeds-container'>"]

        for feed in feeds[:50]:  # Limit to 50 items for performance
            title = feed.get("title", "Untitled")
            summary = feed.get("summary", "")
            link = feed.get("link", "#")
            pub_date = feed.get("published", "Unknown date")
            source = feed.get("source", "Unknown source")
            priority = feed.get("priority", 999)
            color = feed.get("color", "#666666")

            # Format priority badge
            priority_badge = f"<span style='background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;'>Priority {priority}</span>"

            html_parts.append(
                f"""
            <div class='feed-item' style='border-left: 4px solid {color}; padding-left: 12px; margin-bottom: 16px;'>
                <h4><a href='{link}' target='_blank' style='color: #0066cc;'>{title}</a></h4>
                <p class='feed-meta' style='color: #666; font-size: 0.9em; margin: 4px 0;'>
                    <strong>Source:</strong> {source} {priority_badge} |
                    <strong>Published:</strong> {pub_date}
                </p>
                <p class='feed-description' style='margin-top: 8px;'>{summary}</p>
            </div>
            """
            )

        html_parts.append("</div>")
        return "".join(html_parts)

    async def refresh_cve_data(self) -> tuple[str, str]:
        """Refresh CVE (Common Vulnerabilities and Exposures) data.
        Automatically shows last 7 days of CVE data (filtered by time).

        Returns:
            Tuple of (status_message, HTML string with updated CVE content)
        """
        try:
            logger.info("Starting CVE data refresh with 7-day filter...")

            # Refresh feeds first
            async with self.feeds_service as service:
                success = await service.refresh_feeds()
                if not success:
                    error_html = """
                    <div class="no-feeds-message">
                        <h3>🔒 CVE Data Unavailable</h3>
                        <p>Unable to fetch CVE/vulnerability data from feeds.</p>
                        <p>Please try refreshing again.</p>
                    </div>
                    """
                    return "Failed to fetch CVE data", error_html

            # Use display_utility to format CVE data with 7-day filter
            cve_html = self.display_utility.format_cve_display(
                None,  # source_filter
                "All Severities",  # severity_filter
                "All Vendors",  # vendor_filter
                7,  # days_filter = 7 days
            )

            status_msg = "✅ CVE data refreshed (showing last 7 days)"
            logger.info("CVE data refresh completed with 7-day filter")
            return status_msg, cve_html

        except Exception as e:
            error_msg = f"Failed to refresh CVE data: {e!s}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ CVE Data Refresh Failed</h3>
                <p><strong>Error:</strong> {e!s}</p>
                <p>Please try again later or check your network connection.</p>
            </div>
            """
            return f"❌ Error: {e!s}", error_html

    async def refresh_and_filter_feeds(
        self, time_filter: str
    ) -> tuple[str, str, str, str]:
        """Refresh RSS feeds from source and filter by time period.
        Combines refresh and filter operations for time filter buttons.

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)

        Returns:
            Tuple of (status_message, time_range_display_html, filter_state, filtered_html)
        """
        try:
            logger.info(
                f"Refreshing and filtering feeds with time_filter={time_filter}"
            )

            # First refresh feeds from source
            async with self.feeds_service as service:
                success = await service.refresh_feeds()
                if not success:
                    filter_display_map = {
                        "24h": "24 hours",
                        "7d": "7 days",
                        "30d": "30 days",
                        "90d": "90 days",
                    }
                    display_text = filter_display_map.get(time_filter, "7 days")
                    time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

                    error_html = """
                    <div class="no-feeds-message">
                        <h3>📡 Unable to Refresh Feeds</h3>
                        <p>Feed sources are currently unavailable.</p>
                        <p><em>Try again in a few minutes.</em></p>
                    </div>
                    """
                    return (
                        "Failed to refresh feeds",
                        time_range_html,
                        display_text,
                        error_html,
                    )

            # Now filter the refreshed data by time
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "7 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

            # Parse time filter to hours
            filter_hours = self._parse_time_filter(time_filter)
            if filter_hours is None:
                return (
                    "Invalid time filter",
                    time_range_html,
                    display_text,
                    "Invalid time filter specified.",
                )

            # Calculate cutoff date and filter feeds
            cutoff_date = datetime.now() - timedelta(hours=filter_hours)
            feeds = self.feeds_service.get_feeds()

            if not feeds:
                return (
                    "No feeds available",
                    time_range_html,
                    display_text,
                    "<div class='no-content'>No feeds available</div>",
                )

            filtered_feeds = [
                feed
                for feed in feeds
                if self._is_feed_within_timeframe(feed, cutoff_date)
            ]

            if not filtered_feeds:
                empty_html = f"""
                <div class="no-feeds-message">
                    <h3>📅 No Feeds Found</h3>
                    <p>No feeds found for the last {display_text}.</p>
                </div>
                """
                return (
                    f"No feeds in last {display_text}",
                    time_range_html,
                    display_text,
                    empty_html,
                )

            filtered_html = self._format_feeds_html(filtered_feeds)
            status_msg = f"✅ Refreshed {len(filtered_feeds)} feeds ({display_text})"
            logger.info(status_msg)
            return status_msg, time_range_html, display_text, filtered_html

        except Exception as e:
            logger.error(f"Error in refresh_and_filter_feeds: {e}", exc_info=True)
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "7 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"
            error_html = f"<div class='error-message'>Error: {e!s}</div>"
            return f"❌ Error: {e!s}", time_range_html, display_text, error_html

    async def refresh_and_filter_cve(
        self, time_filter: str
    ) -> tuple[str, str, str, str]:
        """Refresh CVE data from source and filter by time period.
        Combines refresh and filter operations for CVE time filter buttons.

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)

        Returns:
            Tuple of (status_message, time_range_display_html, filter_state, filtered_html)
        """
        try:
            logger.info(
                f"Refreshing and filtering CVE data with time_filter={time_filter}"
            )

            # First refresh feeds from source (CVE data comes from feeds)
            async with self.feeds_service as service:
                success = await service.refresh_feeds()
                if not success:
                    filter_display_map = {
                        "24h": "24 hours",
                        "7d": "7 days",
                        "30d": "30 days",
                        "90d": "90 days",
                    }
                    display_text = filter_display_map.get(time_filter, "7 days")
                    time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

                    error_html = """
                    <div class="no-feeds-message">
                        <h3>🔒 Unable to Refresh CVE Data</h3>
                        <p>Unable to fetch vulnerability data from feeds.</p>
                        <p><em>Try again in a few minutes.</em></p>
                    </div>
                    """
                    return (
                        "Failed to refresh CVE data",
                        time_range_html,
                        display_text,
                        error_html,
                    )

            # Map time filter to days for CVE filtering
            filter_days_map = {
                "24h": 1,
                "7d": 7,
                "30d": 30,
                "90d": 90,
            }
            days = filter_days_map.get(time_filter, 7)

            # Create display HTML
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "7 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"

            # Format CVE data with time filter
            cve_html = self.display_utility.format_cve_display(
                None, "All Severities", "All Vendors", days
            )

            status_msg = f"✅ Refreshed CVE data ({display_text})"
            logger.info(status_msg)
            return status_msg, time_range_html, display_text, cve_html

        except Exception as e:
            logger.error(f"Error in refresh_and_filter_cve: {e}", exc_info=True)
            filter_display_map = {
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            display_text = filter_display_map.get(time_filter, "7 days")
            time_range_html = f"<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: {display_text}</div>"
            error_html = f"<div class='error-message'>Error: {e!s}</div>"
            return f"❌ Error: {e!s}", time_range_html, display_text, error_html

    async def refresh_mitre_data(self) -> tuple[str, str]:
        """Refresh MITRE ATT&CK framework data from official API.
        Fetches actual techniques, tactics, and threat groups from MITRE ATT&CK.

        Returns:
            Tuple of (status_message, HTML string with updated MITRE content)
        """
        try:
            logger.info("Starting MITRE ATT&CK data refresh...")

            # Import the dedicated MITRE ATT&CK service
            from internal_assistant.server.threat_intelligence.mitre_attack_service import (
                MitreAttackService,
            )

            # Use the actual MITRE ATT&CK API
            async with MitreAttackService() as mitre_service:
                success = await mitre_service.refresh_data()

                if not success:
                    # Try to use cached data
                    cache_info = mitre_service.get_cache_info()
                    if cache_info.get("techniques_count", 0) > 0:
                        logger.info("Using cached MITRE data after refresh failure")
                        mitre_html = self._format_mitre_attack_data(mitre_service)
                        return (
                            "⚠️ Using cached MITRE data (refresh failed)",
                            mitre_html,
                        )

                    error_html = """
                    <div class="no-feeds-message">
                        <h3>🎯 MITRE ATT&CK API Unavailable</h3>
                        <p>Unable to fetch MITRE ATT&CK framework data from API</p>
                        <p><strong>Possible reasons:</strong></p>
                        <ul>
                            <li>MITRE ATT&CK API is temporarily down</li>
                            <li>Network connectivity issues</li>
                            <li>API rate limiting</li>
                        </ul>
                        <p><em>Try refreshing again in a few minutes.</em></p>
                    </div>
                    """
                    return "Failed to fetch MITRE data", error_html

                # Format MITRE data using dedicated formatter
                mitre_html = self._format_mitre_attack_data(mitre_service)

                cache_info = mitre_service.get_cache_info()
                status_msg = f"✅ MITRE ATT&CK: {cache_info['techniques_count']} techniques, {cache_info['tactics_count']} tactics, {cache_info['groups_count']} threat groups"
                logger.info(f"MITRE refresh completed: {cache_info}")
                return status_msg, mitre_html

        except Exception as e:
            error_msg = f"Failed to refresh MITRE data: {e!s}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ MITRE ATT&CK Refresh Failed</h3>
                <p><strong>Error:</strong> {e!s}</p>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check your internet connection</li>
                    <li>Verify MITRE ATT&CK API is accessible</li>
                    <li>Try refreshing again in a few minutes</li>
                </ul>
            </div>
            """
            return f"❌ Error: {e!s}", error_html

    def _format_mitre_attack_data(
        self, mitre_service, sector: str = "Financial"
    ) -> str:
        """Format MITRE ATT&CK data into HTML.

        Args:
            mitre_service: MitreAttackService instance with loaded data
            sector: Sector name for filtering (Financial, Government, Healthcare, Energy, Technology, Retail, Manufacturing)

        Returns:
            Formatted HTML string with MITRE framework data
        """
        cache_info = mitre_service.get_cache_info()

        # Get sector-relevant data with sector parameter
        sector_techniques = mitre_service.get_sector_relevant_techniques(sector)
        sector_groups = mitre_service.get_sector_threat_groups(sector)

        html_parts = [
            f"""
        <div class="mitre-attack-container">
            <div class="mitre-header">
                <h3>🎯 MITRE ATT&CK Framework Data</h3>
                <p><strong>Total Techniques:</strong> {cache_info['techniques_count']} |
                   <strong>Tactics:</strong> {cache_info['tactics_count']} |
                   <strong>Threat Groups:</strong> {cache_info['groups_count']}</p>
                <p><strong>Sector-Relevant:</strong> {len(sector_techniques)} techniques | {len(sector_groups)} threat groups</p>
            </div>
        """
        ]

        # Display sector-relevant threat groups
        if sector_groups:
            html_parts.append(
                """
            <div class="mitre-section">
                <h4 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 8px; margin-top: 20px;">
                    🚨 High-Priority Threat Groups (Targeting Banking/Financial Sector)
                </h4>
            """
            )

            for group in sector_groups[:10]:  # Show top 10
                aliases_str = ", ".join(group.aliases[:3]) if group.aliases else "None"
                techniques_count = len(group.techniques) if group.techniques else 0

                html_parts.append(
                    f"""
                <div class="threat-group" style="border-left: 4px solid #d32f2f; padding-left: 12px; margin-bottom: 16px; background-color: #ffebee; padding: 12px; border-radius: 4px;">
                    <h5 style="margin: 0 0 8px 0; color: #b71c1c;">
                        <span style="color: #d32f2f;">🎯</span> {group.name}
                    </h5>
                    <p style="margin: 4px 0 8px 0; color: #666; font-size: 0.9em;">
                        {group.description[:200]}{"..." if len(group.description) > 200 else ""}
                    </p>
                    <div class="group-meta" style="font-size: 0.85em; color: #999;">
                        <strong>Aliases:</strong> {aliases_str} |
                        <strong>Known Techniques:</strong> {techniques_count} |
                        <a href="{group.url}" target="_blank" style="color: #0066cc;">View Details</a>
                    </div>
                </div>
                """
                )

            html_parts.append("</div>")

        # Display sector-relevant techniques (sample)
        if sector_techniques:
            html_parts.append(
                """
            <div class="mitre-section">
                <h4 style="color: #FF6B35; border-bottom: 2px solid #FF6B35; padding-bottom: 8px; margin-top: 20px;">
                    ⚠️ Key Techniques to Monitor
                </h4>
            """
            )

            for technique in sector_techniques[:15]:  # Show top 15
                platforms_str = (
                    ", ".join(technique.platforms[:3])
                    if technique.platforms
                    else "Multiple"
                )

                html_parts.append(
                    f"""
                <div class="technique-item" style="border-left: 4px solid #FF6B35; padding-left: 12px; margin-bottom: 16px; background-color: #fff3e0; padding: 12px; border-radius: 4px;">
                    <h5 style="margin: 0 0 8px 0; color: #E65100;">
                        <span style="background-color: #FF6B35; color: white; padding: 2px 8px; border-radius: 3px; font-family: monospace; font-size: 0.85em;">
                            {technique.technique_id}
                        </span> {technique.name}
                    </h5>
                    <p style="margin: 4px 0 8px 0; color: #666; font-size: 0.9em;">
                        {technique.description[:180]}{"..." if len(technique.description) > 180 else ""}
                    </p>
                    <div class="technique-meta" style="font-size: 0.85em; color: #999;">
                        <strong>Tactic:</strong> {technique.tactic} |
                        <strong>Platforms:</strong> {platforms_str} |
                        <a href="{technique.url}" target="_blank" style="color: #0066cc;">View Details</a>
                    </div>
                </div>
                """
                )

            html_parts.append("</div>")

        # Footer with cache info
        last_refresh = cache_info.get("last_refresh", "Never")
        html_parts.append(
            f"""
            <div class="mitre-footer" style="margin-top: 20px; padding: 12px; background-color: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196F3;">
                <p style="margin: 0; color: #0d47a1;"><strong>ℹ️ Data Source:</strong></p>
                <ul style="margin: 8px 0 0 0; padding-left: 20px; color: #1565c0;">
                    <li>Official MITRE ATT&CK Framework API</li>
                    <li>Last Updated: {last_refresh}</li>
                    <li>Cached locally in: {cache_info['storage_location']}</li>
                    <li>Focus: Enterprise threats targeting {sector} sector</li>
                </ul>
            </div>
        </div>
        """
        )

        return "".join(html_parts)


class FeedsEventHandlerBuilder:
    """Builder class for creating feeds event handlers with dependency injection."""

    def __init__(self, feeds_service: RSSFeedService):
        """Initialize the builder with required services.

        Args:
            feeds_service: Service for RSS feed operations
        """
        self.feeds_service = feeds_service
        # Create display_utility for CVE filtering with threat analyzer
        from internal_assistant.ui.components.feeds.display_utility import (
            DisplayUtilityBuilder,
        )

        # Get threat analyzer from dependency injection for MITRE integration
        threat_analyzer = None
        try:
            from internal_assistant.di import global_injector
            from internal_assistant.server.threat_intelligence.threat_analyzer import (
                ThreatIntelligenceAnalyzer,
            )

            threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)
            logger.debug("ThreatIntelligenceAnalyzer loaded for CVE MITRE integration")
        except Exception as e:
            logger.warning(
                f"Could not load ThreatIntelligenceAnalyzer for CVE display: {e}"
            )

        self.display_utility = DisplayUtilityBuilder(feeds_service, threat_analyzer)
        self._handler = None

    def get_handler(self) -> FeedsEventHandler:
        """Get or create the feeds event handler instance.

        Returns:
            FeedsEventHandler instance
        """
        if self._handler is None:
            self._handler = FeedsEventHandler(self.feeds_service, self.display_utility)
        return self._handler

    def create_refresh_feeds_handler(self):
        """Create handler for refreshing RSS feeds."""

        async def wrapper():
            return await self.get_handler().refresh_feeds()

        return wrapper

    def create_filter_feeds_handler(self, time_filter: str):
        """Create handler for filtering feeds by time period."""

        def wrapper(feeds_content):
            # Returns tuple of (time_range_display_html, filter_state, filtered_feeds_html)
            return self.get_handler().filter_feeds(time_filter, feeds_content)

        return wrapper

    def create_filter_cve_handler(self, time_filter: str):
        """Create handler for filtering CVE data by time period."""

        def wrapper(cve_content):
            # Returns tuple of (time_range_display_html, filter_state, filtered_cve_html)
            return self.get_handler().filter_cve(time_filter, cve_content)

        return wrapper

    def create_refresh_cve_handler(self):
        """Create handler for refreshing CVE data."""

        async def wrapper():
            # Handler now returns (status, html) tuple
            return await self.get_handler().refresh_cve_data()

        return wrapper

    def create_refresh_mitre_handler(self):
        """Create handler for refreshing MITRE data."""

        async def wrapper():
            # Handler now returns (status, html) tuple
            return await self.get_handler().refresh_mitre_data()

        return wrapper

    def create_refresh_and_filter_feeds_handler(self, time_filter: str):
        """Create handler for refreshing and filtering RSS feeds by time period."""

        async def wrapper():
            # Handler returns (status, time_range_display_html, filter_state, filtered_html)
            return await self.get_handler().refresh_and_filter_feeds(time_filter)

        return wrapper

    def create_refresh_and_filter_cve_handler(self, time_filter: str):
        """Create handler for refreshing and filtering CVE data by time period."""

        async def wrapper():
            # Handler returns (status, time_range_display_html, filter_state, filtered_html)
            return await self.get_handler().refresh_and_filter_cve(time_filter)

        return wrapper

    def create_category_filter_handler(self, category: str):
        """Create handler for filtering feeds by source category (30-day window).

        Args:
            category: Category name (e.g., "Banking Regulation", "Cybersecurity")

        Returns:
            Handler function that filters feeds by category
        """

        def wrapper():
            # Handler returns combined HTML with status header + feed display
            return self.get_handler().filter_by_category(category)

        return wrapper
