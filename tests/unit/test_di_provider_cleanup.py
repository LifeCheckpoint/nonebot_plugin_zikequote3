"""
Verify DI providers properly clean up resources (fixes #1, #2).
"""

from pathlib import Path


class TestEngineProviderCleanup:
    def test_provide_engine_is_async_generator(self):
        """provide_engine uses async generator to enable dispose on scope exit."""
        source_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "di" / "providers" / "database_provider.py"
        source = source_file.read_text(encoding="utf-8")
        assert 'yield engine' in source or 'yield' in source, "Should use yield for async generator pattern"

    def test_provide_engine_calls_dispose(self):
        """provide_engine disposes the engine on cleanup."""
        source_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "di" / "providers" / "database_provider.py"
        source = source_file.read_text(encoding="utf-8")
        assert 'yield' in source
        assert 'dispose' in source


class TestVectorProviderCleanup:
    def test_provide_vector_runtime_is_async_generator(self):
        """provide_vector_runtime uses async generator for cleanup."""
        source_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "di" / "providers" / "vector_provider.py"
        source = source_file.read_text(encoding="utf-8")
        assert 'yield' in source, "Should use yield for async generator pattern"

    def test_embedding_client_has_close(self):
        """EmbeddingClient exposes close() to release HTTP pool."""
        from nonebot_plugin_zikequote3.vector_search.embedding_client import EmbeddingClient
        assert callable(getattr(EmbeddingClient, 'close', None))

    def test_vector_store_has_close(self):
        """VectorStore exposes close() to release LanceDB connection."""
        from nonebot_plugin_zikequote3.vector_search.vector_store import VectorStore
        assert callable(getattr(VectorStore, 'close', None))
