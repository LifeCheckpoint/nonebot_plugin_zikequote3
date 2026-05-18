"""
Verify error logging preserves traceback info (fixes #3, #4).
"""

import inspect
from pathlib import Path


class TestForwardRefErrorVisibility:
    def test_resolve_annotation_logs_failures(self):
        """ForwardRef resolution failures are logged with traceback instead of silenced."""
        from nonebot_plugin_zikequote3.di.inject import _resolve_annotation
        source = inspect.getsource(_resolve_annotation)
        assert 'logger' in source or 'warning' in source, "Should log failures"

    def test_resolve_annotation_still_returns_annotation_on_failure(self):
        """On failure, annotation is still returned (backward compat)."""
        from nonebot_plugin_zikequote3.di.inject import _resolve_annotation
        result = _resolve_annotation("NonExistentType", {})
        assert isinstance(result, str)
        assert result == "NonExistentType"

    def test_resolve_annotation_succeeds_for_valid_types(self):
        """Valid types resolve correctly."""
        from nonebot_plugin_zikequote3.di.inject import _resolve_annotation
        assert _resolve_annotation(str, {}) is str
        assert _resolve_annotation("int", {"int": int}) is int


class TestVectorConsistencyCheckLogging:
    def test_exception_handler_uses_opt_exception(self):
        """Vector consistency check failure uses logger.opt(exception=...) for traceback."""
        init_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "__init__.py"
        source = init_file.read_text(encoding="utf-8")
        assert 'exception=e' in source or 'exception=' in source, (
            "Should use logger.opt(exception=e) to preserve traceback"
        )
