"""
Component Registry

This module provides a centralized registry for managing UI components in the
Internal Assistant system. It handles component registration, dependency resolution,
and lifecycle management.

The ComponentRegistry ensures:
- Components are properly initialized with their dependencies
- Build order respects component dependencies
- Event registration happens in correct sequence
- Component references are available for cross-component communication
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from .ui_component import UIComponent, ServiceContainer

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for managing UI components and their dependencies.

    This class provides centralized management of UI components, including:
    - Component registration and retrieval
    - Dependency injection and validation
    - Build order calculation based on dependencies
    - Component lifecycle management
    """

    def __init__(self, service_container: ServiceContainer):
        """
        Initialize the component registry.

        Args:
            service_container: Container with available services
        """
        self.service_container = service_container
        self._components: Dict[str, UIComponent] = {}
        self._component_classes: Dict[str, type] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._built_components: Set[str] = set()

    def register_component_class(
        self, name: str, component_class: type, dependencies: Optional[List[str]] = None
    ) -> None:
        """
        Register a component class that can be instantiated later.

        Args:
            name: Unique name for this component
            component_class: Class that extends UIComponent
            dependencies: List of other component names this depends on
        """
        if not issubclass(component_class, UIComponent):
            raise ValueError(
                f"Component class {component_class} must extend UIComponent"
            )

        self._component_classes[name] = component_class
        self._dependencies[name] = set(dependencies or [])
        logger.debug(f"Registered component class: {name}")

    def register_component_instance(self, component: UIComponent) -> None:
        """
        Register an already-instantiated component.

        Args:
            component: Component instance to register
        """
        self._components[component.component_id] = component
        if component.component_id not in self._dependencies:
            self._dependencies[component.component_id] = set()
        logger.debug(f"Registered component instance: {component.component_id}")

    def get_component(self, name: str) -> UIComponent:
        """
        Get a component by name, instantiating if necessary.

        Args:
            name: Name of the component to retrieve

        Returns:
            The component instance

        Raises:
            KeyError: If component is not registered
        """
        if name in self._components:
            return self._components[name]

        if name in self._component_classes:
            component = self._instantiate_component(name)
            self._components[name] = component
            return component

        raise KeyError(f"Component '{name}' not registered")

    def has_component(self, name: str) -> bool:
        """Check if a component is registered."""
        return name in self._components or name in self._component_classes

    def get_all_components(self) -> Dict[str, UIComponent]:
        """Get all instantiated components."""
        # Ensure all registered classes are instantiated
        for name in self._component_classes:
            if name not in self._components:
                self.get_component(name)
        return self._components.copy()

    def get_build_order(self) -> List[str]:
        """
        Calculate the order components should be built based on dependencies.

        Returns:
            List of component names in build order

        Raises:
            ValueError: If circular dependencies detected
        """
        # Topological sort to handle dependencies
        visited = set()
        temp_mark = set()
        result = []

        def visit(name: str):
            if name in temp_mark:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name in visited:
                return

            temp_mark.add(name)

            # Visit dependencies first
            for dep in self._dependencies.get(name, set()):
                if self.has_component(dep):
                    visit(dep)

            temp_mark.remove(name)
            visited.add(name)
            result.append(name)

        # Visit all components
        all_components = set(self._component_classes.keys()) | set(
            self._components.keys()
        )
        for name in all_components:
            if name not in visited:
                visit(name)

        return result

    def build_all_components(self) -> Dict[str, Any]:
        """
        Build all components in dependency order.

        Returns:
            Dictionary mapping component names to their built interfaces
        """
        build_order = self.get_build_order()
        built_interfaces = {}

        for name in build_order:
            if name not in self._built_components:
                component = self.get_component(name)

                # Validate dependencies
                missing_deps = component.validate_dependencies()
                if missing_deps:
                    logger.warning(
                        f"Component {name} missing dependencies: {missing_deps}"
                    )

                # Build the component
                interface = component.build_interface()
                component._mark_built()

                built_interfaces[name] = interface
                self._built_components.add(name)

                logger.debug(f"Built component: {name}")

        return built_interfaces

    def register_all_events(self, demo) -> None:
        """
        Register events for all built components.

        Args:
            demo: The main gr.Blocks context
        """
        for name in self._built_components:
            component = self._components[name]
            component.register_events(demo)
            logger.debug(f"Registered events for component: {name}")

    def get_component_refs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get component references from all built components.

        Returns:
            Nested dictionary: {component_name: {ref_name: component}}
        """
        refs = {}
        for name, component in self._components.items():
            if component.is_built():
                refs[name] = component.get_component_refs()
        return refs

    def validate_all_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate dependencies for all registered components.

        Returns:
            Dictionary mapping component names to lists of missing dependencies
        """
        validation_results = {}

        for name in self._component_classes:
            component = self.get_component(name)
            missing = component.validate_dependencies()
            if missing:
                validation_results[name] = missing

        return validation_results

    def _instantiate_component(self, name: str) -> UIComponent:
        """
        Instantiate a component class with proper service injection.

        Args:
            name: Name of the component to instantiate

        Returns:
            Instantiated component
        """
        component_class = self._component_classes[name]

        # Create services dictionary for this component
        services = self.service_container.get_all()

        # Instantiate the component
        component = component_class(component_id=name, services=services)

        logger.debug(f"Instantiated component: {name}")
        return component


class ComponentFactory:
    """
    Factory for creating common component configurations.

    This class provides convenient methods for creating and configuring
    standard component setups used throughout the application.
    """

    @staticmethod
    def create_basic_registry(service_container: ServiceContainer) -> ComponentRegistry:
        """
        Create a component registry with basic component types.

        Args:
            service_container: Container with application services

        Returns:
            Configured component registry
        """
        registry = ComponentRegistry(service_container)

        # Register basic component types (these will be defined in subsequent phases)
        # registry.register_component_class("chat", ChatComponent)
        # registry.register_component_class("documents", DocumentComponent)
        # registry.register_component_class("feeds", FeedComponent)
        # registry.register_component_class("sidebar", SidebarComponent)

        return registry

    @staticmethod
    def create_service_container_from_injector(injector) -> ServiceContainer:
        """
        Create a service container from the application's dependency injector.

        Args:
            injector: Application dependency injector

        Returns:
            Service container with injected services
        """
        from internal_assistant.server.chat.chat_service import ChatService
        from internal_assistant.server.ingest.ingest_service import IngestService
        from internal_assistant.server.feeds.feeds_service import RSSFeedService
        from internal_assistant.server.chunks.chunks_service import ChunksService
        from internal_assistant.server.recipes.summarize.summarize_service import (
            SummarizeService,
        )

        container = ServiceContainer()

        # Register services that UI components need
        try:
            container.register("chat", injector.get(ChatService))
            container.register("ingest", injector.get(IngestService))
            container.register("feeds", injector.get(RSSFeedService))
            container.register("chunks", injector.get(ChunksService))
            container.register("summarize", injector.get(SummarizeService))
        except Exception as e:
            logger.warning(f"Could not register some services: {e}")

        return container
