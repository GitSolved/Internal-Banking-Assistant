"""External Information Component

This module contains the extracted external information and RSS feeds interface from ui.py.
It handles regulatory information feeds, CVE tracking, time filtering, and feed refresh functionality.

Extracted from ui.py lines 7386-7476 during Phase 1A.3 refactoring.

Author: Internal Assistant Team
Version: 0.6.2
"""

import logging
from collections.abc import Callable
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)


class ExternalInfoBuilder:
    """Builder class for external information and RSS feeds components.

    This class handles the creation and layout of all external information UI elements
    including regulatory feeds, CVE tracking, time filtering, and refresh functionality.
    Extracted from the monolithic ui.py to improve code organization.
    """

    def __init__(
        self, format_feeds_fn: Callable = None, format_cve_fn: Callable = None
    ):
        """Initialize the external information builder.

        Args:
            format_feeds_fn: Function to format RSS feeds for display
            format_cve_fn: Function to format CVE data for display
        """
        self.format_feeds_fn = format_feeds_fn or (
            lambda *args: "<div>No feeds available</div>"
        )
        self.format_cve_fn = format_cve_fn or (
            lambda *args: "<div>No CVE data available</div>"
        )
        logger.debug("ExternalInfoBuilder initialized")

    def build_external_info_interface(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Build the complete external information interface.

        This method creates the full external information layout including:
        - Regulatory information feeds display
        - CVE tracking interface
        - Time range filtering controls
        - Refresh functionality and status displays

        Returns:
            Tuple containing:
            - components: Dictionary of all Gradio components
            - layout_config: Configuration for layout integration
        """
        logger.debug("Building external information interface")

        components = {}
        layout_config = {}

        # External Information Section - Full Width (Matching Chat Layout)
        with gr.Group(elem_classes=["external-info-section"]):

            # Section Header
            section_header = gr.HTML(
                "<div class='file-section-title'>Regulatory Information Feed</div>"
            )
            components["section_header"] = section_header

            # Category display is now embedded in feed_display HTML (no separate component needed)

            # Source Category Filter Buttons (Row 1: Primary categories)
            with gr.Row():
                all_sources_btn = gr.Button(
                    "All Sources", elem_classes=["filter-btn"], size="sm", scale=1
                )
                banking_btn = gr.Button(
                    "Banking Regulation", elem_classes=["filter-btn"], size="sm", scale=1
                )
                cybersec_btn = gr.Button(
                    "Cybersecurity", elem_classes=["filter-btn"], size="sm", scale=1
                )
                aml_btn = gr.Button(
                    "AML/BSA", elem_classes=["filter-btn"], size="sm", scale=1
                )

                components["all_sources_btn"] = all_sources_btn
                components["banking_btn"] = banking_btn
                components["cybersec_btn"] = cybersec_btn
                components["aml_btn"] = aml_btn

            # Source Category Filter Buttons (Row 2: Secondary categories)
            with gr.Row():
                securities_btn = gr.Button(
                    "Securities", elem_classes=["filter-btn"], size="sm", scale=1
                )
                consumer_btn = gr.Button(
                    "Consumer Protection", elem_classes=["filter-btn"], size="sm", scale=1
                )
                ai_security_btn = gr.Button(
                    "AI Security", elem_classes=["filter-btn"], size="sm", scale=1
                )
                international_btn = gr.Button(
                    "International", elem_classes=["filter-btn"], size="sm", scale=1
                )

                components["securities_btn"] = securities_btn
                components["consumer_btn"] = consumer_btn
                components["ai_security_btn"] = ai_security_btn
                components["international_btn"] = international_btn

            # Hidden state components to track current selections
            current_feed_category = gr.Textbox(value="All Sources", visible=False)
            current_days_filter = gr.Textbox(value="30", visible=False)
            components["current_feed_category"] = current_feed_category
            components["current_days_filter"] = current_days_filter

            # Feed Status Display
            feed_status = gr.HTML(
                "<div class='feed-status'>Loading external information...</div>",
                elem_classes=["feed-status-display"],
            )
            components["feed_status"] = feed_status

            # Feed Items Display
            try:
                initial_feeds_html = self.format_feeds_fn(
                    None, 30
                )  # Default 30 days, All sources
            except Exception as e:
                logger.warning(f"Error loading initial feeds: {e}")
                initial_feeds_html = """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>📡 No external information available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click any category button to load regulatory feeds
                        </div>
                    </div>
                </div>"""

            feed_display = gr.HTML(
                value=initial_feeds_html, elem_classes=["file-list-container"]
            )
            components["feed_display"] = feed_display

            # Add resize handle for External Information
            external_resize_handle = gr.HTML(
                '<div class="external-resize-handle" id="external-resize-handle"></div>'
            )
            components["external_resize_handle"] = external_resize_handle

        # CVE Tracking Section - Dedicated Panel
        with gr.Group(elem_classes=["cve-tracking-section"]):

            # CVE Section Header
            cve_header = gr.HTML(
                "<div class='file-section-title'>Common Vulnerabilities and Exposures (CVE) Tracking</div>"
            )
            components["cve_header"] = cve_header

            # Dynamic CVE Time Range Display
            cve_time_range_display = gr.HTML(
                "<div style='font-size: 12px; font-weight: 600; color: #0077BE; margin-bottom: 4px; margin-top: 8px;'>⏰ TIME RANGE: 7 days</div>"
            )
            components["cve_time_range_display"] = cve_time_range_display

            # CVE Time Filter Buttons
            with gr.Row():
                cve_time_24h_btn = gr.Button(
                    "24h", elem_classes=["filter-btn"], size="sm", scale=1
                )
                cve_time_7d_btn = gr.Button(
                    "7d", elem_classes=["filter-btn"], size="sm", scale=1
                )
                cve_time_30d_btn = gr.Button(
                    "30d", elem_classes=["filter-btn"], size="sm", scale=1
                )
                cve_time_90d_btn = gr.Button(
                    "90d", elem_classes=["filter-btn"], size="sm", scale=1
                )

                components["cve_time_24h_btn"] = cve_time_24h_btn
                components["cve_time_7d_btn"] = cve_time_7d_btn
                components["cve_time_30d_btn"] = cve_time_30d_btn
                components["cve_time_90d_btn"] = cve_time_90d_btn

            # Hidden state to track CVE time filter
            cve_current_time_filter = gr.Textbox(value="7 days", visible=False)
            components["cve_current_time_filter"] = cve_current_time_filter

            # CVE Status Display
            cve_status = gr.HTML(
                "<div class='feed-status'>Loading CVE data...</div>",
                elem_classes=["feed-status-display"],
            )
            components["cve_status"] = cve_status

            # CVE Items Display
            try:
                initial_cve_html = self.format_cve_fn(
                    None, "All Severities", "All Vendors"
                )
            except Exception as e:
                logger.warning(f"Error loading initial CVE data: {e}")
                initial_cve_html = """
                <div class='feed-content'>
                    <div style='text-align: center; color: #666; padding: 20px;'>
                        <div>🔍 No CVE data available</div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Click any time range button to load latest vulnerability information
                        </div>
                    </div>
                </div>"""

            cve_display = gr.HTML(
                value=initial_cve_html, elem_classes=["file-list-container"]
            )
            components["cve_display"] = cve_display

        # Store layout configuration
        layout_config["external_info_section"] = True
        layout_config["cve_tracking_enabled"] = True
        layout_config["time_filtering"] = True
        layout_config["refresh_functionality"] = True

        logger.debug(
            f"External information interface created with {len(components)} components"
        )
        return components, layout_config

    def get_component_references(self, components: dict[str, Any]) -> dict[str, Any]:
        """Extract component references for external event handling.

        Args:
            components: Dictionary of all created components

        Returns:
            Dictionary mapping component names to Gradio component references
        """
        return {
            "all_sources_btn": components.get("all_sources_btn"),
            "banking_btn": components.get("banking_btn"),
            "cybersec_btn": components.get("cybersec_btn"),
            "aml_btn": components.get("aml_btn"),
            "securities_btn": components.get("securities_btn"),
            "consumer_btn": components.get("consumer_btn"),
            "ai_security_btn": components.get("ai_security_btn"),
            "international_btn": components.get("international_btn"),
            "current_feed_category": components.get("current_feed_category"),
            "current_days_filter": components.get("current_days_filter"),
            "feed_status": components.get("feed_status"),
            "feed_display": components.get("feed_display"),
            "cve_time_range_display": components.get("cve_time_range_display"),
            "cve_time_24h_btn": components.get("cve_time_24h_btn"),
            "cve_time_7d_btn": components.get("cve_time_7d_btn"),
            "cve_time_30d_btn": components.get("cve_time_30d_btn"),
            "cve_time_90d_btn": components.get("cve_time_90d_btn"),
            "cve_current_time_filter": components.get("cve_current_time_filter"),
            "cve_status": components.get("cve_status"),
            "cve_display": components.get("cve_display"),
            "external_resize_handle": components.get("external_resize_handle"),
            "section_header": components.get("section_header"),
            "cve_header": components.get("cve_header"),
        }

    def get_layout_configuration(self) -> dict[str, Any]:
        """Get layout configuration for integration with main UI.

        Returns:
            Dictionary containing layout configuration options
        """
        return {
            "section_classes": ["external-info-section", "cve-tracking-section"],
            "button_classes": ["modern-button", "refresh-button", "filter-btn"],
            "status_classes": ["feed-status-display"],
            "display_classes": ["file-list-container"],
            "resize_handles": ["external-resize-handle"],
        }


def create_external_info_interface(
    format_feeds_fn: Callable = None, format_cve_fn: Callable = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Factory function to create an external information interface.

    Args:
        format_feeds_fn: Function to format RSS feeds for display
        format_cve_fn: Function to format CVE data for display

    Returns:
        Tuple containing components dictionary and layout configuration
    """
    builder = ExternalInfoBuilder(format_feeds_fn, format_cve_fn)
    return builder.build_external_info_interface()


def get_external_info_component_refs(components: dict[str, Any]) -> dict[str, Any]:
    """Extract component references for event handling integration.

    Args:
        components: Dictionary of created components

    Returns:
        Dictionary of component references for external use
    """
    builder = ExternalInfoBuilder()
    return builder.get_component_references(components)
