"""
P1 Bugs #12, #13, #14, #15: Vector search bugs.
"""
import inspect
from pathlib import Path


class TestUpsertSilentException:
    def test_upsert_delete_step_has_proper_error_handling(self):
        """upsert should NOT use bare except Exception: pass."""
        vs_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "vector_search" / "vector_store.py"
        source = vs_file.read_text(encoding="utf-8")
        lines = source.split('\n')
        found_bare_pass = False
        for i, line in enumerate(lines):
            if 'except Exception' in line and 'pass' in line:
                found_bare_pass = True
            elif 'except Exception' in line:
                # Check next line for 'pass'
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                if next_line == 'pass' or next_line.startswith('pass'):
                    found_bare_pass = True
        assert not found_bare_pass, (
            "BUG CONFIRMED: upsert has bare 'except Exception: pass' that silently\n"
            "swallows all errors from table.delete(), masking connection/schema failures."
        )


class TestIsAvailableNoLogging:
    def test_is_available_logs_errors(self):
        """is_available should log exceptions before returning False."""
        from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService
        source = inspect.getsource(VectorSearchService.is_available)
        has_logging = 'logger' in source
        assert has_logging, (
            "BUG CONFIRMED: is_available catches all exceptions and returns False\n"
            "with zero diagnostic output. Operators cannot distinguish 'not available'\n"
            "from 'LanceDB crash'."
        )


class TestReindexLockTOCTOU:
    def test_index_quote_checks_lock_before_acquire(self):
        """index_quote/remove_quote check .locked() then await, creating TOCTOU gap."""
        from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService
        source = inspect.getsource(VectorSearchService.index_quote)
        lines = source.split('\n')
        found_check = False
        has_await_after_check = False
        for line in lines:
            if '.locked()' in line and 'reindex_lock' in line:
                found_check = True
            if found_check and ('await' in line or 'async with' in line):
                has_await_after_check = True
                break
        assert not (found_check and has_await_after_check), (
            "BUG CONFIRMED: index_quote checks reindex_lock.locked() then has an await\n"
            "before acquiring the lock. Another task can grab the lock in between."
        )


class TestEmbeddingDimensionValidation:
    def test_embed_texts_validates_dimensions(self):
        """embed_texts should compare returned vector length to config dimensions."""
        from nonebot_plugin_zikequote3.vector_search.embedding_client import EmbeddingClient
        source = inspect.getsource(EmbeddingClient.embed_texts)
        # Look for a validation that compares len(vector) to self._config.dimensions
        # Not just any occurrence of "dimension" — the config field uses that word.
        lines = source.split('\n')
        found_validation = False
        for line in lines:
            stripped = line.strip()
            # Skip docstrings/comments
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # Check if line validates returned vector length against dimensions config
            if 'len(' in stripped and ('dimension' in stripped.lower() or 'self._config.dimensions' in stripped):
                found_validation = True
                break
        assert found_validation, (
            "BUG CONFIRMED: embed_texts returns vectors without comparing their actual\n"
            "length to self._config.dimensions. Dimension mismatch causes cryptic LanceDB errors."
        )
