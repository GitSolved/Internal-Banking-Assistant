"""
Feeds Event Handlers

This module contains all event handlers for RSS feeds and threat intelligence components.
Extracted from ui.py as part of Phase 1 refactoring to decouple event handling
from UI construction.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

import gradio as gr

from internal_assistant.server.feeds.feeds_service import RSSFeedService

logger = logging.getLogger(__name__)


class FeedsEventHandler:
    """
    Handles all feed-related events including RSS feed refresh, filtering,
    and threat intelligence updates.
    """

    def __init__(self, feeds_service: RSSFeedService, display_utility=None):
        """
        Initialize feeds event handler with required services.

        Args:
            feeds_service: Service for RSS feed operations
            display_utility: DisplayUtilityBuilder for formatting CVE data
        """
        self.feeds_service = feeds_service
        self.display_utility = display_utility

    async def refresh_feeds(self) -> Tuple[str, str]:
        """
        Refresh RSS feeds and update display.
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
            error_msg = f"Failed to refresh RSS feeds: {str(e)}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ RSS Feed Refresh Failed</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check your internet connection</li>
                    <li>Verify feed URLs are accessible</li>
                    <li>Try refreshing again in a few minutes</li>
                </ul>
            </div>
            """
            return f"❌ Error: {str(e)}", error_html

    def filter_cve(
        self, time_filter: str, cve_content: str
    ) -> Tuple[str, str, str]:
        """
        Filter CVE data by time period.

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
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""
            return (
                "<div style='color: #d32f2f;'>⚠️ Filter Error</div>",
                "30 days",
                error_html,
            )

    def filter_feeds(
        self, time_filter: str, feeds_content: str
    ) -> Tuple[str, str, str]:
        """
        Filter feeds by time period.
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
            error_msg = f"Failed to filter feeds: {str(e)}"
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
                f"<div class='error-message'>Filter error: {str(e)}</div>",
            )

    def _is_feed_within_timeframe(
        self, feed: Dict[str, Any], cutoff_date: datetime
    ) -> bool:
        """
        Check if feed is within the specified timeframe.

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
                        from datetime import timezone

                        cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
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

    def _parse_time_filter(self, time_filter: str) -> Optional[int]:
        """
        Parse time filter string to hours.

        Args:
            time_filter: Time filter (24h, 7d, 30d, 90d)

        Returns:
            Hours as integer, or None if invalid
        """
        filter_map = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30, "90d": 24 * 90}
        return filter_map.get(time_filter.lower())

    def _format_feeds_html(self, feeds: List[Dict[str, Any]]) -> str:
        """
        Format feeds data into HTML.

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

    async def refresh_cve_data(self) -> Tuple[str, str]:
        """
        Refresh CVE (Common Vulnerabilities and Exposures) data.
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
                7  # days_filter = 7 days
            )

            status_msg = "✅ CVE data refreshed (showing last 7 days)"
            logger.info(f"CVE data refresh completed with 7-day filter")
            return status_msg, cve_html

        except Exception as e:
            error_msg = f"Failed to refresh CVE data: {str(e)}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ CVE Data Refresh Failed</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please try again later or check your network connection.</p>
            </div>
            """
            return f"❌ Error: {str(e)}", error_html

    async def refresh_and_filter_feeds(self, time_filter: str) -> Tuple[str, str, str, str]:
        """
        Refresh RSS feeds from source and filter by time period.
        Combines refresh and filter operations for time filter buttons.

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)

        Returns:
            Tuple of (status_message, time_range_display_html, filter_state, filtered_html)
        """
        try:
            logger.info(f"Refreshing and filtering feeds with time_filter={time_filter}")

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
                    return "Failed to refresh feeds", time_range_html, display_text, error_html

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
                return "Invalid time filter", time_range_html, display_text, "Invalid time filter specified."

            # Calculate cutoff date and filter feeds
            cutoff_date = datetime.now() - timedelta(hours=filter_hours)
            feeds = self.feeds_service.get_feeds()

            if not feeds:
                return "No feeds available", time_range_html, display_text, "<div class='no-content'>No feeds available</div>"

            filtered_feeds = [
                feed for feed in feeds
                if self._is_feed_within_timeframe(feed, cutoff_date)
            ]

            if not filtered_feeds:
                empty_html = f"""
                <div class="no-feeds-message">
                    <h3>📅 No Feeds Found</h3>
                    <p>No feeds found for the last {display_text}.</p>
                </div>
                """
                return f"No feeds in last {display_text}", time_range_html, display_text, empty_html

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
            error_html = f"<div class='error-message'>Error: {str(e)}</div>"
            return f"❌ Error: {str(e)}", time_range_html, display_text, error_html

    async def refresh_and_filter_cve(self, time_filter: str) -> Tuple[str, str, str, str]:
        """
        Refresh CVE data from source and filter by time period.
        Combines refresh and filter operations for CVE time filter buttons.

        Args:
            time_filter: Time filter period (24h, 7d, 30d, 90d)

        Returns:
            Tuple of (status_message, time_range_display_html, filter_state, filtered_html)
        """
        try:
            logger.info(f"Refreshing and filtering CVE data with time_filter={time_filter}")

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
                    return "Failed to refresh CVE data", time_range_html, display_text, error_html

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
            error_html = f"<div class='error-message'>Error: {str(e)}</div>"
            return f"❌ Error: {str(e)}", time_range_html, display_text, error_html

    async def refresh_mitre_data(self) -> Tuple[str, str]:
        """
        Refresh MITRE ATT&CK framework data from official API.
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
            error_msg = f"Failed to refresh MITRE data: {str(e)}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ MITRE ATT&CK Refresh Failed</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check your internet connection</li>
                    <li>Verify MITRE ATT&CK API is accessible</li>
                    <li>Try refreshing again in a few minutes</li>
                </ul>
            </div>
            """
            return f"❌ Error: {str(e)}", error_html

    def _format_mitre_attack_data(self, mitre_service, sector: str = "Financial") -> str:
        """
        Format MITRE ATT&CK data into HTML.

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

        html_parts = [f"""
        <div class="mitre-attack-container">
            <div class="mitre-header">
                <h3>🎯 MITRE ATT&CK Framework Data</h3>
                <p><strong>Total Techniques:</strong> {cache_info['techniques_count']} |
                   <strong>Tactics:</strong> {cache_info['tactics_count']} |
                   <strong>Threat Groups:</strong> {cache_info['groups_count']}</p>
                <p><strong>Sector-Relevant:</strong> {len(sector_techniques)} techniques | {len(sector_groups)} threat groups</p>
            </div>
        """]

        # Display sector-relevant threat groups
        if sector_groups:
            html_parts.append("""
            <div class="mitre-section">
                <h4 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 8px; margin-top: 20px;">
                    🚨 High-Priority Threat Groups (Targeting Banking/Financial Sector)
                </h4>
            """)

            for group in sector_groups[:10]:  # Show top 10
                aliases_str = ", ".join(group.aliases[:3]) if group.aliases else "None"
                techniques_count = len(group.techniques) if group.techniques else 0

                html_parts.append(f"""
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
                """)

            html_parts.append("</div>")

        # Display sector-relevant techniques (sample)
        if sector_techniques:
            html_parts.append("""
            <div class="mitre-section">
                <h4 style="color: #FF6B35; border-bottom: 2px solid #FF6B35; padding-bottom: 8px; margin-top: 20px;">
                    ⚠️ Key Techniques to Monitor
                </h4>
            """)

            for technique in sector_techniques[:15]:  # Show top 15
                platforms_str = ", ".join(technique.platforms[:3]) if technique.platforms else "Multiple"

                html_parts.append(f"""
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
                """)

            html_parts.append("</div>")

        # Footer with cache info
        last_refresh = cache_info.get("last_refresh", "Never")
        html_parts.append(f"""
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
        """)

        return "".join(html_parts)

    async def refresh_simple_forum_directory(self) -> Tuple[str, str]:
        """
        Refresh Tor Taxi forum directory.
        Fetches actual dark web forum links from tor.taxi using dedicated scraper.

        Returns:
            Tuple of (status_message, HTML string with updated forum directory content)
        """
        try:
            logger.info("Starting Tor Taxi forum directory refresh...")

            # Import the dedicated forum directory service
            from internal_assistant.server.feeds.forum_directory_service import (
                ForumDirectoryService,
            )

            # Use the actual Tor Taxi scraper
            async with ForumDirectoryService() as forum_service:
                success = await forum_service.fetch_forum_directory()

                if not success:
                    error_html = """
                    <div class="no-feeds-message">
                        <h3>🌐 Tor Taxi Unavailable</h3>
                        <p>Unable to fetch forum directory from tor.taxi</p>
                        <p><strong>Possible reasons:</strong></p>
                        <ul>
                            <li>Tor.taxi is temporarily down</li>
                            <li>Network connectivity issues</li>
                            <li>Site is being updated</li>
                        </ul>
                        <p><em>Try refreshing again in a few minutes.</em></p>
                    </div>
                    """
                    return "Failed to fetch Tor Taxi data", error_html

                forums = forum_service.get_forums()

            if not forums:
                empty_html = """
                <div class="no-feeds-message">
                    <h3>🌐 No Forums Found</h3>
                    <p>No forums available from Tor Taxi.</p>
                    <p>This may indicate a parsing issue. Try refreshing again.</p>
                </div>
                """
                return "No forums found", empty_html

            # Format forum directory using dedicated formatter
            forum_html = self._format_tor_taxi_forums(forums)

            status_msg = f"✅ Found {len(forums)} forums from Tor Taxi"
            logger.info(f"Tor Taxi refresh completed: {len(forums)} forums")
            return status_msg, forum_html

        except Exception as e:
            error_msg = f"Failed to refresh Tor Taxi: {str(e)}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ Tor Taxi Refresh Failed</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check your internet connection</li>
                    <li>Verify tor.taxi is accessible</li>
                    <li>Try refreshing again in a few minutes</li>
                </ul>
            </div>
            """
            return f"❌ Error: {str(e)}", error_html

    def _format_tor_taxi_forums(self, forums: List[Dict[str, Any]]) -> str:
        """
        Format Tor Taxi forum data into HTML.

        Args:
            forums: List of forum dictionaries from ForumDirectoryService

        Returns:
            Formatted HTML string with forum directory
        """
        if not forums:
            return "<div class='no-content'>No forums available</div>"

        # Group forums by category
        categories = {}
        for forum in forums:
            category = forum.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(forum)

        html_parts = ['<div class="forum-directory">']

        # Display forums grouped by category
        for category, category_forums in sorted(categories.items()):
            html_parts.append(f"""
            <div class="forum-category">
                <h4 class="category-title" style="color: #0077BE; border-bottom: 2px solid #0077BE; padding-bottom: 8px; margin-top: 20px;">
                    📁 {category} ({len(category_forums)} forums)
                </h4>
            """)

            for forum in category_forums[:20]:  # Limit per category
                name = forum.get("name", "Unknown Forum")
                description = forum.get("description", "No description available")
                url = forum.get("url", "#")

                # Truncate long descriptions
                if len(description) > 150:
                    description = description[:150] + "..."

                html_parts.append(f"""
                <div class="forum-item" style="border-left: 4px solid #6F42C1; padding-left: 12px; margin-bottom: 16px; background-color: #f8f9fa; padding: 12px; border-radius: 4px;">
                    <h5 style="margin: 0 0 8px 0; color: #333;">
                        <span style="color: #6F42C1;">🌐</span> {name}
                    </h5>
                    <p class="forum-description" style="margin: 4px 0 8px 0; color: #666; font-size: 0.9em;">
                        {description}
                    </p>
                    <div class="forum-meta" style="font-size: 0.85em; color: #999;">
                        <span style="font-family: monospace; background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">
                            {url}
                        </span>
                    </div>
                </div>
                """)

            html_parts.append("</div>")

        html_parts.append("</div>")

        return "".join(html_parts)

    async def filter_forum_directory(self, filter_category: str) -> Tuple[str, str]:
        """
        Filter forum directory by category (Professional, Dark Web, CTF, etc.).

        Args:
            filter_category: Category filter ("All", "Professional", "Dark Web", "CTF & Training", "Bug Bounty", "Specialized")

        Returns:
            Tuple of (status_message, HTML string with filtered forum content)
        """
        try:
            logger.info(f"Filtering forum directory with category={filter_category}")

            # Import the forum directory service
            from internal_assistant.server.feeds.forum_directory_service import (
                ForumDirectoryService,
            )

            # Map display names to internal category codes
            category_map = {
                "All": None,
                "Professional": "professional",
                "Dark Web": "darkweb",
                "CTF & Training": "ctf_training",
                "Bug Bounty": "bug_bounty",
                "Specialized": "specialized",
            }

            category_filter = category_map.get(filter_category)

            # Get forums with category filter
            async with ForumDirectoryService() as forum_service:
                forums = forum_service.get_forums(category_filter=category_filter)

            if not forums:
                empty_html = f"""
                <div class="no-feeds-message">
                    <h3>🌐 No Forums Found</h3>
                    <p>No forums found for category: <strong>{filter_category}</strong></p>
                    <p>Try selecting a different category or "All" to see all forums.</p>
                </div>
                """
                return f"No forums in {filter_category}", empty_html

            # Format forums using combined formatter
            forum_html = self._format_combined_forums(forums, filter_category)

            status_msg = f"✅ Showing {len(forums)} forums ({filter_category})"
            logger.info(status_msg)
            return status_msg, forum_html

        except Exception as e:
            error_msg = f"Failed to filter forums: {str(e)}"
            logger.error(error_msg)

            error_html = f"""
            <div class="error-message">
                <h3>⚠️ Forum Filter Failed</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Try refreshing the forum directory or selecting a different category.</p>
            </div>
            """
            return f"❌ Error: {str(e)}", error_html

    async def export_forum_directory(self, filter_category: str) -> str:
        """
        Export forum directory to JSON/CSV/Markdown format.

        Args:
            filter_category: Category filter for export

        Returns:
            Status message indicating export success/failure
        """
        try:
            logger.info(f"Exporting forum directory with category={filter_category}")

            # Import the forum directory service
            from internal_assistant.server.feeds.forum_directory_service import (
                ForumDirectoryService,
            )

            # Map display names to internal category codes
            category_map = {
                "All": None,
                "Professional": "professional",
                "Dark Web": "darkweb",
                "CTF & Training": "ctf_training",
                "Bug Bounty": "bug_bounty",
                "Specialized": "specialized",
            }

            category_filter = category_map.get(filter_category)

            # Export forums (default to JSON format)
            async with ForumDirectoryService() as forum_service:
                export_data = forum_service.export_forum_list(
                    format="json",
                    category_filter=category_filter
                )

            # Save to file in local_data directory
            from pathlib import Path
            export_dir = Path("local_data/internal_assistant/exports")
            export_dir.mkdir(parents=True, exist_ok=True)

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            category_suffix = filter_category.lower().replace(" ", "_").replace("&", "and")
            export_file = export_dir / f"forum_directory_{category_suffix}_{timestamp}.json"

            export_file.write_text(export_data, encoding="utf-8")

            status_msg = f"✅ Exported {filter_category} forums to: {export_file.name}"
            logger.info(status_msg)
            return status_msg

        except Exception as e:
            error_msg = f"Failed to export forums: {str(e)}"
            logger.error(error_msg)
            return f"❌ Export Error: {str(e)}"

    def _format_combined_forums(self, forums: List[Dict[str, Any]], category_display: str) -> str:
        """
        Format combined clearnet and darkweb forums into HTML.

        Args:
            forums: List of forum dictionaries from ForumDirectoryService
            category_display: Display name of the selected category

        Returns:
            Formatted HTML string with forum directory
        """
        if not forums:
            return "<div class='no-content'>No forums available</div>"

        # Separate clearnet and darkweb forums
        clearnet_forums = [f for f in forums if f.get("access_type") == "clearnet"]
        darkweb_forums = [f for f in forums if f.get("access_type") == "darkweb"]

        html_parts = [f"""
        <div class="forum-directory">
            <div class="forum-header">
                <h3>🌐 Security Forums & Communities Directory</h3>
                <p><strong>Category:</strong> {category_display} | <strong>Total Forums:</strong> {len(forums)}</p>
                <p><strong>Clearnet:</strong> {len(clearnet_forums)} | <strong>Dark Web:</strong> {len(darkweb_forums)}</p>
            </div>
        """]

        # Display clearnet forums first
        if clearnet_forums:
            html_parts.append("""
            <div class="forum-section">
                <h4 class="section-title" style="color: #28A745; border-bottom: 2px solid #28A745; padding-bottom: 8px; margin-top: 20px;">
                    🌐 Clearnet Forums (Public Access)
                </h4>
            """)

            for forum in clearnet_forums:
                name = forum.get("name", "Unknown Forum")
                description = forum.get("description", "No description available")
                url = forum.get("url", "#")
                category = forum.get("category", "General")

                # Category badge with color coding
                category_colors = {
                    "professional": "#0077BE",
                    "ctf_training": "#6F42C1",
                    "bug_bounty": "#FF6B35",
                    "specialized": "#20C997",
                }
                badge_color = category_colors.get(category, "#6c757d")

                html_parts.append(f"""
                <div class="forum-item" style="border-left: 4px solid {badge_color}; padding-left: 12px; margin-bottom: 16px; background-color: #f8f9fa; padding: 12px; border-radius: 4px;">
                    <h5 style="margin: 0 0 8px 0; color: #333;">
                        <span style="color: #28A745;">🌐</span> {name}
                        <span style="background-color: {badge_color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.75em; margin-left: 8px;">
                            {category.replace('_', ' ').title()}
                        </span>
                    </h5>
                    <p class="forum-description" style="margin: 4px 0 8px 0; color: #666; font-size: 0.9em;">
                        {description}
                    </p>
                    <div class="forum-meta" style="font-size: 0.85em; color: #999;">
                        <a href="{url}" target="_blank" style="color: #0066cc;">🔗 Visit Forum</a>
                    </div>
                </div>
                """)

            html_parts.append("</div>")

        # Display darkweb forums
        if darkweb_forums:
            html_parts.append("""
            <div class="forum-section">
                <h4 class="section-title" style="color: #6F42C1; border-bottom: 2px solid #6F42C1; padding-bottom: 8px; margin-top: 20px;">
                    🔒 Dark Web Forums (Tor Required)
                </h4>
            """)

            for forum in darkweb_forums:
                name = forum.get("name", "Unknown Forum")
                description = forum.get("description", "No description available")
                url = forum.get("url", "#")
                category = forum.get("category", "General")

                # Truncate long descriptions
                if len(description) > 150:
                    description = description[:150] + "..."

                html_parts.append(f"""
                <div class="forum-item" style="border-left: 4px solid #6F42C1; padding-left: 12px; margin-bottom: 16px; background-color: #f8f9fa; padding: 12px; border-radius: 4px;">
                    <h5 style="margin: 0 0 8px 0; color: #333;">
                        <span style="color: #6F42C1;">🔒</span> {name}
                    </h5>
                    <p class="forum-description" style="margin: 4px 0 8px 0; color: #666; font-size: 0.9em;">
                        {description}
                    </p>
                    <div class="forum-meta" style="font-size: 0.85em; color: #999;">
                        <span style="font-family: monospace; background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">
                            {url}
                        </span>
                    </div>
                </div>
                """)

            html_parts.append("</div>")

        html_parts.append("</div>")

        return "".join(html_parts)


class FeedsEventHandlerBuilder:
    """
    Builder class for creating feeds event handlers with dependency injection.
    """

    def __init__(self, feeds_service: RSSFeedService):
        """
        Initialize the builder with required services.

        Args:
            feeds_service: Service for RSS feed operations
        """
        self.feeds_service = feeds_service
        # Create display_utility for CVE filtering with threat analyzer
        from internal_assistant.ui.components.feeds.display_utility import DisplayUtilityBuilder

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
            logger.warning(f"Could not load ThreatIntelligenceAnalyzer for CVE display: {e}")

        self.display_utility = DisplayUtilityBuilder(feeds_service, threat_analyzer)
        self._handler = None

    def get_handler(self) -> FeedsEventHandler:
        """
        Get or create the feeds event handler instance.

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

    def create_refresh_forum_handler(self):
        """Create handler for refreshing forum directory."""

        async def wrapper():
            # Handler now returns (status, html) tuple
            return await self.get_handler().refresh_simple_forum_directory()

        return wrapper

    def create_filter_forum_handler(self):
        """Create handler for filtering forum directory by category."""

        async def wrapper(filter_category: str):
            # Handler now returns (status, html) tuple
            return await self.get_handler().filter_forum_directory(filter_category)

        return wrapper

    def create_export_forum_handler(self):
        """Create handler for exporting forum directory."""

        async def wrapper(filter_category: str):
            # Handler returns status message only
            return await self.get_handler().export_forum_directory(filter_category)

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
