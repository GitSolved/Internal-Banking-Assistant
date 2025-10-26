from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from injector import Provider, ScopeDecorator, singleton

from internal_assistant.di import create_application_injector
from internal_assistant.settings.settings import Settings, unsafe_settings
from internal_assistant.settings.settings_loader import merge_settings
from internal_assistant.utils.typing import T


class MockInjector:
    def __init__(self) -> None:
        self.test_injector = create_application_injector()

    def bind_mock(
        self,
        interface: type[T],
        mock: (T | (Callable[..., T] | Provider[T])) | None = None,
        *,
        scope: ScopeDecorator = singleton,
    ) -> T:
        if mock is None:
            mock = MagicMock()
        self.test_injector.binder.bind(interface, to=mock, scope=scope)
        return mock  # type: ignore

    def bind_settings(self, settings: dict[str, Any]) -> Settings:
        merged = merge_settings([unsafe_settings, settings])
        new_settings = Settings(**merged)
        self.test_injector.binder.bind(Settings, new_settings)
        return new_settings

    def get(self, interface: type[T]) -> T:
        return self.test_injector.get(interface)

    def clear_cache(self) -> None:
        """Clear the injector's instance cache to force recreation of singletons."""
        # First, close any Qdrant clients to release locks before recreating injector
        try:
            from internal_assistant.components.vector_store.vector_store_component import (
                VectorStoreComponent,
            )

            # Try to get and close the existing vector store client
            try:
                vector_store = self.test_injector.get(VectorStoreComponent)
                if vector_store and hasattr(vector_store, "close"):
                    vector_store.close()
            except Exception:
                # Client might not exist yet, that's fine
                pass
        except ImportError:
            pass

        # Now recreate the injector for fresh instances
        # This ensures all subsequent .get() calls create fresh instances
        self.test_injector = create_application_injector()


@pytest.fixture
def injector() -> MockInjector:
    # Ensure each test gets a completely fresh injector instance
    return MockInjector()
