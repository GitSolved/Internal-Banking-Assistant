"""Settings and General Assistant Event Handlers

This module contains event handlers for settings management and general assistant features
like calculator and definition shortcuts. Extracted from ui.py as part of Phase 1 refactoring
to decouple event handling from UI construction.
"""

import logging

logger = logging.getLogger(__name__)


class GeneralAssistantEventHandler:
    """Handles general assistant events including calculator and definition shortcuts."""

    def __init__(self):
        """Initialize general assistant event handler."""
        pass

    def handle_calculation(self, calc_expression: str) -> str:
        """Handle calculator expressions with security checks.
        Extracted from ui.py lines 5474-5510 (~35 lines).

        Args:
            calc_expression: Mathematical expression to evaluate

        Returns:
            Formatted calculation result or error message
        """
        if not calc_expression or calc_expression.strip() == "":
            return "Please enter a calculation (e.g., 15% of $250,000 or 1024 * 8)"

        try:
            # Handle percentage calculations
            if "%" in calc_expression and "of" in calc_expression.lower():
                # Parse "15% of $250,000" format
                parts = (
                    calc_expression.lower()
                    .replace("$", "")
                    .replace(",", "")
                    .split("of")
                )
                if len(parts) == 2:
                    percentage = float(parts[0].strip().replace("%", ""))
                    amount = float(parts[1].strip())
                    result = (percentage / 100) * amount
                    return f"💰 {percentage}% of ${amount:,.2f} = ${result:,.2f}"

            # Handle basic math expressions
            # Remove currency symbols and commas for calculation
            clean_expression = calc_expression.replace("$", "").replace(",", "")

            # Security: Only allow basic math operations
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in clean_expression):
                return "⚠️ Only basic math operations (+, -, *, /, %) are allowed"

            result = eval(clean_expression)

            # Format result appropriately
            if isinstance(result, float):
                if result.is_integer():
                    return f"🧮 {calc_expression} = {int(result):,}"
                else:
                    return f"🧮 {calc_expression} = {result:,.2f}"
            else:
                return f"🧮 {calc_expression} = {result:,}"

        except Exception as e:
            return "❌ Calculation error: Please check your expression format"

    def handle_definition_shortcut(self, term_category: str) -> str:
        """Handle definition shortcut template selection.
        Extracted from ui.py lines 5519-5530.

        Args:
            term_category: Selected category of terms

        Returns:
            Template string for the selected category
        """
        if not term_category:
            return ""

        templates = {
            "🔒 Security Terms": "Define these key cybersecurity terms: firewall, encryption, vulnerability, threat actor, zero-day exploit, and phishing",
            "💰 Financial Terms": "Explain these banking terms: interest rate, LIBOR, credit risk, Basel III, capital adequacy ratio, and liquidity coverage ratio",
            "⚖️ Compliance Terms": "Define these compliance concepts: SOX, PCI DSS, GDPR, data retention, audit trail, and risk assessment",
            "🏗️ Tech Architecture": "Explain these technical terms: API, microservices, load balancer, CDN, container, and database sharding",
        }

        return templates.get(term_category, "")


class SettingsEventHandler:
    """Handles settings-related events including system prompt management and defaults."""

    def __init__(self, get_default_system_prompt_func, reset_settings_func):
        """Initialize settings event handler.

        Args:
            get_default_system_prompt_func: Function to get default system prompt
            reset_settings_func: Function to reset settings to defaults
        """
        self.get_default_system_prompt = get_default_system_prompt_func
        self.reset_settings = reset_settings_func

    def update_system_prompt_from_template(self, selected_template: str) -> str:
        """Update system prompt based on selected template.
        Extracted from ui.py advanced settings section.

        Args:
            selected_template: Selected template name

        Returns:
            System prompt text for the selected template
        """
        if not selected_template or selected_template == "Custom":
            return ""

        # This would typically call the get_default_system_prompt function
        # with the appropriate mode/template parameter
        try:
            prompt = self.get_default_system_prompt(selected_template)
            logger.info(f"Updated system prompt from template: {selected_template}")
            return prompt
        except Exception as e:
            logger.error(f"Failed to update system prompt: {e}")
            return ""

    def reset_to_defaults(self) -> tuple:
        """Reset all settings to their default values.
        Extracted from ui.py reset settings functionality.

        Returns:
            Tuple of default values for all settings
        """
        try:
            # Call the reset settings function and return defaults
            defaults = self.reset_settings()
            logger.info("Settings reset to defaults")
            return defaults
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            # Return reasonable defaults if reset fails
            return (
                0.7,  # similarity_threshold
                0.1,  # response_temperature
                "Include Sources",  # citation_style
                "Medium",  # response_length
                "",  # system_prompt_input
                "Custom",  # system_prompt_templates
            )

    def on_system_prompt_blur(self, system_prompt: str) -> str:
        """Handle system prompt input blur event.
        Extracted from ui.py system prompt blur handler.

        Args:
            system_prompt: Current system prompt text

        Returns:
            Processed system prompt (currently returns as-is)
        """
        # This could include validation, formatting, or other processing
        return system_prompt.strip() if system_prompt else ""


class SettingsEventHandlerBuilder:
    """Builder class for creating settings and general assistant event handlers."""

    def __init__(self, get_default_system_prompt_func=None, reset_settings_func=None):
        """Initialize the builder with optional dependency injection.

        Args:
            get_default_system_prompt_func: Function to get default system prompt
            reset_settings_func: Function to reset settings to defaults
        """
        self.get_default_system_prompt_func = get_default_system_prompt_func
        self.reset_settings_func = reset_settings_func
        self._general_handler = None
        self._settings_handler = None

    def get_general_handler(self) -> GeneralAssistantEventHandler:
        """Get or create the general assistant event handler instance.

        Returns:
            GeneralAssistantEventHandler instance
        """
        if self._general_handler is None:
            self._general_handler = GeneralAssistantEventHandler()
        return self._general_handler

    def get_settings_handler(self) -> SettingsEventHandler:
        """Get or create the settings event handler instance.

        Returns:
            SettingsEventHandler instance
        """
        if self._settings_handler is None:
            self._settings_handler = SettingsEventHandler(
                self.get_default_system_prompt_func, self.reset_settings_func
            )
        return self._settings_handler

    def create_calculation_handler(self):
        """Create handler for calculator functionality."""
        return self.get_general_handler().handle_calculation

    def create_definition_shortcut_handler(self):
        """Create handler for definition shortcuts."""
        return self.get_general_handler().handle_definition_shortcut

    def create_system_prompt_template_handler(self):
        """Create handler for system prompt template updates."""
        return self.get_settings_handler().update_system_prompt_from_template

    def create_reset_settings_handler(self):
        """Create handler for resetting settings to defaults."""
        return self.get_settings_handler().reset_to_defaults

    def create_system_prompt_blur_handler(self):
        """Create handler for system prompt blur events."""
        return self.get_settings_handler().on_system_prompt_blur
