"""
Display Utility Builder Component

This module contains display utility functions extracted from ui.py
during Phase 1C.1 of the UI refactoring project.

Extracted from ui.py lines:
- _format_simple_forum_display() (lines 453-517)
- _format_cve_display() (lines 597-743)
- _format_mitre_display() (lines 744+)
- _get_simple_forum_data() (lines 519-595)

Author: UI Refactoring Team
Date: 2025-01-19
Phase: 1C.1 - Simple Display Functions Extraction
"""

import logging
import re
from typing import Optional, Any, Dict, List

from internal_assistant.server.feeds.feeds_service import RSSFeedService

logger = logging.getLogger(__name__)


class DisplayUtilityBuilder:
    """
    Builder class for display utility functions.
    Handles formatting for forum, CVE, and MITRE displays.
    """

    def __init__(self, feeds_service: RSSFeedService, threat_analyzer=None):
        """
        Initialize the DisplayUtilityBuilder.

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
                logger.debug("ThreatIntelligenceAnalyzer loaded for MITRE integration in DisplayUtilityBuilder")
            except Exception as e:
                logger.warning(f"Could not load ThreatIntelligenceAnalyzer: {e}")
                self._threat_analyzer = None

    def format_simple_forum_display(self) -> str:
        """Format forum directory display with beautiful RSS feed-style styling."""
        try:
            # Get ALL forum data with no limits
            forums_data = self.get_simple_forum_data()

            if not forums_data:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🌐 No forum directory available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load forum directory
                        </div>
                    </div>
                </div>"""

            # Beautiful header matching RSS feed style
            total_count = len(forums_data)
            html_content = f"""<div class='feed-content'>
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' 
                        style='color: #FF6B35; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                        🌐 Tor Taxi ({total_count} forums)
                    </h4>
                </div>
            """

            # Display forums with beautiful RSS feed-style formatting
            for forum in forums_data:
                forum_name = forum.get("name", "Unknown Forum")
                forum_url = forum.get("url", "")

                if not forum_url:
                    continue

                # Condensed forum item styling - title and link on same line
                html_content += f"""
                <div class='feed-item' style='margin-bottom: 8px; padding: 8px; border-left: 3px solid #FF6B35; background: #1a1a1a;'>
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        <span style='color: #FF6B35; font-weight: bold; font-size: 16px; min-width: 120px;'>
                            🔗 {forum_name}
                        </span>
                        <span style='color: #666; font-family: monospace; font-size: 15px; flex: 1;'>
                            {forum_url}
                        </span>
                    </div>
                </div>"""

            html_content += "</div>"

            # Removed copy functionality - simplified display
            html_content += ""

            return html_content

        except Exception as e:
            logger.error(f"Error formatting forum directory: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading forum directory</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def get_simple_forum_data(self) -> List[Dict[str, str]]:
        """Get forum data from the forum service or fallback to complete sample data."""
        try:
            # Try to get forum service from dependency injection
            from internal_assistant.di import global_injector

            try:
                # Try the simple forum service first
                from internal_assistant.server.feeds.simple_forum_service import (
                    SimpleForumDirectoryService,
                )

                forum_service = global_injector.get(SimpleForumDirectoryService)
                forums = forum_service.get_forums()

                if forums:
                    logger.info(
                        f"Retrieved {len(forums)} forums from SimpleForumDirectoryService"
                    )
                    # Convert to the format expected by UI
                    return [
                        {
                            "name": forum.get("name", "Unknown"),
                            "url": forum.get("onion_link", ""),
                        }
                        for forum in forums
                        if forum.get("onion_link")
                    ]

            except Exception as e:
                logger.debug(f"SimpleForumDirectoryService not available: {e}")

            try:
                # Try the main forum directory service
                from internal_assistant.server.feeds.forum_directory_service import (
                    ForumDirectoryService,
                )

                forum_service = global_injector.get(ForumDirectoryService)
                forums = forum_service.get_forums()

                if forums:
                    logger.info(
                        f"Retrieved {len(forums)} forums from ForumDirectoryService"
                    )
                    # Convert ForumLink objects to dict format
                    return [
                        {
                            "name": getattr(forum, "name", "Unknown"),
                            "url": getattr(forum, "onion_link", "")
                            or getattr(forum, "url", ""),
                        }
                        for forum in forums
                    ]

            except Exception as e:
                logger.debug(f"ForumDirectoryService not available: {e}")

        except Exception as e:
            logger.warning(f"Could not access forum services: {e}")

        # Fallback to complete sample data with ALL known forums
        logger.info("Using fallback forum data with complete forum list")
        return [
            {
                "name": "Dread",
                "url": "dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion",
            },
            {
                "name": "Pitch - 2",
                "url": "n7vermpu3kwcgz527x265cpkwq4h2jtgynq7qdrvm3erdx7p4ifqd.onion",
            },
            {
                "name": "NZ Darknet Market Forum",
                "url": "nzmarketbf5k4z7b2xcdaovacm3kj2apcpw7yxjqggdwt5q2evtj55oad.onion",
            },
            {
                "name": "Germania",
                "url": "germaniadhqfm5cnqyc7jq7qcklbvdkk5r7nfq6g5whpvkpxhqtb4xd.onion",
            },
            {
                "name": "EndChan",
                "url": "enxx3byspwsdo446jujc52ucy2pf5urdbhqw3kbsfhlfjwmbpj5smdad.onion",
            },
            {
                "name": "XSS.is",
                "url": "xssforever4s7z6ennrfmyfkwq2qmbtmdpbclvfzqqrxzpcaxtpnqmpqad.onion",
            },
        ]

    def get_mitre_data(self) -> dict:
        """Get MITRE ATT&CK data using ThreatIntelligenceAnalyzer."""
        try:
            # Get MITRE data from threat analyzer using dependency injection
            from internal_assistant.di import global_injector
            from internal_assistant.server.threat_intelligence.threat_analyzer import (
                ThreatIntelligenceAnalyzer,
            )

            threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)
            return threat_analyzer.get_mitre_data()
        except Exception as e:
            logger.error(f"Error getting MITRE data: {e}")
            return {}

    def format_cve_display(
        self,
        source_filter: str = None,
        severity_filter: str = "All Severities",
        vendor_filter: str = "All Vendors",
        days_filter: int = 30,
    ) -> str:
        """Format CVE data for display in the UI."""
        try:
            # Get CVE data from feeds service, specifically Microsoft Security
            feeds = self._feeds_service.get_feeds(
                "Microsoft Security", days_filter
            )  # Get Microsoft Security feeds with time filter

            # Additional filter: Ensure ONLY Microsoft Security items
            feeds = [f for f in feeds if f.get("source") == "Microsoft Security"]

            if not feeds:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🔍 No Microsoft Security CVE data available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest Microsoft Security vulnerabilities
                        </div>
                    </div>
                </div>"""

            html_content = "<div class='feed-content'>"

            # Group feeds by source
            sources = {}
            for feed in feeds:
                source = feed["source"]
                # Double-check: ONLY Microsoft Security
                if source != "Microsoft Security":
                    continue
                if source not in sources:
                    sources[source] = []
                sources[source].append(feed)

            for source, source_feeds in sources.items():
                # Only show Microsoft Security for CVE panel (redundant but explicit)
                if source != "Microsoft Security":
                    continue

                # Source header with CVE-specific styling
                source_icons = {
                    "Microsoft Security": "🔒",
                }
                source_icon = source_icons.get(source, "🔍")

                # Get color from feeds service
                source_color = self._feeds_service.SOURCE_COLORS.get(source, "#0077BE")

                html_content += f"""
                <div class='feed-source-section'>
                    <h4 class='feed-source-header' data-source='{source}' 
                        style='color: {source_color}; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                        {source_icon} {source} ({len(source_feeds)} vulnerabilities)
                    </h4>
                </div>
                """

                # Feed items for this source
                for feed in source_feeds[
                    :15
                ]:  # Limit to 15 items per source for CVE panel
                    # Extract CVE ID if present in title or summary
                    cve_id = self.extract_cve_id(feed["title"] + " " + feed["summary"])

                    # Determine severity based on content
                    severity = self.determine_cve_severity(
                        feed["title"] + " " + feed["summary"]
                    )

                    published_date = feed.get("published", "Unknown Date")
                    title = feed.get("title", "No Title")
                    link = feed.get("link", "#")
                    summary = feed.get("summary", "No summary available")

                    # Truncate summary if too long for CVE display
                    if len(summary) > 150:
                        summary = summary[:150] + "..."

                    # Extract MITRE techniques for this CVE feed item
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

                            # Color based on confidence: high=green, medium=orange, low=red-orange
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

                    # Color code severity
                    severity_colors = {
                        "Critical": "#d32f2f",
                        "High": "#ff5722",
                        "Medium": "#ff9800",
                        "Low": "#4caf50",
                        "Unknown": "#666",
                    }
                    severity_color = severity_colors.get(severity, "#666")

                    html_content += f"""
                    <div class='feed-item' style='margin-bottom: 12px; padding: 10px; background: #1a1a1a; border-radius: 6px; border-left: 3px solid {source_color};'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;'>
                            <div style='display: flex; align-items: center; gap: 8px;'>
                                <span style='color: {severity_color}; font-size: 11px; font-weight: 600; background: rgba({severity_color.replace("#", "").replace(severity_color[1:3], str(int(severity_color[1:3], 16)))}40); padding: 2px 6px; border-radius: 3px;'>{severity}</span>
                                <span style='color: #888; font-size: 10px; font-family: monospace;'>{cve_id}</span>
                            </div>
                            <span style='color: #888; font-size: 10px; white-space: nowrap;'>{published_date}</span>
                        </div>
                        <h5 style='margin: 0 0 4px 0; color: #e0e0e0; font-size: 13px; font-weight: 600; line-height: 1.3;'>
                            <a href='{link}' target='_blank' style='color: inherit; text-decoration: none;'>{title}</a>
                        </h5>
                        <p style='margin: 0; color: #ccc; font-size: 11px; line-height: 1.3;'>{summary}</p>
                        {mitre_badges_html}
                    </div>
                    """

            html_content += "</div>"
            return html_content

        except Exception as e:
            logger.error(f"Error formatting CVE display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading CVE data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def extract_cve_id(self, text: str) -> str:
        """Extract CVE ID from text."""
        cve_pattern = r"CVE-\d{4}-\d{4,7}"
        match = re.search(cve_pattern, text, re.IGNORECASE)
        return match.group(0) if match else "CVE-XXXX-XXXX"

    def determine_cve_severity(self, text: str) -> str:
        """Determine CVE severity based on text content."""
        text_lower = text.lower()
        if any(
            word in text_lower
            for word in ["critical", "remote code execution", "privilege escalation"]
        ):
            return "Critical"
        elif any(
            word in text_lower for word in ["high", "elevation", "bypass", "spoofing"]
        ):
            return "High"
        elif any(
            word in text_lower
            for word in ["medium", "denial of service", "information disclosure"]
        ):
            return "Medium"
        elif any(word in text_lower for word in ["low", "security feature bypass"]):
            return "Low"
        else:
            return "Unknown"

    def format_mitre_display(
        self,
        domain_filter: str = "Enterprise",
        domain_focus: str = "All Domains",
        search_query: str = None,
        tactic_filter: str = "All Tactics",
        show_groups: bool = False,
        banking_focus: bool = False,
        mitre_data: dict = None,
    ) -> str:
        """
        Format MITRE ATT&CK data for display in the UI.

        Args:
            mitre_data: Optional cached MITRE data. If None, will attempt to get fresh data.
        """
        try:
            # Use provided data or get fresh data (fallback for compatibility)
            if mitre_data is None:
                from internal_assistant.di import global_injector
                from internal_assistant.server.threat_intelligence.threat_analyzer import (
                    ThreatIntelligenceAnalyzer,
                )

                threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)
                mitre_data = threat_analyzer.get_mitre_data()

            if not mitre_data:
                return """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🛡️ No MITRE ATT&CK data available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click the REFRESH button to load latest threat intelligence
                        </div>
                    </div>
                </div>"""

            html_content = "<div class='feed-content'>"

            if show_groups:
                # Display Threat Groups
                groups = mitre_data.get("groups", [])
                if groups:
                    html_content += f"""
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #FF0000; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🎯 {'Banking-Targeting ' if banking_focus else 'All '}Threat Groups ({len(groups)} groups)
                        </h4>
                    </div>
                    """

                    for group in groups[:10]:  # Limit to 10 groups
                        group_name = group.get("name", "Unknown Group")
                        group_id = group.get("group_id", "")
                        description = group.get(
                            "description", "No description available"
                        )
                        techniques = group.get("techniques", [])
                        targets = group.get("targets", [])

                        html_content += f"""
                        <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid #FF0000; background: #1a1a1a;'>
                            <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                                <span style='color: #FF0000; font-size: 14px; font-weight: bold; margin-right: 8px;'>
                                    🕵️ {group_name}
                                </span>
                                <a href='javascript:void(0)' onclick='confirmOpenExternal("{group.get("url", "")}", "{group_name}")' 
                                   style='color: #FF0000; text-decoration: none; font-size: 16px;'>
                                    {group_id}
                                </a>
                            </div>
                            <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                                {description[:120]}{'...' if len(description) > 120 else ''}
                            </div>
                            <div class='feed-meta' style='font-size: 12px; color: #888;'>
                                🔍 Techniques: {len(techniques)} • 🎯 Targets: {', '.join(targets[:3])}{'...' if len(targets) > 3 else ''}
                            </div>
                        </div>"""
                else:
                    html_content += """
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #FF0000; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🎯 No Threat Groups Available
                        </h4>
                    </div>
                    """
            else:
                # Display Techniques
                techniques = mitre_data.get("techniques", [])
                if techniques:
                    # Apply filters
                    filtered_techniques = []
                    for tech in techniques:
                        # Domain focus filter
                        if domain_focus != "All Domains" and tech.get(
                            "technique_id"
                        ) not in threat_analyzer.get_domain_techniques(domain_focus):
                            continue

                        # Search filter
                        if search_query:
                            search_lower = search_query.lower()
                            if not (
                                search_lower in tech.get("name", "").lower()
                                or search_lower in tech.get("technique_id", "").lower()
                                or search_lower in tech.get("description", "").lower()
                            ):
                                continue

                        # Tactic filter
                        if (
                            tactic_filter != "All Tactics"
                            and tech.get("tactic") != tactic_filter
                        ):
                            continue

                        filtered_techniques.append(tech)

                    if filtered_techniques:
                        html_content += f"""
                        <div class='feed-source-section'>
                            <h4 class='feed-source-header' 
                                style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                                🔍 {'Domain-Relevant ' if domain_focus != "All Domains" else 'All '}Techniques ({len(filtered_techniques)} techniques)
                            </h4>
                        </div>
                        """

                        for tech in filtered_techniques[:15]:  # Limit to 15 techniques
                            technique_id = tech.get("technique_id", "")
                            name = tech.get("name", "Unknown Technique")
                            description = tech.get(
                                "description", "No description available"
                            )
                            tactic = tech.get("tactic", "Unknown Tactic")
                            platforms = tech.get("platforms", [])

                            # Tactic color coding
                            tactic_colors = {
                                "Initial Access": "#FF0000",
                                "Execution": "#FF6B35",
                                "Persistence": "#FFA500",
                                "Privilege Escalation": "#FFFF00",
                                "Defense Evasion": "#00FF00",
                                "Credential Access": "#00FFFF",
                                "Discovery": "#0000FF",
                                "Lateral Movement": "#FF00FF",
                                "Collection": "#800080",
                                "Command & Control": "#008000",
                                "Exfiltration": "#800000",
                                "Impact": "#FF0000",
                            }
                            tactic_color = tactic_colors.get(tactic, "#0077BE")

                            html_content += f"""
                            <div class='feed-item' style='margin-bottom: 12px; padding: 8px; border-left: 3px solid {tactic_color}; background: #1a1a1a;'>
                                <div class='feed-title' style='font-weight: bold; margin-bottom: 4px;'>
                                    <span style='color: {tactic_color}; font-size: 14px; font-weight: bold; margin-right: 8px;'>
                                        🎯 {tactic}
                                    </span>
                                    <a href='javascript:void(0)' onclick='confirmOpenExternal("{tech.get("url", "")}", "{name}")' 
                                       style='color: {tactic_color}; text-decoration: none; font-size: 16px;'>
                                        {technique_id} - {name}
                                    </a>
                                </div>
                                <div class='feed-summary' style='font-size: 14px; color: #666; margin-bottom: 4px;'>
                                    {description[:120]}{'...' if len(description) > 120 else ''}
                                </div>
                                <div class='feed-meta' style='font-size: 12px; color: #888;'>
                                    💻 Platforms: {', '.join(platforms[:3])}{'...' if len(platforms) > 3 else ''}
                                </div>
                            </div>"""
                    else:
                        html_content += """
                        <div class='feed-source-section'>
                            <h4 class='feed-source-header' 
                                style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                                🔍 No Techniques Match Filters
                            </h4>
                        </div>
                        """
                else:
                    html_content += """
                    <div class='feed-source-section'>
                        <h4 class='feed-source-header' 
                            style='color: #0077BE; margin: 16px 0 8px 0; font-size: 18px; font-weight: bold;'>
                            🔍 No Techniques Available
                        </h4>
                    </div>
                    """

            html_content += "</div>"  # Close feed content

            return html_content

        except Exception as e:
            logger.error(f"Error formatting MITRE display: {e}")
            return f"""
            <div class='feed-content error'>
                <div style='text-align: center; color: #d32f2f; padding: 20px;'>
                    <div>⚠️ Error loading MITRE ATT&CK data</div>
                    <div style='font-size: 12px; margin-top: 8px;'>{str(e)}</div>
                </div>
            </div>"""

    def format_active_threats_display(self, days_filter: int = 7) -> str:
        """
        Format active threats with attack chains for MITRE panel.

        Shows collapsed cards by default, expandable to full attack chain.
        Limit to 10 threats max for performance.

        ONLY analyzes feeds from THREAT_INTEL_SOURCES (e.g., US-CERT alerts).
        Excludes CVEs, regulatory updates, and informational content.
        """
        try:
            # Get threat analyzer via dependency injection
            from internal_assistant.di import global_injector
            from internal_assistant.server.threat_intelligence.threat_analyzer import (
                ThreatIntelligenceAnalyzer,
            )

            threat_analyzer = global_injector.get(ThreatIntelligenceAnalyzer)

            # Get THREAT INTELLIGENCE feeds only (not CVEs, regulatory, or news)
            from internal_assistant.server.feeds.feeds_service import RSSFeedService
            THREAT_SOURCES = RSSFeedService.THREAT_INTEL_SOURCES

            logger.info(f"Filtering Active Threats to sources: {THREAT_SOURCES}")

            # Collect feeds from threat intelligence sources only
            threat_feeds = []
            for source in THREAT_SOURCES:
                source_feeds = self._feeds_service.get_feeds(source, days_filter)
                threat_feeds.extend(source_feeds)
                logger.info(f"Found {len(source_feeds)} feeds from {source}")

            # If no threat intelligence feeds found, show appropriate message
            if not threat_feeds:
                logger.warning(f"No threat intelligence feeds found from sources: {THREAT_SOURCES}")
                return self._render_no_threats_available_state(THREAT_SOURCES)

            # Sort by published date (most recent first)
            sorted_feeds = sorted(
                threat_feeds,
                key=lambda x: x.get('published', ''),
                reverse=True
            )

            # Take 10 most recent threat feeds and enrich with MITRE analysis
            threat_cards = []
            for feed in sorted_feeds[:10]:
                # Extract MITRE techniques from threat description
                techniques = threat_analyzer.extract_mitre_techniques_from_feed_item(feed)

                if techniques:
                    # Build attack chain if techniques found
                    attack_chain = threat_analyzer.build_attack_chain(techniques)
                    confidence = max(t['confidence'] for t in techniques)
                else:
                    # No techniques found in threat description
                    attack_chain = {'phases': [], 'total_phases': 0, 'is_complete_chain': False}
                    techniques = []
                    confidence = 0.5  # Neutral confidence when no techniques extracted

                threat_cards.append({
                    'feed': feed,
                    'techniques': techniques,
                    'attack_chain': attack_chain,
                    'confidence': confidence,
                })

            if not threat_cards:
                return self._render_no_threats_available_state(THREAT_SOURCES)

            # Render HTML
            html = self._render_threats_header(len(threat_cards))

            for idx, threat in enumerate(threat_cards):
                html += self._render_threat_card_collapsed(threat, idx, threat_analyzer)
                html += self._render_threat_card_expanded(threat, idx, threat_analyzer)

            html += self._render_threats_footer(threat_cards)

            # Safety check: Validate HTML size (max 100KB for performance)
            html_size_kb = len(html.encode('utf-8')) / 1024
            if html_size_kb > 100:
                logger.warning(
                    f"Active threats HTML too large: {html_size_kb:.1f}KB, falling back to simple view"
                )
                # Fallback to simplified view with fewer threats
                simple_threats = threat_cards[:5]  # Only show top 5
                html = self._render_threats_header(len(simple_threats))
                for idx, threat in enumerate(simple_threats):
                    html += self._render_threat_card_collapsed(threat, idx, threat_analyzer)
                    # Skip expanded cards to reduce size
                html += f"""
                <div style='margin-top: 16px; padding: 12px; background: #2a2a2a; border-radius: 8px; border-left: 3px solid #FF0000;'>
                    <div style='color: #FF0000; font-size: 12px; margin-bottom: 8px;'>
                        ⚠️ Showing top 5 threats only (original display too large)
                    </div>
                </div>
                </div>
                """
                logger.info(f"Fallback HTML size: {len(html.encode('utf-8')) / 1024:.1f}KB")

            return html

        except Exception as e:
            logger.error(f"Error formatting active threats: {e}", exc_info=True)
            return self._render_error_state(f"Error loading active threats: {str(e)}")

    def _render_threats_header(self, threat_count: int) -> str:
        """Render header for active threats panel."""
        return f"""
        <style>
            .threat-card-collapsed {{ display: block; }}
            .threat-card-expanded {{ display: none; }}
            .threat-expand-btn, .threat-collapse-btn {{
                cursor: pointer;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #FF0000;
                background: rgba(255, 0, 0, 0.1);
                color: #FF0000;
                transition: all 0.2s;
            }}
            .threat-expand-btn:hover, .threat-collapse-btn:hover {{
                background: rgba(255, 0, 0, 0.2);
            }}
        </style>
        <div class='feed-content' style='max-height: none; height: auto; overflow-y: auto; padding-right: 8px;'>
            <div class='feed-source-section'>
                <h4 class='feed-source-header' style='color: #FF0000; margin: 16px 0 12px 0; font-size: 18px; font-weight: bold;'>
                    🎯 Active Threats ({threat_count} detected)
                </h4>
                <p style='color: #888; font-size: 12px; margin: 0 0 16px 0;'>
                    Click "Show Attack Chain" to view full kill chain progression and mitigations
                </p>
            </div>
        """

    def _render_threat_card_collapsed(
        self, threat: dict, idx: int, threat_analyzer: Any
    ) -> str:
        """Render collapsed threat card showing summary."""
        feed = threat['feed']
        techniques = threat['techniques']
        attack_chain = threat['attack_chain']
        confidence = threat['confidence']

        # Build attack chain summary (T1566 → T1059 → T1486)
        chain_summary = " → ".join([
            t['technique_id'] for t in techniques[:5]
        ])
        if len(techniques) > 5:
            chain_summary += " ..."

        # Get top 3 mitigations across all techniques
        all_mitigations = []
        for tech in techniques[:3]:
            mits = threat_analyzer.get_mitigations_for_technique(tech['technique_id'])
            all_mitigations.extend(mits)

        # Deduplicate mitigations
        seen = set()
        unique_mitigations = []
        for mit in all_mitigations:
            if mit['id'] not in seen:
                seen.add(mit['id'])
                unique_mitigations.append(mit)

        top_mitigations = unique_mitigations[:3]

        # Confidence bar color
        confidence_pct = int(confidence * 100)
        confidence_color = "#28A745" if confidence >= 0.8 else "#FFA500" if confidence >= 0.6 else "#FF6B35"

        source = feed.get('source', 'Unknown Source')
        source_color = self._feeds_service.SOURCE_COLORS.get(source, '#666666')
        title = feed.get('title', 'No Title')
        published = feed.get('published', 'Unknown Date')

        return f"""
        <div id='threat-collapsed-{idx}' class='threat-card-collapsed' style='margin-bottom: 12px; padding: 12px; background: #1a1a1a; border-radius: 8px; border-left: 3px solid {source_color};'>
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                <div style='flex: 1;'>
                    <h5 style='margin: 0 0 4px 0; color: #e0e0e0; font-size: 14px; font-weight: 600;'>{title}</h5>
                    <div style='color: #888; font-size: 11px; margin-bottom: 8px;'>
                        <span style='color: {source_color};'>📡 {source}</span> • <span>{published}</span>
                    </div>
                </div>
            </div>

            <div style='margin-bottom: 8px;'>
                <div style='color: #ccc; font-size: 12px; margin-bottom: 4px;'>
                    <strong>Attack Chain:</strong> {chain_summary}
                </div>
                <div style='background: #2a2a2a; height: 6px; border-radius: 3px; overflow: hidden;'>
                    <div style='background: {confidence_color}; width: {confidence_pct}%; height: 100%;'></div>
                </div>
                <div style='color: #888; font-size: 10px; margin-top: 2px;'>
                    Confidence: {confidence_pct}% • {attack_chain['total_phases']} kill chain phases detected
                </div>
            </div>

            <div style='margin-bottom: 8px;'>
                <div style='color: #ccc; font-size: 11px; margin-bottom: 4px;'><strong>Top Mitigations:</strong></div>
                <div style='display: flex; flex-wrap: wrap; gap: 6px;'>
                    {"".join([f"<span style='background: #1e88e522; color: #1e88e5; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; border: 1px solid #1e88e5;'>{mit['id']}: {mit['name']}</span>" for mit in top_mitigations])}
                </div>
            </div>

            <div style='text-align: right;'>
                <button class='threat-expand-btn' onclick='expandThreat({idx})'>
                    Show Attack Chain ➤
                </button>
            </div>
        </div>
        """

    def _render_threat_card_expanded(
        self, threat: dict, idx: int, threat_analyzer: Any
    ) -> str:
        """Render expanded threat card with full attack chain and mitigations."""
        feed = threat['feed']
        techniques = threat['techniques']
        attack_chain = threat['attack_chain']
        confidence = threat['confidence']

        source = feed.get('source', 'Unknown Source')
        source_color = self._feeds_service.SOURCE_COLORS.get(source, '#666666')
        title = feed.get('title', 'No Title')
        published = feed.get('published', 'Unknown Date')
        summary = feed.get('summary', '')
        link = feed.get('link', '#')

        # Build phase-by-phase breakdown
        phases_html = ""
        for phase_name, phase_data in attack_chain['phases']:
            phase_order = phase_data['order']
            phase_techniques = phase_data['techniques']

            # Phase color based on kill chain position
            phase_colors = {
                1: "#FF0000",  # Initial Access - Red
                2: "#FF6B35",  # Execution - Orange
                3: "#FFA500",  # Persistence - Yellow-Orange
                4: "#00FFFF",  # Credential Access - Cyan
                5: "#FF00FF",  # Lateral Movement - Magenta
                6: "#8B0000",  # Impact - Dark Red
            }
            phase_color = phase_colors.get(phase_order, "#0077BE")

            phases_html += f"""
            <div style='margin-bottom: 16px; padding: 12px; background: #2a2a2a; border-radius: 6px; border-left: 4px solid {phase_color};'>
                <div style='color: {phase_color}; font-size: 13px; font-weight: 700; margin-bottom: 8px;'>
                    Phase {phase_order}: {phase_name}
                </div>
            """

            for tech in phase_techniques:
                tech_id = tech['technique_id']
                tech_name = tech['name']
                tech_confidence = int(tech['confidence'] * 100)

                # Get mitigations for this technique
                mitigations = threat_analyzer.get_mitigations_for_technique(tech_id)

                # MITRE ATT&CK link
                mitre_link = f"https://attack.mitre.org/techniques/{tech_id.replace('.', '/')}"

                phases_html += f"""
                <div style='margin-bottom: 12px; padding: 8px; background: #1a1a1a; border-radius: 4px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                        <div style='color: #e0e0e0; font-size: 12px; font-weight: 600;'>
                            <a href='javascript:void(0)' onclick='confirmOpenExternal("{mitre_link}", "{tech_id}")'
                               style='color: {phase_color}; text-decoration: none;'>
                                🎯 {tech_id}
                            </a>
                            <span style='color: #ccc; margin-left: 6px;'>{tech_name}</span>
                        </div>
                        <span style='color: #888; font-size: 10px;'>{tech_confidence}% confidence</span>
                    </div>

                    <div style='margin-top: 6px;'>
                        <div style='color: #aaa; font-size: 10px; margin-bottom: 4px;'><strong>Mitigations:</strong></div>
                        <div style='display: flex; flex-wrap: wrap; gap: 4px;'>
                            {"".join([f"<span style='background: #1e88e522; color: #1e88e5; padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: 600; border: 1px solid #1e88e5;'>{mit['id']}: {mit['name']}</span>" for mit in mitigations])}
                        </div>
                    </div>
                </div>
                """

            phases_html += "</div>"

        return f"""
        <div id='threat-expanded-{idx}' class='threat-card-expanded' style='margin-bottom: 12px; padding: 12px; background: #1a1a1a; border-radius: 8px; border-left: 3px solid {source_color};'>
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;'>
                <div style='flex: 1;'>
                    <h5 style='margin: 0 0 4px 0; color: #e0e0e0; font-size: 14px; font-weight: 600;'>
                        <a href='javascript:void(0)' onclick='confirmOpenExternal("{link}", "{title}")'
                           style='color: inherit; text-decoration: none;'>
                            {title}
                        </a>
                    </h5>
                    <div style='color: #888; font-size: 11px; margin-bottom: 8px;'>
                        <span style='color: {source_color};'>📡 {source}</span> • <span>{published}</span>
                    </div>
                    <p style='color: #ccc; font-size: 12px; margin: 0;'>{summary}</p>
                </div>
            </div>

            <div style='background: #2a2a2a; padding: 8px; border-radius: 6px; margin-bottom: 12px;'>
                <div style='color: #FF0000; font-size: 12px; font-weight: 700; margin-bottom: 8px;'>
                    📊 Attack Chain Analysis
                </div>
                <div style='color: #aaa; font-size: 11px;'>
                    <strong>Total Techniques:</strong> {len(techniques)} detected •
                    <strong>Kill Chain Phases:</strong> {attack_chain['total_phases']} •
                    <strong>Confidence:</strong> {int(confidence * 100)}%
                </div>
            </div>

            <div style='margin-bottom: 12px;'>
                {phases_html}
            </div>

            <div style='text-align: right;'>
                <button class='threat-collapse-btn' onclick='collapseThreat({idx})'>
                    ◀ Collapse
                </button>
            </div>
        </div>
        """

    def _render_threats_footer(self, threat_cards: list) -> str:
        """Render footer with summary statistics."""
        total_techniques = sum(len(t['techniques']) for t in threat_cards)
        total_phases = sum(t['attack_chain']['total_phases'] for t in threat_cards)
        avg_confidence = sum(t['confidence'] for t in threat_cards) / len(threat_cards)

        complete_chains = sum(1 for t in threat_cards if t['attack_chain']['is_complete_chain'])

        return f"""
            <div style='margin-top: 16px; padding: 12px; background: #2a2a2a; border-radius: 8px; border-left: 3px solid #FF0000;'>
                <div style='color: #FF0000; font-size: 13px; font-weight: 700; margin-bottom: 8px;'>
                    📊 Threat Summary
                </div>
                <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; color: #ccc; font-size: 11px;'>
                    <div><strong>Total Threats:</strong> {len(threat_cards)}</div>
                    <div><strong>Total Techniques:</strong> {total_techniques}</div>
                    <div><strong>Kill Chain Phases:</strong> {total_phases}</div>
                    <div><strong>Complete Chains:</strong> {complete_chains}</div>
                    <div><strong>Avg Confidence:</strong> {int(avg_confidence * 100)}%</div>
                    <div><strong>Time Range:</strong> Last 7 days</div>
                </div>
            </div>
        </div>
        """

    def _render_no_threats_available_state(self, threat_sources: list) -> str:
        """Render state when no threat intelligence feeds are available."""
        sources_list = ", ".join(threat_sources)
        return f"""
        <div class='feed-content'>
            <div style='text-align: center; color: #666; padding: 40px 20px;'>
                <div style='font-size: 48px; margin-bottom: 16px;'>✅</div>
                <div style='font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #28A745;'>
                    No Active Threats Detected
                </div>
                <div style='font-size: 12px; color: #888; margin-bottom: 16px;'>
                    No cyber threat alerts found from {sources_list} in the last 7 days.
                </div>
                <div style='font-size: 11px; color: #666; padding: 16px; background: #2a2a2a; border-radius: 8px; margin: 0 auto; max-width: 500px;'>
                    <strong>ℹ️ Active Threats Panel</strong><br/>
                    This panel analyzes threat intelligence feeds containing adversary behavior descriptions.
                    It does NOT show CVEs, regulatory updates, or security news.
                </div>
                <div style='font-size: 10px; color: #555; margin-top: 16px;'>
                    Click "Refresh MITRE Data" to fetch latest threat intelligence.
                </div>
            </div>
        </div>
        """

    def _render_empty_threats_state(self) -> str:
        """Render empty state when no threats are detected (legacy fallback)."""
        return self._render_no_threats_available_state(["threat intelligence sources"])

    def _render_error_state(self, error_message: str) -> str:
        """Render error state with message."""
        return f"""
        <div class='feed-content error'>
            <div style='text-align: center; color: #d32f2f; padding: 40px 20px;'>
                <div style='font-size: 48px; margin-bottom: 16px;'>⚠️</div>
                <div style='font-size: 16px; font-weight: 600; margin-bottom: 8px;'>
                    Error Loading Active Threats
                </div>
                <div style='font-size: 12px; color: #888; margin-bottom: 16px;'>
                    {error_message}
                </div>
                <div style='font-size: 11px; color: #666;'>
                    Click "Refresh MITRE Data" to try again or check application logs for details.
                </div>
            </div>
        </div>
        """
