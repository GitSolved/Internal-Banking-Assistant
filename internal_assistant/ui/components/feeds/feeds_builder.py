"""Feeds Component Builder.

This module contains the FeedsComponentBuilder class that handles
RSS feeds, CVE data, MITRE ATT&CK, and forum display components
for the Internal Assistant UI system.

Author: Internal Assistant Team
Version: 0.6.2
"""

import logging
import gradio as gr
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeedsComponentBuilder:
    """
    Builder class for feed display interface components.

    This class provides methods to build various feed-related UI elements
    including RSS displays, CVE data, MITRE ATT&CK, and forum content.
    """

    def __init__(self, services: Dict[str, Any]):
        """
        Initialize the feeds builder.

        Args:
            services: Dictionary of available services
        """
        self.services = services
        self.feeds_service = services.get("feeds")
        self.cve_service = services.get("cve")
        self.mitre_service = services.get("mitre")

    def build_feeds_interface(self) -> tuple:
        """
        Build feeds display interface components.

        Returns:
            Tuple of Gradio components for feeds display
        """
        with gr.Column():
            # Feed type selector
            feed_type_selector = gr.Radio(
                label="Select Feed Type",
                choices=["RSS Feeds", "CVE Database", "MITRE ATT&CK", "Forums"],
                value="RSS Feeds",
                elem_id="feed-type-selector",
            )

            # Filter controls
            with gr.Row():
                feed_search = gr.Textbox(
                    label="Search Feeds",
                    placeholder="Search by keywords...",
                    elem_id="feed-search-box",
                )

                severity_filter = gr.Dropdown(
                    label="Severity",
                    choices=["All", "Critical", "High", "Medium", "Low"],
                    value="All",
                    visible=False,
                    elem_id="severity-filter",
                )

            # Refresh controls
            with gr.Row():
                refresh_btn = gr.Button(
                    "Refresh Feeds", variant="primary", elem_id="refresh-feeds"
                )

                auto_refresh_toggle = gr.Checkbox(
                    label="Auto-refresh every 5 minutes",
                    value=False,
                    elem_id="auto-refresh-toggle",
                )

            # Feed display area
            feeds_display = gr.HTML(
                value=self._get_default_feeds_html(), elem_id="feeds-display-area"
            )

        return (
            feed_type_selector,
            feed_search,
            severity_filter,
            refresh_btn,
            auto_refresh_toggle,
            feeds_display,
        )

    def format_feeds_display(
        self, feed_type: str, search_term: str = "", severity: str = "All"
    ) -> str:
        """
        Format feed display based on type and filters.

        Args:
            feed_type: Type of feed to display
            search_term: Search filter
            severity: Severity filter (for CVE feeds)

        Returns:
            HTML string for feed display
        """
        if feed_type == "RSS Feeds":
            return self._format_rss_feeds(search_term)
        elif feed_type == "CVE Database":
            return self._format_cve_display(severity, search_term)
        elif feed_type == "MITRE ATT&CK":
            return self._format_mitre_display(search_term)
        elif feed_type == "Forums":
            return self._format_forum_display(search_term)
        else:
            return self._get_default_feeds_html()

    def _format_rss_feeds(self, search_term: str = "") -> str:
        """
        Format RSS feeds for display.

        Args:
            search_term: Optional search filter

        Returns:
            HTML string with RSS feed content
        """
        if self.feeds_service:
            try:
                # Get feed data from service
                feeds_data = self._get_sample_rss_data()

                if search_term:
                    feeds_data = [
                        feed
                        for feed in feeds_data
                        if search_term.lower() in feed["title"].lower()
                        or search_term.lower() in feed["description"].lower()
                    ]

                return self._render_rss_html(feeds_data)
            except Exception as e:
                logger.error(f"Failed to format RSS feeds: {e}")
                return f"<p>Error loading RSS feeds: {str(e)}</p>"

        return self._render_rss_html(self._get_sample_rss_data())

    def _format_cve_display(self, severity: str = "All", search_term: str = "") -> str:
        """
        Format CVE data for display.

        Args:
            severity: Severity filter
            search_term: Search filter

        Returns:
            HTML string with CVE data
        """
        cve_data = self._get_sample_cve_data()

        # Apply filters
        if severity != "All":
            cve_data = [cve for cve in cve_data if cve["severity"] == severity]

        if search_term:
            cve_data = [
                cve
                for cve in cve_data
                if search_term.lower() in cve["id"].lower()
                or search_term.lower() in cve["description"].lower()
            ]

        return self._render_cve_html(cve_data)

    def _format_mitre_display(self, search_term: str = "") -> str:
        """
        Format MITRE ATT&CK data for display.

        Args:
            search_term: Search filter

        Returns:
            HTML string with MITRE data
        """
        mitre_data = self._get_sample_mitre_data()

        if search_term:
            mitre_data = [
                item
                for item in mitre_data
                if search_term.lower() in item["name"].lower()
                or search_term.lower() in item["description"].lower()
            ]

        return self._render_mitre_html(mitre_data)

    def _format_forum_display(self, search_term: str = "") -> str:
        """
        Format forum content for display.

        Args:
            search_term: Search filter

        Returns:
            HTML string with forum content
        """
        forum_data = self._get_sample_forum_data()

        if search_term:
            forum_data = [
                post
                for post in forum_data
                if search_term.lower() in post["title"].lower()
                or search_term.lower() in post["content"].lower()
            ]

        return self._render_forum_html(forum_data)

    def _render_rss_html(self, feeds_data: List[Dict]) -> str:
        """Render RSS feeds as HTML."""
        if not feeds_data:
            return "<div class='no-feeds'><p>No RSS feeds found.</p></div>"

        html = '<div class="rss-feeds">'
        for feed in feeds_data:
            html += f"""
            <div class="feed-item">
                <h4><a href="{feed['link']}" target="_blank">{feed['title']}</a></h4>
                <p class="feed-meta">
                    <span class="source">{feed['source']}</span> | 
                    <span class="date">{feed['date']}</span>
                </p>
                <p class="feed-description">{feed['description']}</p>
            </div>
            """
        html += "</div>"
        return html

    def _render_cve_html(self, cve_data: List[Dict]) -> str:
        """Render CVE data as HTML."""
        if not cve_data:
            return "<div class='no-cves'><p>No CVE entries found.</p></div>"

        html = '<div class="cve-list">'
        for cve in cve_data:
            severity_class = cve["severity"].lower()
            html += f"""
            <div class="cve-item severity-{severity_class}">
                <h4>{cve['id']} - <span class="severity {severity_class}">{cve['severity']}</span></h4>
                <p class="cve-score">CVSS Score: {cve['score']}</p>
                <p class="cve-description">{cve['description']}</p>
                <p class="cve-date">Published: {cve['published']}</p>
            </div>
            """
        html += "</div>"
        return html

    def _render_mitre_html(self, mitre_data: List[Dict]) -> str:
        """Render MITRE ATT&CK data as HTML."""
        if not mitre_data:
            return "<div class='no-mitre'><p>No MITRE ATT&CK data found.</p></div>"

        html = '<div class="mitre-techniques">'
        for item in mitre_data:
            html += f"""
            <div class="mitre-item">
                <h4>{item['id']}: {item['name']}</h4>
                <p class="mitre-tactic">Tactic: {item['tactic']}</p>
                <p class="mitre-description">{item['description']}</p>
                <div class="mitre-platforms">
                    <strong>Platforms:</strong> {', '.join(item['platforms'])}
                </div>
            </div>
            """
        html += "</div>"
        return html

    def _render_forum_html(self, forum_data: List[Dict]) -> str:
        """Render forum posts as HTML."""
        if not forum_data:
            return "<div class='no-posts'><p>No forum posts found.</p></div>"

        html = '<div class="forum-posts">'
        for post in forum_data:
            html += f"""
            <div class="forum-post">
                <h4><a href="{post['url']}" target="_blank">{post['title']}</a></h4>
                <p class="post-meta">
                    <span class="author">By {post['author']}</span> | 
                    <span class="forum">{post['forum']}</span> | 
                    <span class="date">{post['date']}</span>
                </p>
                <p class="post-preview">{post['content'][:200]}...</p>
                <p class="post-stats">Replies: {post['replies']} | Views: {post['views']}</p>
            </div>
            """
        html += "</div>"
        return html

    def _get_default_feeds_html(self) -> str:
        """Get default HTML for feeds display."""
        return """
        <div class="feeds-default">
            <div class="welcome-message">
                <h3>🌐 Threat Intelligence Feeds</h3>
                <p>Select a feed type above to view the latest security information.</p>
                <ul>
                    <li>📰 <strong>RSS Feeds:</strong> Latest security news and updates</li>
                    <li>🔍 <strong>CVE Database:</strong> Common Vulnerabilities and Exposures</li>
                    <li>⚔️ <strong>MITRE ATT&CK:</strong> Threat actor tactics and techniques</li>
                    <li>💬 <strong>Forums:</strong> Community discussions and insights</li>
                </ul>
            </div>
        </div>
        """

    def _get_sample_rss_data(self) -> List[Dict]:
        """Get sample RSS feed data."""
        return [
            {
                "title": "Critical Security Update Released",
                "link": "https://example.com/security-update",
                "description": "A critical security vulnerability has been patched in the latest software release.",
                "source": "Security News",
                "date": "2024-01-15",
            },
            {
                "title": "New Threat Actor Campaign Discovered",
                "link": "https://example.com/threat-campaign",
                "description": "Researchers have identified a new APT campaign targeting financial institutions.",
                "source": "Threat Intel",
                "date": "2024-01-14",
            },
        ]

    def _get_sample_cve_data(self) -> List[Dict]:
        """Get sample CVE data."""
        return [
            {
                "id": "CVE-2024-0001",
                "severity": "Critical",
                "score": "9.8",
                "description": "Remote code execution vulnerability in web application framework",
                "published": "2024-01-15",
            },
            {
                "id": "CVE-2024-0002",
                "severity": "High",
                "score": "8.5",
                "description": "Privilege escalation vulnerability in operating system kernel",
                "published": "2024-01-14",
            },
        ]

    def _get_sample_mitre_data(self) -> List[Dict]:
        """Get sample MITRE ATT&CK data."""
        return [
            {
                "id": "T1059",
                "name": "Command and Scripting Interpreter",
                "tactic": "Execution",
                "description": "Adversaries may abuse command interpreters to execute commands and scripts.",
                "platforms": ["Windows", "Linux", "macOS"],
            },
            {
                "id": "T1055",
                "name": "Process Injection",
                "tactic": "Defense Evasion",
                "description": "Adversaries may inject code into processes to evade detection.",
                "platforms": ["Windows", "Linux", "macOS"],
            },
        ]

    def _get_sample_forum_data(self) -> List[Dict]:
        """Get sample forum data."""
        return [
            {
                "title": "Discussion: Latest Malware Trends",
                "url": "https://forum.example.com/malware-trends",
                "author": "SecurityExpert",
                "forum": "Malware Analysis",
                "date": "2024-01-15",
                "content": "What are the latest malware trends you've observed in your environment?",
                "replies": 23,
                "views": 456,
            },
            {
                "title": "Zero-day Vulnerability Disclosure Process",
                "url": "https://forum.example.com/zero-day-process",
                "author": "ResearcherJohn",
                "forum": "Vulnerability Research",
                "date": "2024-01-14",
                "content": "Best practices for responsible vulnerability disclosure in enterprise environments.",
                "replies": 15,
                "views": 287,
            },
        ]
