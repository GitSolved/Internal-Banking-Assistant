"""Feed Component

This module implements the feed display component for the Internal Assistant UI.
It handles RSS feeds, CVE information, MITRE ATT&CK data, and forum displays.

This component will eventually contain the extracted feed functionality from ui.py,
including feed formatting, threat intelligence display, and data visualization.
"""

import logging
from typing import Any

import gradio as gr

from internal_assistant.ui.core.ui_component import UIComponent

logger = logging.getLogger(__name__)


class FeedComponent(UIComponent):
    """Feed display component for the Internal Assistant.

    This component manages:
    - RSS feed display and filtering
    - CVE information display
    - MITRE ATT&CK framework visualization
    - Forum content display
    - Threat intelligence integration
    """

    def __init__(
        self, component_id: str = "feeds", services: dict[str, Any] | None = None
    ):
        """Initialize the feed component.

        Args:
            component_id: Unique identifier for this component
            services: Dictionary of injected services
        """
        super().__init__(component_id, services)
        self.feeds_service = None

        # Get required services
        if self.has_service("feeds"):
            self.feeds_service = self.get_service("feeds")

    def get_required_services(self) -> list[str]:
        """Specify required services for this component."""
        return ["feeds"]

    def build_interface(self) -> dict[str, Any]:
        """Build the feed display interface components.

        Returns:
            Dictionary of Gradio components for the feed interface
        """
        # Feed type selector
        feed_type = gr.Radio(
            label="Feed Type",
            choices=["RSS Feeds", "CVE Database", "MITRE ATT&CK", "Forums"],
            value="RSS Feeds",
            elem_id="feed-type",
        )

        # Feed filter controls
        with gr.Row():
            feed_search = gr.Textbox(
                label="Search Feeds",
                placeholder="Enter search terms...",
                elem_id="feed-search",
            )

            severity_filter = gr.Dropdown(
                label="Severity Filter",
                choices=["All", "Critical", "High", "Medium", "Low"],
                value="All",
                visible=False,  # Only visible for CVE
                elem_id="severity-filter",
            )

            category_filter = gr.Dropdown(
                label="Category Filter",
                choices=["All", "Security", "News", "Updates", "Research"],
                value="All",
                elem_id="category-filter",
            )

        # Refresh controls
        with gr.Row():
            refresh_feeds_btn = gr.Button(
                "Refresh Feeds", variant="primary", elem_id="refresh-feeds-btn"
            )

            auto_refresh = gr.Checkbox(
                label="Auto-refresh (5 min)", value=False, elem_id="auto-refresh"
            )

        # Feed display area
        feed_display = gr.HTML(label="Feed Content", elem_id="feed-display")

        # Feed statistics
        with gr.Accordion("Feed Statistics", open=False):
            feed_stats = gr.HTML(label="Statistics", elem_id="feed-stats")

        # Store component references
        self._store_component_ref("feed_type", feed_type)
        self._store_component_ref("feed_search", feed_search)
        self._store_component_ref("severity_filter", severity_filter)
        self._store_component_ref("category_filter", category_filter)
        self._store_component_ref("refresh_feeds_btn", refresh_feeds_btn)
        self._store_component_ref("auto_refresh", auto_refresh)
        self._store_component_ref("feed_display", feed_display)
        self._store_component_ref("feed_stats", feed_stats)

        self._mark_built()

        return self._component_refs

    def register_events(self, demo: gr.Blocks) -> None:
        """Register event handlers for the feed component.

        Args:
            demo: The main gr.Blocks context
        """
        if not self.is_built():
            raise RuntimeError("Component must be built before registering events")

        # Get component references
        feed_type = self._component_refs["feed_type"]
        feed_search = self._component_refs["feed_search"]
        severity_filter = self._component_refs["severity_filter"]
        category_filter = self._component_refs["category_filter"]
        refresh_feeds_btn = self._component_refs["refresh_feeds_btn"]
        auto_refresh = self._component_refs["auto_refresh"]
        feed_display = self._component_refs["feed_display"]
        feed_stats = self._component_refs["feed_stats"]

        # Feed type change
        feed_type.change(
            fn=self._handle_feed_type_change,
            inputs=[feed_type],
            outputs=[feed_display, severity_filter, category_filter],
        )

        # Search and filter
        feed_search.change(
            fn=self._handle_feed_search,
            inputs=[feed_type, feed_search, severity_filter, category_filter],
            outputs=[feed_display],
        )

        severity_filter.change(
            fn=self._handle_filter_change,
            inputs=[feed_type, feed_search, severity_filter, category_filter],
            outputs=[feed_display],
        )

        category_filter.change(
            fn=self._handle_filter_change,
            inputs=[feed_type, feed_search, severity_filter, category_filter],
            outputs=[feed_display],
        )

        # Refresh feeds
        refresh_feeds_btn.click(
            fn=self._handle_refresh_feeds,
            inputs=[feed_type],
            outputs=[feed_display, feed_stats],
        )

        # Auto-refresh toggle
        auto_refresh.change(
            fn=self._handle_auto_refresh_toggle, inputs=[auto_refresh], outputs=[]
        )

        logger.debug(f"Registered events for {self.component_id}")

    def get_component_refs(self) -> dict[str, Any]:
        """Get references to this component's Gradio components.

        Returns:
            Dictionary mapping component names to Gradio components
        """
        return self._component_refs.copy()

    def _handle_feed_type_change(self, feed_type: str):
        """Handle feed type selection change.

        Args:
            feed_type: Selected feed type

        Returns:
            Tuple of (feed display HTML, severity filter visibility, category filter choices)
        """
        # Show severity filter only for CVE
        severity_visible = gr.update(visible=(feed_type == "CVE Database"))

        # Update category filter based on feed type
        if feed_type == "RSS Feeds":
            categories = ["All", "Security", "News", "Updates", "Research"]
        elif feed_type == "MITRE ATT&CK":
            categories = ["All", "Tactics", "Techniques", "Procedures", "Mitigations"]
        elif feed_type == "Forums":
            categories = ["All", "Security", "General", "Announcements"]
        else:
            categories = ["All"]

        category_update = gr.update(choices=categories, value="All")

        # Get feed content
        feed_html = self._get_feed_display(feed_type)

        return feed_html, severity_visible, category_update

    def _handle_feed_search(
        self, feed_type: str, search_term: str, severity: str, category: str
    ) -> str:
        """Handle feed search.

        Args:
            feed_type: Current feed type
            search_term: Search query
            severity: Severity filter (CVE only)
            category: Category filter

        Returns:
            Updated feed display HTML
        """
        return self._get_feed_display(feed_type, search_term, severity, category)

    def _handle_filter_change(
        self, feed_type: str, search_term: str, severity: str, category: str
    ) -> str:
        """Handle filter changes.

        Args:
            feed_type: Current feed type
            search_term: Current search query
            severity: Severity filter
            category: Category filter

        Returns:
            Updated feed display HTML
        """
        return self._get_feed_display(feed_type, search_term, severity, category)

    def _handle_refresh_feeds(self, feed_type: str):
        """Handle feed refresh.

        Args:
            feed_type: Current feed type

        Returns:
            Tuple of (updated feed HTML, updated statistics HTML)
        """
        logger.info(f"Refreshing {feed_type} feeds")

        if self.feeds_service:
            try:
                # Refresh data from actual feed service
                self.feeds_service.refresh_feeds(feed_type)
            except Exception as e:
                logger.error(f"Failed to refresh feeds: {e}")

        feed_html = self._get_feed_display(feed_type)
        stats_html = self._get_feed_statistics(feed_type)

        return feed_html, stats_html

    def _handle_auto_refresh_toggle(self, enabled: bool) -> None:
        """Handle auto-refresh toggle.

        Args:
            enabled: Whether auto-refresh is enabled
        """
        if enabled:
            logger.info("Auto-refresh enabled (5-minute intervals)")
            self._auto_refresh_enabled = True
            # Start auto-refresh timer in a separate thread
            self._start_auto_refresh_timer()
        else:
            logger.info("Auto-refresh disabled")
            self._auto_refresh_enabled = False

    def _start_auto_refresh_timer(self):
        """Start auto-refresh timer (5 minutes)."""
        if hasattr(self, "_auto_refresh_enabled") and self._auto_refresh_enabled:
            # Schedule next refresh
            import threading

            timer = threading.Timer(300.0, self._start_auto_refresh_timer)  # 5 minutes
            timer.daemon = True
            timer.start()

            # Trigger refresh if feeds service is available
            if self.feeds_service:
                try:
                    self.feeds_service.refresh_all_feeds()
                    logger.debug("Auto-refresh completed")
                except Exception as e:
                    logger.error(f"Auto-refresh failed: {e}")

    def _get_feed_display(
        self,
        feed_type: str,
        search_term: str = "",
        severity: str = "All",
        category: str = "All",
    ) -> str:
        """Generate feed display HTML.

        Args:
            feed_type: Type of feed to display
            search_term: Optional search filter
            severity: Optional severity filter (CVE only)
            category: Optional category filter

        Returns:
            HTML string for feed display
        """
        # Determine which feed format to use
        if feed_type == "RSS Feeds":
            html = self._format_rss_display(search_term, category)
        elif feed_type == "CVE Database":
            html = self._format_cve_display(severity, search_term)
        elif feed_type == "MITRE ATT&CK":
            html = self._format_mitre_display(search_term, category)
        elif feed_type == "Forums":
            html = self._format_forum_display(search_term, category)
        else:
            html = "<div class='error'><p>Unknown feed type selected</p></div>"

        return html

    def _format_rss_display(self, search_term: str = "", category: str = "All") -> str:
        """Format RSS feed display with search and category filtering.

        Args:
            search_term: Search filter text
            category: Category filter

        Returns:
            HTML string for RSS feed display
        """
        if self.feeds_service:
            try:
                feeds_data = self.feeds_service.get_rss_feeds()
                if search_term:
                    feeds_data = [
                        feed
                        for feed in feeds_data
                        if search_term.lower() in feed.get("title", "").lower()
                        or search_term.lower() in feed.get("description", "").lower()
                    ]

                if category != "All":
                    feeds_data = [
                        feed
                        for feed in feeds_data
                        if feed.get("category", "").lower() == category.lower()
                    ]

                return self._render_rss_html(feeds_data)
            except Exception as e:
                logger.error(f"Failed to get RSS feeds: {e}")
                return (
                    f"<div class='error'><p>Error loading RSS feeds: {e!s}</p></div>"
                )

        return """
        <div class="feed-display">
            <h3>📰 RSS Security Feeds</h3>
            <div class="no-data">
                <p>No RSS feeds service configured.</p>
                <p>Configure RSS feeds in your settings to view security news and updates.</p>
            </div>
        </div>
        """

    def _render_rss_html(self, feeds_data: list) -> str:
        """Render RSS feeds as HTML."""
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
            description = feed.get("description", "No description available")[:200]
            published = feed.get("published", "Unknown date")
            source = feed.get("source", "Unknown source")

            html += f"""
            <div class="feed-item">
                <h4><a href="{link}" target="_blank" rel="noopener">{title}</a></h4>
                <p class="feed-meta">
                    <span class="source">📡 {source}</span> | 
                    <span class="date">📅 {published}</span>
                </p>
                <p class="feed-description">{description}...</p>
            </div>
            """

        html += "</div>"
        return html

    def _format_cve_display(self, severity: str = "All", search_term: str = "") -> str:
        """Format CVE display with severity and search filtering.

        Args:
            severity: Severity filter (Critical, High, Medium, Low, All)
            search_term: Search filter text

        Returns:
            HTML string for CVE display
        """
        if self.feeds_service:
            try:
                cve_data = self.feeds_service.get_cve_data()

                # Apply severity filter
                if severity != "All":
                    cve_data = [
                        cve
                        for cve in cve_data
                        if cve.get("severity", "").lower() == severity.lower()
                    ]

                # Apply search filter
                if search_term:
                    cve_data = [
                        cve
                        for cve in cve_data
                        if search_term.lower() in cve.get("id", "").lower()
                        or search_term.lower() in cve.get("description", "").lower()
                    ]

                return self._render_cve_html(cve_data)
            except Exception as e:
                logger.error(f"Failed to get CVE data: {e}")
                return (
                    f"<div class='error'><p>Error loading CVE data: {e!s}</p></div>"
                )

        return """
        <div class="feed-display">
            <h3>🔍 CVE Database</h3>
            <div class="no-data">
                <p>No CVE service configured.</p>
                <p>Configure CVE data source to view vulnerability information.</p>
            </div>
        </div>
        """

    def _render_cve_html(self, cve_data: list) -> str:
        """Render CVE data as HTML."""
        if not cve_data:
            return """
            <div class="feed-display">
                <h3>🔍 CVE Database</h3>
                <p>No CVE entries found matching your criteria.</p>
            </div>
            """

        html = '<div class="cve-display"><h3>🔍 CVE Database</h3>'
        for cve in cve_data[:15]:  # Limit to 15 CVEs
            cve_id = cve.get("id", "Unknown ID")
            severity = cve.get("severity", "Unknown")
            score = cve.get("score", "N/A")
            description = cve.get("description", "No description available")[:300]
            published = cve.get("published", "Unknown date")

            severity_class = severity.lower()
            severity_color = {
                "critical": "#dc3545",
                "high": "#fd7e14",
                "medium": "#ffc107",
                "low": "#28a745",
            }.get(severity_class, "#6c757d")

            html += f"""
            <div class="cve-item" style="border-left: 4px solid {severity_color};">
                <h4>{cve_id} <span class="severity {severity_class}" style="color: {severity_color};">({severity})</span></h4>
                <p class="cve-score">⚡ CVSS Score: {score}</p>
                <p class="cve-description">{description}...</p>
                <p class="cve-date">📅 Published: {published}</p>
            </div>
            """

        html += "</div>"
        return html

    def _format_mitre_display(
        self, search_term: str = "", category: str = "All"
    ) -> str:
        """Format MITRE ATT&CK display with search and category filtering.

        Args:
            search_term: Search filter text
            category: Category filter (Tactics, Techniques, etc.)

        Returns:
            HTML string for MITRE ATT&CK display
        """
        if self.feeds_service:
            try:
                mitre_data = self.feeds_service.get_mitre_data()

                # Apply category filter
                if category != "All":
                    mitre_data = [
                        item
                        for item in mitre_data
                        if item.get("type", "").lower() == category.lower()
                    ]

                # Apply search filter
                if search_term:
                    mitre_data = [
                        item
                        for item in mitre_data
                        if search_term.lower() in item.get("name", "").lower()
                        or search_term.lower() in item.get("description", "").lower()
                    ]

                return self._render_mitre_html(mitre_data)
            except Exception as e:
                logger.error(f"Failed to get MITRE data: {e}")
                return f"<div class='error'><p>Error loading MITRE data: {e!s}</p></div>"

        return """
        <div class="feed-display">
            <h3>⚔️ MITRE ATT&CK Framework</h3>
            <div class="no-data">
                <p>No MITRE ATT&CK service configured.</p>
                <p>Configure MITRE data source to view threat intelligence.</p>
            </div>
        </div>
        """

    def _render_mitre_html(self, mitre_data: list) -> str:
        """Render MITRE ATT&CK data as HTML."""
        if not mitre_data:
            return """
            <div class="feed-display">
                <h3>⚔️ MITRE ATT&CK Framework</h3>
                <p>No MITRE ATT&CK data found matching your criteria.</p>
            </div>
            """

        html = '<div class="mitre-display"><h3>⚔️ MITRE ATT&CK Framework</h3>'
        for item in mitre_data[:12]:  # Limit to 12 items
            technique_id = item.get("id", "Unknown ID")
            name = item.get("name", "Unknown Technique")
            tactic = item.get("tactic", "Unknown Tactic")
            description = item.get("description", "No description available")[:250]
            platforms = item.get("platforms", [])

            platforms_str = ", ".join(platforms[:3]) if platforms else "Unknown"
            if len(platforms) > 3:
                platforms_str += f" (+{len(platforms)-3} more)"

            html += f"""
            <div class="mitre-item">
                <h4>🎯 {technique_id}: {name}</h4>
                <p class="mitre-tactic">📋 Tactic: <strong>{tactic}</strong></p>
                <p class="mitre-description">{description}...</p>
                <p class="mitre-platforms">💻 Platforms: {platforms_str}</p>
            </div>
            """

        html += "</div>"
        return html

    def _format_forum_display(
        self, search_term: str = "", category: str = "All"
    ) -> str:
        """Format forum display with search and category filtering.

        Args:
            search_term: Search filter text
            category: Category filter

        Returns:
            HTML string for forum display
        """
        if self.feeds_service:
            try:
                forum_data = self.feeds_service.get_forum_data()

                # Apply category filter
                if category != "All":
                    forum_data = [
                        post
                        for post in forum_data
                        if post.get("category", "").lower() == category.lower()
                    ]

                # Apply search filter
                if search_term:
                    forum_data = [
                        post
                        for post in forum_data
                        if search_term.lower() in post.get("title", "").lower()
                        or search_term.lower() in post.get("content", "").lower()
                    ]

                return self._render_forum_html(forum_data)
            except Exception as e:
                logger.error(f"Failed to get forum data: {e}")
                return f"<div class='error'><p>Error loading forum data: {e!s}</p></div>"

        return """
        <div class="feed-display">
            <h3>💬 Security Forums</h3>
            <div class="no-data">
                <p>No forum service configured.</p>
                <p>Configure forum data source to view community discussions.</p>
            </div>
        </div>
        """

    def _render_forum_html(self, forum_data: list) -> str:
        """Render forum posts as HTML."""
        if not forum_data:
            return """
            <div class="feed-display">
                <h3>💬 Security Forums</h3>
                <p>No forum posts found matching your criteria.</p>
            </div>
            """

        html = '<div class="forum-display"><h3>💬 Security Forums</h3>'
        for post in forum_data[:10]:  # Limit to 10 posts
            title = post.get("title", "No Title")
            url = post.get("url", "#")
            author = post.get("author", "Unknown Author")
            forum_name = post.get("forum", "Unknown Forum")
            date = post.get("date", "Unknown Date")
            content = post.get("content", "No content available")[:200]
            replies = post.get("replies", 0)
            views = post.get("views", 0)

            html += f"""
            <div class="forum-post">
                <h4><a href="{url}" target="_blank" rel="noopener">💬 {title}</a></h4>
                <p class="post-meta">
                    <span class="author">👤 {author}</span> | 
                    <span class="forum">🏛️ {forum_name}</span> | 
                    <span class="date">📅 {date}</span>
                </p>
                <p class="post-preview">{content}...</p>
                <p class="post-stats">
                    <span class="replies">💬 {replies} replies</span> | 
                    <span class="views">👁️ {views} views</span>
                </p>
            </div>
            """

        html += "</div>"
        return html

    def _get_feed_statistics(self, feed_type: str) -> str:
        """Generate feed statistics HTML.

        Args:
            feed_type: Type of feed

        Returns:
            HTML string for statistics display
        """
        from datetime import datetime

        if self.feeds_service:
            try:
                stats = self.feeds_service.get_feed_statistics(feed_type)
                total_items = stats.get("total_items", 0)
                last_updated = stats.get("last_updated", "Never")
                error_count = stats.get("errors", 0)
                active_sources = stats.get("active_sources", 0)

                return f"""
                <div class="feed-stats">
                    <h4>📊 Statistics for {feed_type}</h4>
                    <div class="stats-grid">
                        <p><strong>📈 Total Items:</strong> {total_items:,}</p>
                        <p><strong>🔄 Last Updated:</strong> {last_updated}</p>
                        <p><strong>📡 Active Sources:</strong> {active_sources}</p>
                        <p><strong>⚠️ Errors:</strong> {error_count}</p>
                    </div>
                </div>
                """
            except Exception as e:
                logger.error(f"Failed to get statistics: {e}")
                return f"""
                <div class="feed-stats">
                    <h4>📊 Statistics for {feed_type}</h4>
                    <p class="error">Error loading statistics: {e!s}</p>
                </div>
                """

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
        <div class="feed-stats">
            <h4>📊 Statistics for {feed_type}</h4>
            <div class="stats-grid">
                <p><strong>📈 Total Items:</strong> 0</p>
                <p><strong>🔄 Last Updated:</strong> {current_time}</p>
                <p><strong>📡 Status:</strong> No service configured</p>
                <p><strong>⚠️ Errors:</strong> Service unavailable</p>
            </div>
        </div>
        """
