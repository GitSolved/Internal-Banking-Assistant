"""
Feeds Display Component

This module contains feeds display functions extracted from ui.py
during Phase 1B.5 of the UI refactoring project.

Extracted from ui.py lines:
- _format_feeds_display() (lines 442-754)
- _format_cve_display() (lines 754+)

Author: UI Refactoring Team
Date: 2024-01-18
Phase: 1B.5 - Feeds Display Extraction
Updated: 2025-01-19 - Phase 1B.ACC.1 - Added missing format_rss_display() and format_news_display()
Updated: 2025-01-19 - Phase 1 MITRE Integration - Added MITRE technique cross-referencing
"""

import logging
from typing import Optional

from internal_assistant.server.feeds.feeds_service import RSSFeedService

logger = logging.getLogger(__name__)


class FeedsDisplayBuilder:
    """
    Builder class for feeds display functionality.
    Handles RSS feeds and CVE display formatting with MITRE ATT&CK integration.
    """

    def __init__(self, feeds_service: RSSFeedService, threat_analyzer=None):
        """
        Initialize the FeedsDisplayBuilder.

        Args:
            feeds_service: Service for RSS feeds management
            threat_analyzer: Optional ThreatIntelligenceAnalyzer for MITRE technique extraction
        """
        self._feeds_service = feeds_service
        self._threat_analyzer = threat_analyzer

        # Lazy-load threat analyzer if not provided
        if self._threat_analyzer is None:
            try:
                from internal_assistant.di import global_injector
                from internal_assistant.server.threat_intelligence.threat_analyzer import (
                    ThreatIntelligenceAnalyzer,
                )
                self._threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)
                logger.debug("ThreatIntelligenceAnalyzer loaded for MITRE integration")
            except Exception as e:
                logger.warning(f"Could not load ThreatIntelligenceAnalyzer: {e}")
                self._threat_analyzer = None

    def format_feeds_display(
        self, source_filter: str = None, days_filter: int = None
    ) -> str:
        """
        Format RSS feeds for display in the UI.

        Args:
            source_filter: Optional source filter
            days_filter: Optional days filter

        Returns:
            Formatted HTML string for feeds display
        """
        try:
            feeds = self._feeds_service.get_feeds(source_filter, days_filter)

            if not feeds:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>📡 No external information available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest regulatory feeds
                        </div>
                    </div>
                </div>"""

            html_content = """
            <script>
            function confirmOpenExternal(url, title) {
                if (confirm('Open external link: ' + title + '?')) {
                    window.open(url, '_blank');
                }
            }
            </script>
            <div class='feed-content' style='max-height: none; height: auto; overflow-y: auto; overflow-x: auto; padding-right: 8px; scroll-behavior: smooth; min-width: 100%;'>"""

            # Group feeds by source
            sources = {}
            for feed in feeds:
                source = feed["source"]
                if source not in sources:
                    sources[source] = []
                sources[source].append(feed)

            # Sort feeds within each source by date (latest first)
            for source in sources:
                sources[source].sort(key=lambda x: x["published"], reverse=True)

            for source, source_feeds in sources.items():
                # Source header with color scheme
                # Enhanced source icons for threat intelligence agencies
                source_icons = {
                    # Banking Regulators
                    "Federal Reserve": "🏦",
                    "FDIC": "🏛️",
                    "OCC": "🏦",
                    "FFIEC": "📋",
                    # Financial Crimes
                    "FinCEN": "💰",
                    "FBI IC3": "🔍",
                    "Secret Service Financial Crimes": "🕵️",
                    # Cybersecurity
                    "US-CERT": "🔒",
                    "NIST": "📊",
                    "DHS": "🏛️",
                    "NSA": "🕵️",
                    # Government & Treasury
                    "Treasury": "💰",
                    # Consumer Protection
                    "CFPB": "🛡️",
                    # Securities & Markets
                    "SEC": "📈",
                    "FINRA": "📋",
                    "NCUA": "🏦",
                }
                source_icon = source_icons.get(source, "📰")

                # Get color from feeds service
                source_color = self._feeds_service.SOURCE_COLORS.get(source, "#0077BE")

                html_content += f"""
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' data-source='{source}' 
                        style='color: {source_color}; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold; cursor: pointer; transition: all 0.2s;'
                        onmouseover='this.style.textDecoration="underline"; this.style.color="{source_color}"; this.style.opacity="0.8";'
                        onmouseout='this.style.textDecoration="none"; this.style.color="{source_color}"; this.style.opacity="1";'
                        onclick='filterBySource("{source}")'>
                        {source_icon} {source} ({len(source_feeds)} items)
                    </h4>
                    <div class='feed-items' style='margin-left: 16px;'>
                """

                # Display feeds for this source
                for feed in source_feeds[:10]:  # Limit to 10 items per source
                    published_date = feed.get("published", "Unknown Date")
                    title = feed.get("title", "No Title")
                    link = feed.get("link", "#")
                    summary = feed.get("summary", "No summary available")

                    # Truncate summary if too long
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                    # Extract MITRE techniques for this feed item
                    mitre_techniques = []
                    if self._threat_analyzer:
                        try:
                            mitre_techniques = self._threat_analyzer.extract_mitre_techniques_from_feed_item(feed)
                            # Limit to top 3 techniques by confidence
                            mitre_techniques = mitre_techniques[:3]
                        except Exception as e:
                            logger.warning(f"Error extracting MITRE techniques: {e}")

                    # Build MITRE technique badges HTML
                    mitre_badges_html = ""
                    if mitre_techniques:
                        mitre_badges_html = "<div style='margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px;'>"
                        for tech in mitre_techniques:
                            technique_id = tech.get("technique_id", "")
                            confidence = tech.get("confidence", 0.0)
                            confidence_pct = int(confidence * 100)

                            # Color based on confidence: high=green, medium=yellow, low=orange
                            badge_color = "#28A745" if confidence >= 0.8 else "#FFA500" if confidence >= 0.6 else "#FF6B35"

                            mitre_badges_html += f"""
                            <span style='
                                background: {badge_color}22;
                                color: {badge_color};
                                padding: 3px 8px;
                                border-radius: 4px;
                                font-size: 10px;
                                font-weight: 600;
                                border: 1px solid {badge_color};
                                cursor: help;
                            ' title='Confidence: {confidence_pct}%'>
                                🎯 {technique_id}
                            </span>"""
                        mitre_badges_html += "</div>"

                    html_content += f"""
                    <div class='feed-item' style='margin-bottom: 16px; padding: 12px; background: #1a1a1a; border-radius: 8px; border-left: 3px solid {source_color};'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                            <h5 style='margin: 0; color: #e0e0e0; font-size: 14px; font-weight: 600;'>
                                <a href='javascript:void(0)' onclick='confirmOpenExternal("{link}", "{title}")' style='color: inherit; text-decoration: none; cursor: pointer;'>{title}</a>
                            </h5>
                            <span style='color: #888; font-size: 11px; white-space: nowrap; margin-left: 8px;'>{published_date}</span>
                        </div>
                        <p style='margin: 0; color: #ccc; font-size: 12px; line-height: 1.4;'>{summary}</p>
                        {mitre_badges_html}
                    </div>
                    """

                html_content += """
                    </div>
                </div>
                """

            html_content += "</div>"
            return html_content

        except Exception as e:
            logger.error(f"Error formatting feeds display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #ff6b6b; padding: 20px;'>
                    <div>❌ Error loading external information</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        {str(e)}
                    </div>
                </div>
            </div>"""

    def format_rss_display(self, search_term: str = "", category: str = "All") -> str:
        """
        Format RSS feed display with search and category filtering.

        Args:
            search_term: Search filter text
            category: Category filter

        Returns:
            HTML string for RSS feed display
        """
        try:
            if self._feeds_service:
                feeds_data = self._feeds_service.get_feeds(
                    category, 30
                )  # Get last 30 days

                if search_term:
                    feeds_data = [
                        feed
                        for feed in feeds_data
                        if search_term.lower() in feed.get("title", "").lower()
                        or search_term.lower() in feed.get("summary", "").lower()
                    ]

                if category != "All":
                    feeds_data = [
                        feed
                        for feed in feeds_data
                        if feed.get("source", "").lower() == category.lower()
                    ]

                return self._render_rss_html(feeds_data)
            else:
                return """
                <div class="feed-display">
                    <h3>📰 RSS Security Feeds</h3>
                    <div class="no-data">
                        <p>No RSS feeds service configured.</p>
                        <p>Configure RSS feeds in your settings to view security news and updates.</p>
                    </div>
                </div>
                """

        except Exception as e:
            logger.error(f"Failed to get RSS feeds: {e}")
            return f"""
            <div class="feed-display">
                <h3>📰 RSS Security Feeds</h3>
                <div class="error">
                    <p>Error loading RSS feeds: {str(e)}</p>
                </div>
            </div>
            """

    def format_news_display(self, search_term: str = "", category: str = "All") -> str:
        """
        Format news display with search and category filtering.

        Args:
            search_term: Search filter text
            category: Category filter

        Returns:
            HTML string for news display
        """
        try:
            # This is a placeholder implementation for news display
            # Can be enhanced later with specific news sources
            return self.format_rss_display(search_term, category)

        except Exception as e:
            logger.error(f"Error formatting news display: {e}")
            return f"""
            <div class="news-display">
                <h3>📰 News Display</h3>
                <div class="error">
                    <p>Error loading news: {str(e)}</p>
                </div>
            </div>
            """

    def _render_rss_html(self, feeds_data: list) -> str:
        """
        Render RSS feeds as HTML.

        Args:
            feeds_data: List of feed data

        Returns:
            HTML string for RSS feeds
        """
        if not feeds_data:
            return """
            <div class="feed-display">
                <h3>📰 RSS Security Feeds</h3>
                <p>No RSS feeds found matching your criteria.</p>
            </div>
            """

        html = '<div class="rss-feeds"><h3>📰 RSS Security Feeds</h3>'
        for feed in feeds_data[:10]:  # Limit to 10 feeds
            title = feed.get("title", "No Title")
            link = feed.get("link", "#")
            summary = feed.get("summary", "No description available")[:200]
            published = feed.get("published", "Unknown date")
            source = feed.get("source", "Unknown source")

            html += f"""
            <div class="feed-item">
                <h4><a href="javascript:void(0)" onclick="confirmOpenExternal('{link}', '{title}')" target="_blank" rel="noopener">{title}</a></h4>
                <p class="feed-meta">
                    <span class="source">📡 {source}</span> | 
                    <span class="date">📅 {published}</span>
                </p>
                <p class="feed-description">{summary}...</p>
            </div>
            """

        html += "</div>"
        return html

    def format_cve_display(
        self,
        source_filter: str = None,
        severity_filter: str = "All Severities",
        vendor_filter: str = "All Vendors",
    ) -> str:
        """
        Format CVE information for display in the UI.

        Args:
            source_filter: Optional source filter
            severity_filter: Severity filter
            vendor_filter: Vendor filter

        Returns:
            Formatted HTML string for CVE display
        """
        try:
            # This would integrate with CVE service when available
            # For now, return a placeholder
            return """
            <div class='cve-content'>
                <div style='text-align: center; color: #666; padding: 20px;'>
                    <div>🔒 CVE Information</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        CVE display functionality coming soon
                    </div>
                </div>
            </div>"""

        except Exception as e:
            logger.error(f"Error formatting CVE display: {e}")
            return """
            <div class='cve-content'>
                <div style='text-align: center; color: #ff6b6b; padding: 20px;'>
                    <div>❌ Error loading CVE information</div>
                    <div style='font-size: 12px; margin-top: 8px;'>
                        Please try again later
                    </div>
                </div>
            </div>"""

    def get_cve_data(self) -> list:
        """
        Get CVE data from feeds service.

        Returns:
            List of CVE feed items
        """
        try:
            # Get all feeds and filter to CVE tracking sources
            all_feeds = self._feeds_service.get_feeds(None, 30)
            cve_sources = ["CISA KEV", "NIST NVD"]
            feeds = [f for f in all_feeds if f.get("source") in cve_sources]
            logger.info(
                f"Retrieved {len(feeds)} CVE feed items from {', '.join(cve_sources)}"
            )
            return feeds or []
        except Exception as e:
            logger.error(f"Error getting CVE data: {e}")
            return []

    def is_feeds_cache_empty(self) -> bool:
        """
        Check if the feeds cache is empty.

        Returns:
            True if cache is empty, False otherwise
        """
        try:
            # Get cache info from feeds service
            cache_info = self._feeds_service.get_cache_info()
            total_items = cache_info.get("total_items", 0)
            logger.info(f"Feeds cache status: {total_items} items")
            return total_items == 0
        except Exception as e:
            logger.error(f"Error checking feeds cache status: {e}")
            return True  # Assume empty if we can't check
