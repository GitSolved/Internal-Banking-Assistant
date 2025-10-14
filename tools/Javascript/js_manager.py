"""
JavaScript Manager

Manages loading and injection of JavaScript files for the Internal Assistant UI.
Similar to CSSManager but handles JavaScript modules.
"""

from pathlib import Path
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class JSManager:
    """
    Manager for JavaScript loading and injection.

    This class handles loading JavaScript from module files and providing
    them to the Gradio interface.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize JavaScript manager.

        Args:
            base_path: Optional base path for JavaScript files
        """
        self.base_path = base_path or Path(__file__).parent / "modules"
        self.js_cache: Dict[str, str] = {}
        self.modules = [
            "ui_common.js",
            "collapsible.js",
            "document_management.js",
            "ai_controls.js",
            "resize_handlers.js",
            "mode_selector.js",
            "threat_display.js",
        ]

    def load_module(self, module_name: str) -> str:
        """
        Load a JavaScript module from file.

        Args:
            module_name: Name of the JavaScript module file

        Returns:
            JavaScript content as string
        """
        if module_name in self.js_cache:
            return self.js_cache[module_name]

        try:
            module_path = self.base_path / module_name
            if module_path.exists():
                content = module_path.read_text(encoding="utf-8")
                self.js_cache[module_name] = content
                logger.info(f"Loaded JavaScript module: {module_name}")
                return content
            else:
                logger.warning(f"JavaScript module not found: {module_path}")
                return ""
        except Exception as e:
            logger.error(f"Error loading JavaScript module {module_name}: {e}")
            return ""

    def get_script_tags(self) -> str:
        """
        Generate HTML script tags for all JavaScript modules.

        Returns:
            HTML string with script tags containing all JavaScript
        """
        scripts = []

        for module in self.modules:
            content = self.load_module(module)
            if content:
                scripts.append(f"<script>\n{content}\n</script>")

        return "\n".join(scripts)

    def get_inline_scripts(self) -> str:
        """
        Get all JavaScript as inline script blocks.

        Returns:
            Combined JavaScript content for inline inclusion
        """
        combined = []

        for module in self.modules:
            content = self.load_module(module)
            if content:
                combined.append(f"// Module: {module}")
                combined.append(content)
                combined.append("")

        return "\n".join(combined)

    def clear_cache(self):
        """Clear the JavaScript cache."""
        self.js_cache.clear()
        logger.info("JavaScript cache cleared")
