"""
UI Core Module

This module contains the foundational architecture for the Internal Assistant UI system.
It provides abstract base classes, interfaces, and core infrastructure for building
modular UI components while maintaining Gradio framework compatibility.

Author: Internal Assistant Team
Version: 0.6.2
"""

from .ui_component import UIComponent
from .component_registry import ComponentRegistry
from .event_router import EventRouter
from .layout_manager import LayoutManager

__all__ = ["UIComponent", "ComponentRegistry", "EventRouter", "LayoutManager"]
