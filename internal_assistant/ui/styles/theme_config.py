"""Theme Configuration

This module manages theme settings and CSS variables for the Internal Assistant UI.
It provides a centralized place for color schemes, fonts, and other style constants.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ThemeConfig:
    """Configuration class for UI theme settings.

    This class manages color schemes, fonts, spacing, and other visual
    constants used throughout the application.
    """

    # Color schemes
    DARK_THEME = {
        "primary_bg": "#000000",
        "secondary_bg": "#0b0f19",
        "tertiary_bg": "#1a1d23",
        "primary_text": "#e0e0e0",
        "secondary_text": "#b0b0b0",
        "accent": "#0077BE",
        "accent_hover": "#0099FF",
        "success": "#00C853",
        "warning": "#FFB300",
        "error": "#FF5252",
        "border": "#2a2d33",
        "shadow": "rgba(0, 119, 190, 0.2)",
    }

    LIGHT_THEME = {
        "primary_bg": "#FFFFFF",
        "secondary_bg": "#F5F5F5",
        "tertiary_bg": "#E0E0E0",
        "primary_text": "#212121",
        "secondary_text": "#757575",
        "accent": "#0077BE",
        "accent_hover": "#0099FF",
        "success": "#00C853",
        "warning": "#FFB300",
        "error": "#FF5252",
        "border": "#BDBDBD",
        "shadow": "rgba(0, 0, 0, 0.1)",
    }

    # Typography
    FONTS = {
        "primary": "'Arial', 'Helvetica', sans-serif",
        "heading": "'Merriweather', 'Inter', 'Segoe UI', 'Roboto', 'Arial', sans-serif",
        "monospace": "'Courier New', 'Consolas', 'Monaco', monospace",
    }

    # Sizing
    SIZES = {
        "max_width": "1400px",
        "header_height": "120px",
        "sidebar_width": "320px",
        "border_radius": "12px",
        "spacing_xs": "4px",
        "spacing_sm": "8px",
        "spacing_md": "16px",
        "spacing_lg": "24px",
        "spacing_xl": "32px",
    }

    # Font sizes
    FONT_SIZES = {
        "xs": "12px",
        "sm": "14px",
        "base": "16px",
        "lg": "18px",
        "xl": "20px",
        "2xl": "24px",
        "3xl": "32px",
        "4xl": "40px",
    }

    def __init__(
        self, theme: str = "dark", custom_config: dict[str, Any] | None = None
    ):
        """Initialize theme configuration.

        Args:
            theme: Theme name ("dark" or "light")
            custom_config: Optional custom configuration overrides
        """
        self.theme_name = theme
        self.colors = self.DARK_THEME if theme == "dark" else self.LIGHT_THEME
        self.fonts = self.FONTS.copy()
        self.sizes = self.SIZES.copy()
        self.font_sizes = self.FONT_SIZES.copy()

        # Apply custom configuration if provided
        if custom_config:
            self._apply_custom_config(custom_config)

    def _apply_custom_config(self, custom_config: dict[str, Any]) -> None:
        """Apply custom configuration overrides.

        Args:
            custom_config: Dictionary of custom settings
        """
        if "colors" in custom_config:
            self.colors.update(custom_config["colors"])
        if "fonts" in custom_config:
            self.fonts.update(custom_config["fonts"])
        if "sizes" in custom_config:
            self.sizes.update(custom_config["sizes"])
        if "font_sizes" in custom_config:
            self.font_sizes.update(custom_config["font_sizes"])

    def get_css_variables(self) -> str:
        """Generate CSS custom properties (variables) from theme configuration.

        Returns:
            CSS string with custom properties
        """
        css_vars = [":root {"]

        # Add color variables
        for key, value in self.colors.items():
            css_var_name = f"--color-{key.replace('_', '-')}"
            css_vars.append(f"    {css_var_name}: {value};")

        # Add font variables
        for key, value in self.fonts.items():
            css_var_name = f"--font-{key.replace('_', '-')}"
            css_vars.append(f"    {css_var_name}: {value};")

        # Add size variables
        for key, value in self.sizes.items():
            css_var_name = f"--size-{key.replace('_', '-')}"
            css_vars.append(f"    {css_var_name}: {value};")

        # Add font size variables
        for key, value in self.font_sizes.items():
            css_var_name = f"--text-{key}"
            css_vars.append(f"    {css_var_name}: {value};")

        css_vars.append("}")

        return "\n".join(css_vars)

    def apply_variables(self, css: str) -> str:
        """Replace placeholders in CSS with theme variables.

        Args:
            css: CSS string with placeholders

        Returns:
            CSS string with variables applied
        """
        # Replace color placeholders
        for key, value in self.colors.items():
            placeholder = f"{{color.{key}}}"
            css = css.replace(placeholder, value)

        # Replace font placeholders
        for key, value in self.fonts.items():
            placeholder = f"{{font.{key}}}"
            css = css.replace(placeholder, value)

        # Replace size placeholders
        for key, value in self.sizes.items():
            placeholder = f"{{size.{key}}}"
            css = css.replace(placeholder, value)

        # Replace font size placeholders
        for key, value in self.font_sizes.items():
            placeholder = f"{{text.{key}}}"
            css = css.replace(placeholder, value)

        return css

    def get_gradio_theme_config(self) -> dict[str, Any]:
        """Get theme configuration in Gradio-compatible format.

        Returns:
            Dictionary of Gradio theme settings
        """
        return {
            "primary_hue": "blue",
            "secondary_hue": "slate",
            "neutral_hue": "gray",
            "text_size": "lg",
            "spacing_size": "md",
            "radius_size": "md",
            "font": self.fonts["primary"],
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert theme configuration to dictionary.

        Returns:
            Dictionary representation of theme
        """
        return {
            "theme_name": self.theme_name,
            "colors": self.colors,
            "fonts": self.fonts,
            "sizes": self.sizes,
            "font_sizes": self.font_sizes,
        }

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "ThemeConfig":
        """Create ThemeConfig from dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            ThemeConfig instance
        """
        theme_name = config.get("theme_name", "dark")
        custom_config = {
            k: v
            for k, v in config.items()
            if k in ["colors", "fonts", "sizes", "font_sizes"]
        }
        return cls(theme_name, custom_config)
