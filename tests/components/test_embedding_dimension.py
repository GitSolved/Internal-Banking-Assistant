"""Test to ensure mock embedding dimensions match configuration."""

from internal_assistant.components.embedding.embedding_component import (
    EmbeddingComponent,
)
from internal_assistant.settings.settings import Settings
from tests.fixtures.mock_injector import MockInjector


def test_mock_embedding_matches_config_dimension(injector: MockInjector) -> None:
    """Verify mock embedding uses configured embed_dim, not hardcoded value.

    This test prevents regression of the bug where MockEmbedding was hardcoded
    to 384 dimensions while production config specifies 768 dimensions.

    See: embedding_component.py:148-152
    Fix: MockEmbedding now uses settings.embedding.embed_dim
    """
    # Get settings
    settings = injector.get(Settings)
    configured_dim = settings.embedding.embed_dim

    # Override to use mock mode
    injector.bind_settings({"embedding": {"mode": "mock"}})

    # Create embedding component
    embedding_component = injector.get(EmbeddingComponent)

    # Test that embedding dimension matches config
    test_text = "test embedding"
    embedding = embedding_component.embedding_model.get_text_embedding(test_text)

    assert len(embedding) == configured_dim, (
        f"Mock embedding dimension {len(embedding)} does not match "
        f"configured embed_dim {configured_dim}. "
        f"Update MockEmbedding initialization in embedding_component.py"
    )


def test_mock_embedding_produces_768_dimensions() -> None:
    """Verify mock embeddings produce 768-dimensional vectors.

    This is the expected dimension for nomic-embed-text-v1.5 model.
    If this test fails, check config/settings.yaml:embed_dim setting.
    """
    from internal_assistant.di import global_injector

    # Get embedding component in mock mode
    settings = global_injector.get(Settings)

    # Only run if in mock mode (test environment)
    if settings.embedding.mode == "mock":
        embedding_component = global_injector.get(EmbeddingComponent)
        test_embedding = embedding_component.embedding_model.get_text_embedding("test")

        assert len(test_embedding) == 768, (
            f"Expected 768-dimensional embeddings (nomic-embed-text-v1.5), "
            f"but got {len(test_embedding)} dimensions"
        )
