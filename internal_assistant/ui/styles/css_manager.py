"""CSS Manager

This module manages CSS loading, injection, and organization for the Internal Assistant UI.
It handles the extraction of CSS from the monolithic ui.py file and provides a clean
interface for theme management.
"""

import logging
from pathlib import Path
from typing import Any

from .theme_config import ThemeConfig

logger = logging.getLogger(__name__)


class CSSManager:
    """Manager for CSS loading and injection.

    This class handles loading CSS from files, applying theme variables,
    and providing CSS for Gradio components.
    """

    def __init__(self, theme_config: ThemeConfig | None = None):
        """Initialize CSS manager.

        Args:
            theme_config: Optional theme configuration
        """
        self.theme_config = theme_config or ThemeConfig()
        self.css_cache: dict[str, str] = {}
        self.styles_dir = Path(__file__).parent
        self._compiled_css_cache: str | None = None

    def load_styles(self) -> str:
        """Load and compile all CSS styles.

        Returns:
            Complete CSS string for the application
        """
        # DISABLED: CSS caching to allow for hot-reload during development
        # Always reload CSS to ensure changes are applied
        self._compiled_css_cache = None

        logger.debug("Compiling CSS styles...")
        css_parts = []

        # Add CSS variables from theme
        css_parts.append(self.theme_config.get_css_variables())

        # Load main styles
        main_css = self._load_main_styles()
        if main_css:
            css_parts.append(main_css)

        # Load component-specific styles
        component_css = self._load_component_styles()
        if component_css:
            css_parts.append(component_css)

        # Load extended styles
        extended_css = self._load_extended_styles()
        if extended_css:
            css_parts.append(extended_css)

        # Load override styles
        override_css = self._load_override_styles()
        if override_css:
            css_parts.append(override_css)

        # Load force dark styles (ultimate override)
        force_dark_css = self._load_force_dark_styles()
        if force_dark_css:
            css_parts.append(force_dark_css)

        # Load responsive styles (last for proper media query precedence)
        responsive_css = self._load_responsive_styles()
        if responsive_css:
            css_parts.append(responsive_css)

        # Add inline CSS extracted from UI components
        inline_css = self._get_inline_css()
        if inline_css:
            css_parts.append(inline_css)

        # Add utility CSS classes
        utility_css = self.add_utility_css()
        if utility_css:
            css_parts.append(utility_css)

        # Combine all CSS
        combined_css = "\n\n".join(css_parts)

        # Apply theme variables
        combined_css = self.theme_config.apply_variables(combined_css)

        # Convert hardcoded colors to CSS variables
        combined_css = self._convert_to_css_variables(combined_css)

        # Cache the compiled CSS
        self._compiled_css_cache = combined_css
        logger.debug(f"Compiled CSS: {len(combined_css)} characters")

        return combined_css

    def _load_main_styles(self) -> str:
        """Load main application styles from CSS file.

        Returns:
            Main CSS styles
        """
        css_file = self.styles_dir / "main.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load main styles: {e}")
                return self._get_fallback_css()
        else:
            logger.warning("Main CSS file not found, using fallback")
            return self._get_fallback_css()

    def _load_component_styles(self) -> str:
        """Load component-specific styles from CSS file.

        Returns:
            Component CSS styles
        """
        css_file = self.styles_dir / "components.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load component styles: {e}")
                return ""
        return ""

    def _load_responsive_styles(self) -> str:
        """Load responsive design styles from CSS file.

        Returns:
            Responsive CSS styles
        """
        css_file = self.styles_dir / "responsive.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load responsive styles: {e}")
                return ""
        return ""

    def _load_extended_styles(self) -> str:
        """Load extended styles from CSS file.

        Returns:
            Extended CSS styles
        """
        css_file = self.styles_dir / "extended.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load extended styles: {e}")
                return ""
        return ""

    def _load_override_styles(self) -> str:
        """Load override styles from CSS file.

        Returns:
            Override CSS styles
        """
        css_file = self.styles_dir / "overrides.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load override styles: {e}")
                return ""
        return ""

    def _load_force_dark_styles(self) -> str:
        """Load force dark styles from CSS file.

        Returns:
            Force dark CSS styles
        """
        css_file = self.styles_dir / "force_dark.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load force dark styles: {e}")
                return ""
        return ""

    def _get_fallback_css(self) -> str:
        """Fallback CSS in case the main CSS files cannot be loaded.

        This provides minimal styling to ensure the UI remains functional.

        Returns:
            Temporary embedded CSS
        """
        return """
        /* Temporary Embedded CSS - Will be replaced with extracted styles */
        
        /* Force black background everywhere */
        * {
            background-color: var(--color-primary-bg) !important;
            color: var(--color-primary-text) !important;
        }
        
        /* Main Container */
        html, body, .gradio-container {
            background: var(--color-primary-bg) !important;
            color: var(--color-primary-text) !important;
        }
        
        .gradio-container {
            max-width: var(--size-max-width) !important;
            margin: 0 auto !important;
            font-family: var(--font-primary) !important;
            font-size: var(--text-base) !important;
            line-height: 1.6 !important;
        }
        
        /* Header Styling */
        .header-container {
            background: var(--color-primary-bg) !important;
            border-radius: var(--size-border-radius);
            padding: var(--size-spacing-sm) var(--size-spacing-lg);
            margin-bottom: var(--size-spacing-sm);
            box-shadow: 0 4px 20px var(--color-shadow);
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 3px solid var(--color-accent);
            min-height: var(--size-header-height);
        }
        
        /* Button Styling */
        .gr-button {
            background: var(--color-accent) !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 8px 16px !important;
            font-weight: 500 !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
        }
        
        .gr-button:hover {
            background: var(--color-accent-hover) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 119, 190, 0.3);
        }
        
        .gr-button.secondary {
            background: var(--color-secondary-bg) !important;
            color: var(--color-primary-text) !important;
            border: 1px solid var(--color-border) !important;
        }
        
        .gr-button.stop {
            background: var(--color-error) !important;
        }
        
        /* Input Styling */
        .gr-textbox input, .gr-textbox textarea {
            background: var(--color-tertiary-bg) !important;
            color: var(--color-primary-text) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
        }
        
        .gr-textbox input:focus, .gr-textbox textarea:focus {
            outline: none !important;
            border-color: var(--color-accent) !important;
            box-shadow: 0 0 0 2px rgba(0, 119, 190, 0.2) !important;
        }
        
        /* Tab Styling */
        .gr-tab {
            background: var(--color-secondary-bg) !important;
            color: var(--color-secondary-text) !important;
            border: none !important;
            padding: 10px 20px !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
        }
        
        .gr-tab.selected {
            background: var(--color-accent) !important;
            color: white !important;
        }
        
        /* Accordion Styling */
        .gr-accordion {
            background: var(--color-secondary-bg) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: 6px !important;
            margin: 8px 0 !important;
        }
        
        /* Chatbot Styling */
        .gr-chatbot {
            background: var(--color-tertiary-bg) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: 6px !important;
        }
        
        .message.user {
            background: var(--color-accent) !important;
            color: white !important;
        }
        
        .message.bot {
            background: var(--color-secondary-bg) !important;
            color: var(--color-primary-text) !important;
        }
        """

    def get_component_css(self, component_name: str) -> str | None:
        """Get CSS for a specific component.

        Args:
            component_name: Name of the component

        Returns:
            Component-specific CSS or None if not found
        """
        css_file = self.styles_dir / f"{component_name}.css"
        if css_file.exists():
            try:
                return css_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load {component_name} styles: {e}")
        return None

    def inject_custom_css(self, custom_css: str) -> str:
        """Inject custom CSS into the main styles.

        Args:
            custom_css: Custom CSS to inject

        Returns:
            Combined CSS with custom styles
        """
        main_css = self.load_styles()
        return f"{main_css}\n\n/* Custom CSS */\n{custom_css}"

    def _get_inline_css(self) -> str:
        """Get CSS for inline styles that should be extracted from UI components.

        Returns:
            CSS for inline styles
        """
        return """
        /* ================================
           Inline Styles Extracted from UI
           ================================ */
        
        /* Header styling */
        .header-container .header-title {
            margin: 0 !important;
            padding: 0 !important;
            font-size: var(--text-2xl);
            font-weight: 700;
            color: var(--color-accent);
        }
        
        .header-container .header-subtitle {
            margin: 0 !important;
            padding: 0 !important;
            font-size: var(--text-lg);
            color: var(--color-secondary-text);
        }
        
        /* Quick actions and file types headers */
        .quick-actions-header,
        .file-types-header {
            font-size: 12px;
            font-weight: 600;
            color: var(--color-accent);
            margin-bottom: 4px;
            margin-top: 8px;
        }
        
        .file-types-header {
            margin-top: 12px;
        }
        
        /* Mode selection */
        .mode-selection-header {
            color: var(--color-accent);
            font-weight: 600;
            margin-bottom: 12px;
            font-size: 16px;
        }
        
        /* Status indicators */
        .mode-indicator {
            text-align: center;
            padding: 8px;
            background: var(--color-secondary-bg);
            border-radius: 4px;
            margin-top: 8px;
            border: 1px solid var(--color-accent);
        }
        
        .general-status {
            text-align: center;
            padding: 8px;
            background: var(--color-success);
            border-radius: 4px;
            color: white;
            opacity: 0.9;
        }
        
        .document-status {
            text-align: center;
            padding: 8px;
            background: var(--color-secondary-bg);
            border-radius: 4px;
            color: var(--color-accent);
            border: 1px solid var(--color-accent);
        }
        
        /* Tool panels */
        .general-tools-panel {
            background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(0, 119, 190, 0.1) 100%);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid var(--color-success);
        }
        
        .general-tools-panel .panel-title {
            font-weight: 600;
            color: var(--color-success);
            margin-bottom: 8px;
        }
        
        .general-tools-panel .panel-subtitle {
            font-size: 13px;
            color: var(--color-secondary-text);
        }
        
        /* Mode confirmation dialog */
        .mode-confirm-dialog {
            background: var(--color-warning);
            border: 1px solid var(--color-warning);
            padding: 16px;
            border-radius: 8px;
            margin: 12px 0;
            opacity: 0.9;
        }
        
        .mode-confirm-dialog .dialog-title {
            font-weight: 600;
            color: var(--color-primary-text);
            margin-bottom: 8px;
        }
        
        .mode-confirm-dialog .dialog-message {
            color: var(--color-primary-text);
            margin-bottom: 12px;
        }
        
        .mode-confirm-dialog .dialog-buttons {
            display: flex;
            gap: 8px;
        }
        
        .mode-confirm-dialog button {
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .mode-confirm-dialog .confirm-btn {
            background: var(--color-accent);
            color: white;
        }
        
        .mode-confirm-dialog .confirm-btn:hover {
            background: var(--color-accent-hover);
        }
        
        .mode-confirm-dialog .cancel-btn {
            background: var(--color-secondary-bg);
            color: var(--color-primary-text);
        }
        
        /* Feed content placeholders */
        .feed-content .placeholder {
            text-align: center;
            color: var(--color-secondary-text);
            padding: 20px;
        }
        
        .feed-content .placeholder-subtitle {
            font-size: 12px;
            margin-top: 8px;
        }
        
        /* Keyboard shortcuts modal */
        .keyboard-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 10000;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .keyboard-modal .modal-content {
            background: var(--color-primary-bg);
            padding: 24px;
            border-radius: 12px;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid var(--color-border);
        }
        
        .keyboard-modal h3 {
            margin: 0 0 16px 0;
            color: var(--color-primary-text);
        }
        
        .keyboard-modal .shortcut-list {
            line-height: 1.6;
            color: var(--color-secondary-text);
        }
        
        .keyboard-modal .shortcut-item {
            margin-bottom: 8px;
        }
        
        .keyboard-modal .shortcut-key {
            font-weight: 600;
            color: var(--color-accent);
        }
        
        .keyboard-modal .modal-footer {
            margin-top: 12px;
            font-size: 13px;
            color: var(--color-secondary-text);
        }
        
        /* Toast notifications */
        .toast-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            background: var(--color-success);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        }
        
        .toast-notification.show {
            transform: translateX(0);
        }
        """

    def _convert_to_css_variables(self, css: str) -> str:
        """Convert hardcoded color values to CSS variables where possible.

        Args:
            css: CSS string with hardcoded values

        Returns:
            CSS string with variables substituted
        """
        # Color mappings from hardcoded values to CSS variables
        color_mappings = {
            "#000000": "var(--color-primary-bg)",
            "#0b0f19": "var(--color-secondary-bg)",
            "#1a1d23": "var(--color-tertiary-bg)",
            "#e0e0e0": "var(--color-primary-text)",
            "#b0b0b0": "var(--color-secondary-text)",
            "#0077BE": "var(--color-accent)",
            "#0099FF": "var(--color-accent-hover)",
            "#00C853": "var(--color-success)",
            "#FFB300": "var(--color-warning)",
            "#FF5252": "var(--color-error)",
            "#2a2d33": "var(--color-border)",
        }

        # Apply color mappings
        for hardcoded, variable in color_mappings.items():
            css = css.replace(hardcoded, variable)
            css = css.replace(hardcoded.lower(), variable)
            css = css.replace(hardcoded.upper(), variable)

        return css

    def add_utility_css(self) -> str:
        """Add utility CSS classes for common styling patterns.

        Returns:
            Utility CSS string
        """
        return """
        /* ================================
           Utility Classes
           ================================ */
        
        /* Flexbox utilities */
        .flex { display: flex !important; }
        .flex-col { flex-direction: column !important; }
        .flex-center { align-items: center; justify-content: center; }
        .flex-between { justify-content: space-between; }
        .flex-around { justify-content: space-around; }
        .flex-wrap { flex-wrap: wrap; }
        
        /* Spacing utilities */
        .gap-xs { gap: var(--size-spacing-xs); }
        .gap-sm { gap: var(--size-spacing-sm); }
        .gap-md { gap: var(--size-spacing-md); }
        .gap-lg { gap: var(--size-spacing-lg); }
        .gap-xl { gap: var(--size-spacing-xl); }
        
        .m-0 { margin: 0 !important; }
        .p-0 { padding: 0 !important; }
        .m-auto { margin: 0 auto !important; }
        
        /* Text utilities */
        .text-center { text-align: center !important; }
        .text-left { text-align: left !important; }
        .text-right { text-align: right !important; }
        
        .text-primary { color: var(--color-primary-text) !important; }
        .text-secondary { color: var(--color-secondary-text) !important; }
        .text-accent { color: var(--color-accent) !important; }
        .text-success { color: var(--color-success) !important; }
        .text-warning { color: var(--color-warning) !important; }
        .text-error { color: var(--color-error) !important; }
        
        /* Background utilities */
        .bg-primary { background-color: var(--color-primary-bg) !important; }
        .bg-secondary { background-color: var(--color-secondary-bg) !important; }
        .bg-tertiary { background-color: var(--color-tertiary-bg) !important; }
        .bg-accent { background-color: var(--color-accent) !important; }
        .bg-success { background-color: var(--color-success) !important; }
        .bg-warning { background-color: var(--color-warning) !important; }
        .bg-error { background-color: var(--color-error) !important; }
        
        /* Border utilities */
        .border { border: 1px solid var(--color-border) !important; }
        .border-accent { border: 1px solid var(--color-accent) !important; }
        .border-success { border: 1px solid var(--color-success) !important; }
        .border-warning { border: 1px solid var(--color-warning) !important; }
        .border-error { border: 1px solid var(--color-error) !important; }
        
        .rounded { border-radius: var(--size-border-radius) !important; }
        .rounded-sm { border-radius: 4px !important; }
        .rounded-lg { border-radius: 16px !important; }
        
        /* Shadow utilities */
        .shadow { box-shadow: 0 4px 20px var(--color-shadow) !important; }
        .shadow-sm { box-shadow: 0 2px 8px var(--color-shadow) !important; }
        .shadow-lg { box-shadow: 0 8px 32px var(--color-shadow) !important; }
        
        /* Transition utilities */
        .transition { transition: all 0.3s ease !important; }
        .transition-colors { transition: color 0.3s ease, background-color 0.3s ease !important; }
        
        /* Visibility utilities */
        .visible { visibility: visible !important; }
        .invisible { visibility: hidden !important; }
        .hidden { display: none !important; }
        """

    def get_css_info(self) -> dict[str, Any]:
        """Get information about loaded CSS files and their status.

        Returns:
            Dictionary with CSS loading information
        """
        css_files = {
            "main.css": self.styles_dir / "main.css",
            "components.css": self.styles_dir / "components.css",
            "extended.css": self.styles_dir / "extended.css",
            "overrides.css": self.styles_dir / "overrides.css",
            "responsive.css": self.styles_dir / "responsive.css",
        }

        info = {
            "theme": self.theme_config.theme_name,
            "styles_directory": str(self.styles_dir),
            "css_files": {},
            "compiled_css_size": (
                len(self._compiled_css_cache) if self._compiled_css_cache else 0
            ),
            "cache_status": "cached" if self._compiled_css_cache else "not_cached",
        }

        for name, path in css_files.items():
            if path.exists():
                try:
                    size = path.stat().st_size
                    info["css_files"][name] = {
                        "exists": True,
                        "size_bytes": size,
                        "size_kb": round(size / 1024, 2),
                        "readable": True,
                    }
                except Exception as e:
                    info["css_files"][name] = {
                        "exists": True,
                        "size_bytes": 0,
                        "readable": False,
                        "error": str(e),
                    }
            else:
                info["css_files"][name] = {"exists": False, "readable": False}

        return info

    def validate_css_loading(self) -> dict[str, Any]:
        """Validate that CSS files are loading correctly.

        Returns:
            Validation results
        """
        validation = {"status": "success", "issues": [], "warnings": []}

        # Check if CSS files exist
        required_files = ["main.css", "components.css"]
        for file_name in required_files:
            file_path = self.styles_dir / file_name
            if not file_path.exists():
                validation["issues"].append(f"Required CSS file missing: {file_name}")
                validation["status"] = "error"

        # Check if CSS can be compiled
        try:
            css = self.load_styles()
            if len(css) < 1000:  # Very small CSS might indicate an issue
                validation["warnings"].append("Compiled CSS is unexpectedly small")
                validation["status"] = (
                    "warning"
                    if validation["status"] == "success"
                    else validation["status"]
                )
        except Exception as e:
            validation["issues"].append(f"CSS compilation failed: {e!s}")
            validation["status"] = "error"

        # Check theme configuration
        if not self.theme_config:
            validation["issues"].append("Theme configuration not initialized")
            validation["status"] = "error"

        return validation

    def clear_cache(self) -> None:
        """Clear the CSS cache."""
        self.css_cache.clear()
        self._compiled_css_cache = None
        logger.debug("CSS cache cleared")
