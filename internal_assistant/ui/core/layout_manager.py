"""
Layout Manager

This module provides layout management capabilities for the Internal Assistant UI system.
It handles the organization and positioning of UI components while maintaining 
Gradio framework compatibility and responsive design principles.

The LayoutManager ensures:
- Consistent layout patterns across components
- Responsive design that works on different screen sizes
- Proper CSS integration and theme management
- Flexible layout composition for complex UIs
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import gradio as gr

logger = logging.getLogger(__name__)


class LayoutSection:
    """
    Represents a section of the UI layout.

    A layout section can contain multiple components and has its own
    styling and positioning rules.
    """

    def __init__(
        self,
        section_id: str,
        title: Optional[str] = None,
        visible: bool = True,
        css_classes: Optional[List[str]] = None,
    ):
        """
        Initialize a layout section.

        Args:
            section_id: Unique identifier for this section
            title: Optional title for the section
            visible: Whether the section is initially visible
            css_classes: Optional CSS classes to apply
        """
        self.section_id = section_id
        self.title = title
        self.visible = visible
        self.css_classes = css_classes or []
        self.components: List[Any] = []
        self.layout_config: Dict[str, Any] = {}

    def add_component(
        self, component: Any, layout_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a component to this section.

        Args:
            component: Gradio component to add
            layout_config: Optional layout configuration for this component
        """
        self.components.append(component)
        if layout_config:
            self.layout_config[len(self.components) - 1] = layout_config

    def get_css_classes(self) -> str:
        """Get CSS classes as a space-separated string."""
        return " ".join(self.css_classes)


class LayoutManager:
    """
    Manages the overall layout structure of the UI.

    This class provides methods for creating consistent, responsive layouts
    while maintaining the single gr.Blocks() context required by Gradio.
    """

    def __init__(self, theme_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the layout manager.

        Args:
            theme_config: Optional theme configuration
        """
        self.theme_config = theme_config or {}
        self.sections: Dict[str, LayoutSection] = {}
        self.global_css = ""
        self.layout_state = {}

    def create_section(
        self,
        section_id: str,
        title: Optional[str] = None,
        visible: bool = True,
        css_classes: Optional[List[str]] = None,
    ) -> LayoutSection:
        """
        Create a new layout section.

        Args:
            section_id: Unique identifier for the section
            title: Optional title for the section
            visible: Whether the section is initially visible
            css_classes: Optional CSS classes to apply

        Returns:
            The created layout section
        """
        section = LayoutSection(section_id, title, visible, css_classes)
        self.sections[section_id] = section

        logger.debug(f"Created layout section: {section_id}")
        return section

    def get_section(self, section_id: str) -> Optional[LayoutSection]:
        """
        Get a layout section by ID.

        Args:
            section_id: ID of the section to retrieve

        Returns:
            The layout section or None if not found
        """
        return self.sections.get(section_id)

    def create_header_layout(self) -> Tuple[Any, ...]:
        """
        Create the standard header layout.

        Returns:
            Tuple of Gradio components for the header
        """
        with gr.Row(elem_classes=["header-row"]):
            with gr.Column(scale=1, elem_classes=["logo-column"]):
                logo = gr.Image(
                    value=str("internal_assistant/ui/internal-assistant-logo.png"),
                    show_label=False,
                    interactive=False,
                    height=80,
                    elem_classes=["logo-image"],
                )

            with gr.Column(scale=6, elem_classes=["title-column"]):
                title = gr.Markdown("# Internal Assistant", elem_classes=["main-title"])
                subtitle = gr.Markdown(
                    "Private, secure, customizable GenAI assistant",
                    elem_classes=["subtitle"],
                )

        return logo, title, subtitle

    def create_tab_layout(self, tab_configs: List[Dict[str, Any]]) -> Any:
        """
        Create a tabbed interface layout.

        Args:
            tab_configs: List of tab configurations

        Returns:
            Gradio TabbedInterface component
        """
        tabs = []
        tab_names = []

        for config in tab_configs:
            tab_name = config.get("name", "Unnamed Tab")
            tab_content = config.get("content", [])

            with gr.Tab(tab_name):
                for component in tab_content:
                    # Add component to tab
                    pass

            tab_names.append(tab_name)

        logger.debug(f"Created tab layout with {len(tab_names)} tabs")
        return gr.TabbedInterface(tabs, tab_names=tab_names)

    def create_sidebar_layout(self, width_ratio: float = 0.3) -> Tuple[Any, Any]:
        """
        Create a sidebar layout with main content area.

        Args:
            width_ratio: Ratio of sidebar width to total width (0.0 to 1.0)

        Returns:
            Tuple of (sidebar_column, main_column)
        """
        sidebar_scale = int(width_ratio * 10)
        main_scale = int((1 - width_ratio) * 10)

        with gr.Row(elem_classes=["sidebar-layout"]):
            sidebar = gr.Column(scale=sidebar_scale, elem_classes=["sidebar-column"])
            main_content = gr.Column(
                scale=main_scale, elem_classes=["main-content-column"]
            )

        logger.debug(
            f"Created sidebar layout (sidebar: {sidebar_scale}, main: {main_scale})"
        )
        return sidebar, main_content

    def create_responsive_grid(
        self, components: List[Any], columns: int = 3, gap: str = "1rem"
    ) -> Any:
        """
        Create a responsive grid layout for components.

        Args:
            components: List of components to arrange in grid
            columns: Number of columns in the grid
            gap: CSS gap value between grid items

        Returns:
            Gradio Row containing the grid
        """
        with gr.Row(elem_classes=["responsive-grid"]) as grid_row:
            for i, component in enumerate(components):
                if i % columns == 0 and i > 0:
                    # Start new row after specified number of columns
                    pass

                with gr.Column(scale=1, elem_classes=["grid-item"]):
                    component

        return grid_row

    def apply_theme_css(self) -> str:
        """
        Generate CSS for the current theme configuration.

        Returns:
            CSS string for the theme
        """
        css_rules = []

        # Base theme styles
        if "primary_color" in self.theme_config:
            css_rules.append(
                f"""
                .gradio-container {{
                    --primary-color: {self.theme_config['primary_color']};
                }}
            """
            )

        # Dark mode styles
        if self.theme_config.get("dark_mode", False):
            css_rules.append(
                """
                .gradio-container {
                    background-color: #0b0f19;
                    color: #ffffff;
                }
                
                .gradio-container .block {
                    background-color: #1a1d23;
                    border-color: #2a2d33;
                }
            """
            )

        # Component-specific styles
        css_rules.extend(
            [
                """
            .header-row {
                margin-bottom: 1rem;
                padding: 1rem;
                border-bottom: 1px solid var(--border-color-primary);
            }
            
            .logo-column {
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .title-column {
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            
            .main-title {
                margin: 0;
                font-size: 2rem;
                font-weight: bold;
            }
            
            .subtitle {
                margin: 0;
                font-size: 1.1rem;
                opacity: 0.8;
            }
            
            .sidebar-layout {
                height: calc(100vh - 200px);
                overflow: hidden;
            }
            
            .sidebar-column {
                height: 100%;
                overflow-y: auto;
                padding-right: 1rem;
                border-right: 1px solid var(--border-color-primary);
            }
            
            .main-content-column {
                height: 100%;
                overflow-y: auto;
                padding-left: 1rem;
            }
            
            .responsive-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 1rem;
            }
            
            .grid-item {
                flex: 1 1 calc(33.333% - 1rem);
                min-width: 250px;
            }
            
            @media (max-width: 768px) {
                .grid-item {
                    flex: 1 1 100%;
                }
                
                .sidebar-layout {
                    flex-direction: column;
                }
                
                .sidebar-column {
                    border-right: none;
                    border-bottom: 1px solid var(--border-color-primary);
                    padding-right: 0;
                    padding-bottom: 1rem;
                    max-height: 300px;
                }
                
                .main-content-column {
                    padding-left: 0;
                    padding-top: 1rem;
                }
            }
            """
            ]
        )

        combined_css = "\n".join(css_rules)
        self.global_css = combined_css

        logger.debug("Generated theme CSS")
        return combined_css

    def get_layout_state(self) -> Dict[str, Any]:
        """
        Get the current layout state.

        Returns:
            Dictionary containing layout state information
        """
        return {
            "sections": list(self.sections.keys()),
            "theme_config": self.theme_config,
            "has_global_css": bool(self.global_css),
            "section_count": len(self.sections),
        }

    def set_section_visibility(self, section_id: str, visible: bool) -> None:
        """
        Set the visibility of a layout section.

        Args:
            section_id: ID of the section
            visible: Whether the section should be visible
        """
        section = self.get_section(section_id)
        if section:
            section.visible = visible
            logger.debug(f"Set section {section_id} visibility to {visible}")
        else:
            logger.warning(f"Section {section_id} not found")

    def create_loading_layout(self, message: str = "Loading...") -> Any:
        """
        Create a loading indicator layout.

        Args:
            message: Loading message to display

        Returns:
            Gradio HTML component with loading indicator
        """
        loading_html = f"""
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <div class="loading-message">{message}</div>
        </div>
        <style>
        .loading-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }}
        
        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        .loading-message {{
            margin-top: 1rem;
            font-size: 1.1rem;
            color: #666;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        """

        return gr.HTML(loading_html)


class ResponsiveLayout:
    """
    Helper class for creating responsive layouts that adapt to different screen sizes.
    """

    @staticmethod
    def create_mobile_friendly_layout(components: List[Any]) -> Any:
        """
        Create a mobile-friendly vertical layout.

        Args:
            components: List of components to stack vertically

        Returns:
            Gradio Column with mobile-optimized layout
        """
        with gr.Column(elem_classes=["mobile-layout"]) as mobile_col:
            for component in components:
                with gr.Row(elem_classes=["mobile-row"]):
                    component

        return mobile_col

    @staticmethod
    def create_desktop_layout(components: List[Any], columns: int = 2) -> Any:
        """
        Create a desktop-optimized multi-column layout.

        Args:
            components: List of components to arrange
            columns: Number of columns for desktop layout

        Returns:
            Gradio Row with desktop-optimized layout
        """
        with gr.Row(elem_classes=["desktop-layout"]) as desktop_row:
            for i in range(columns):
                with gr.Column(scale=1, elem_classes=["desktop-column"]):
                    # Add components for this column
                    column_components = components[i::columns]
                    for component in column_components:
                        component

        return desktop_row
