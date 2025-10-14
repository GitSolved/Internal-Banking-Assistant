"""Component Integration Tests

This module tests the integration of UI components with the new architecture.
It ensures that components work correctly together and maintain compatibility
with the Gradio framework.
"""

from unittest.mock import Mock, patch

import gradio as gr
import pytest

from internal_assistant.ui.core.component_registry import (
    ComponentRegistry,
)
from internal_assistant.ui.core.event_router import EventBridge, EventRouter
from internal_assistant.ui.core.layout_manager import LayoutManager
from internal_assistant.ui.core.ui_component import ServiceContainer, UIComponent


class TestServiceContainer:
    """Test the service container functionality."""

    def test_service_registration(self):
        """Test registering and retrieving services."""
        container = ServiceContainer()
        mock_service = Mock()

        container.register("test_service", mock_service)

        assert container.has("test_service")
        assert container.get("test_service") == mock_service

    def test_service_not_found(self):
        """Test retrieving non-existent service raises error."""
        container = ServiceContainer()

        with pytest.raises(KeyError):
            container.get("non_existent")

    def test_get_all_services(self):
        """Test getting all registered services."""
        container = ServiceContainer()
        service1 = Mock()
        service2 = Mock()

        container.register("service1", service1)
        container.register("service2", service2)

        all_services = container.get_all()
        assert len(all_services) == 2
        assert all_services["service1"] == service1
        assert all_services["service2"] == service2


class TestUIComponent:
    """Test the base UIComponent class."""

    def test_component_initialization(self):
        """Test component initialization."""

        # Create a concrete implementation for testing
        class TestComponent(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return self._component_refs

        services = {"test_service": Mock()}
        component = TestComponent("test_component", services)

        assert component.component_id == "test_component"
        assert component.has_service("test_service")
        assert not component.is_built()

    def test_service_validation(self):
        """Test service dependency validation."""

        class TestComponent(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return self._component_refs

            def get_required_services(self):
                return ["required_service"]

        component = TestComponent("test", {})
        missing = component.validate_dependencies()

        assert "required_service" in missing


class TestComponentRegistry:
    """Test the component registry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = ServiceContainer()
        self.container.register("test_service", Mock())
        self.registry = ComponentRegistry(self.container)

    def test_register_component_class(self):
        """Test registering a component class."""

        class TestComponent(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return {}

        self.registry.register_component_class("test", TestComponent)

        assert self.registry.has_component("test")

    def test_build_order_calculation(self):
        """Test dependency-based build order calculation."""

        class ComponentA(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return {}

        class ComponentB(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return {}

        # B depends on A
        self.registry.register_component_class("component_a", ComponentA, [])
        self.registry.register_component_class(
            "component_b", ComponentB, ["component_a"]
        )

        build_order = self.registry.get_build_order()

        assert build_order.index("component_a") < build_order.index("component_b")

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""

        class TestComponent(UIComponent):
            def build_interface(self):
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return {}

        # Create circular dependency: A -> B -> A
        self.registry.register_component_class(
            "component_a", TestComponent, ["component_b"]
        )
        self.registry.register_component_class(
            "component_b", TestComponent, ["component_a"]
        )

        with pytest.raises(ValueError, match="Circular dependency"):
            self.registry.get_build_order()


class TestEventRouter:
    """Test the event router functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = EventRouter()

    def test_register_handler(self):
        """Test registering event handlers."""

        def test_handler():
            pass

        handler = self.router.register_handler(
            "test_component", "click", test_handler, "Test handler"
        )

        assert handler.component_id == "test_component"
        assert handler.event_type == "click"

        handlers = self.router.get_handlers_for_component("test_component")
        assert len(handlers) == 1

    def test_handler_execution_tracking(self):
        """Test that handler execution is tracked."""
        call_count = 0

        def test_handler():
            nonlocal call_count
            call_count += 1

        handler = self.router.register_handler("test_component", "click", test_handler)

        # Call the handler
        handler()
        handler()

        assert call_count == 2
        assert handler.call_count == 2

    def test_event_bridge(self):
        """Test cross-component communication via EventBridge."""
        bridge = EventBridge(self.router)
        received_data = None

        def callback(data):
            nonlocal received_data
            received_data = data

        bridge.subscribe("test_event", callback)
        bridge.publish("test_event", {"message": "test"})

        assert received_data == {"message": "test"}


class TestLayoutManager:
    """Test the layout manager functionality."""

    def test_theme_configuration(self):
        """Test theme configuration application."""
        theme_config = {"primary_color": "#FF0000"}
        manager = LayoutManager(theme_config)

        css = manager.apply_theme_css()

        assert css is not None
        assert len(css) > 0

    def test_section_creation(self):
        """Test creating layout sections."""
        manager = LayoutManager()

        section = manager.create_section(
            "test_section",
            title="Test Section",
            visible=True,
            css_classes=["test-class"],
        )

        assert section.section_id == "test_section"
        assert section.title == "Test Section"
        assert section.visible is True
        assert "test-class" in section.css_classes

    def test_section_visibility_control(self):
        """Test controlling section visibility."""
        manager = LayoutManager()

        section = manager.create_section("test_section", visible=True)
        assert section.visible is True

        manager.set_section_visibility("test_section", False)
        assert section.visible is False


class TestComponentIntegration:
    """Test full component integration scenarios."""

    @patch("gradio.Blocks")
    def test_complete_ui_build(self, mock_blocks):
        """Test building a complete UI with multiple components."""
        # Create service container
        container = ServiceContainer()
        container.register("chat", Mock())
        container.register("ingest", Mock())
        container.register("feeds", Mock())

        # Create registry
        registry = ComponentRegistry(container)

        # Create mock components
        class MockChatComponent(UIComponent):
            def build_interface(self):
                return {"chatbot": gr.Chatbot(), "input": gr.Textbox()}

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return self._component_refs

        class MockDocumentComponent(UIComponent):
            def build_interface(self):
                return {"upload": gr.File(), "library": gr.HTML()}

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return self._component_refs

        # Register components
        registry.register_component_class("chat", MockChatComponent)
        registry.register_component_class("documents", MockDocumentComponent)

        # Build all components
        built = registry.build_all_components()

        assert "chat" in built
        assert "documents" in built

    def test_component_communication(self):
        """Test components can communicate through events."""
        container = ServiceContainer()
        registry = ComponentRegistry(container)
        router = EventRouter()
        bridge = EventBridge(router)

        # Track communication
        messages = []

        def on_document_uploaded(data):
            messages.append(f"Document uploaded: {data}")

        def on_chat_updated(data):
            messages.append(f"Chat updated: {data}")

        # Subscribe to events
        bridge.subscribe("document_uploaded", on_document_uploaded)
        bridge.subscribe("chat_updated", on_chat_updated)

        # Simulate events
        bridge.publish("document_uploaded", "test.pdf")
        bridge.publish("chat_updated", "New message")

        assert len(messages) == 2
        assert "Document uploaded: test.pdf" in messages
        assert "Chat updated: New message" in messages


class TestPerformance:
    """Test performance characteristics of the architecture."""

    def test_component_build_performance(self):
        """Test that component building is reasonably fast."""
        import time

        class TestComponent(UIComponent):
            def build_interface(self):
                # Simulate some work
                return gr.Textbox()

            def register_events(self, demo):
                pass

            def get_component_refs(self):
                return {}

        container = ServiceContainer()
        registry = ComponentRegistry(container)

        # Register 10 components
        for i in range(10):
            registry.register_component_class(f"component_{i}", TestComponent)

        # Measure build time
        start = time.time()
        registry.build_all_components()
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second for 10 components)
        assert elapsed < 1.0

    def test_event_routing_performance(self):
        """Test that event routing is efficient."""
        import time

        router = EventRouter()

        # Register 100 handlers
        for i in range(100):
            router.register_handler(f"component_{i % 10}", "click", lambda: None)

        # Measure retrieval time
        start = time.time()
        for _ in range(1000):
            handlers = router.get_handlers_for_component("component_5")
        elapsed = time.time() - start

        # Should be very fast (< 0.1 seconds for 1000 lookups)
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
