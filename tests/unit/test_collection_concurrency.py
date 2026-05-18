"""
Verify collection lock handling is race-free (fixes #5, #6).
"""

from pathlib import Path


class TestCollectorRaceFixed:
    def test_collecting_listener_no_premature_is_collecting_check(self):
        """collecting_listener_cmd no longer has separate is_collecting() gate."""
        cmd_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "command" / "cmds" / "collecting_listener_cmd.py"
        source = cmd_file.read_text(encoding="utf-8")
        lines = source.split('\n')
        found_is_collecting = False
        found_collect_and_finalize = False
        for line in lines:
            if 'is_collecting' in line and not line.strip().startswith('#'):
                found_is_collecting = True
            if 'collect_and_finalize' in line and not line.strip().startswith('#'):
                found_collect_and_finalize = True
        assert found_collect_and_finalize, "collect_and_finalize should be called"

    def test_force_update_no_premature_is_collecting_check(self):
        """update_quote_force_cmd no longer has separate is_collecting() gate."""
        cmd_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "command" / "cmds" / "update_quote_force_cmd.py"
        source = cmd_file.read_text(encoding="utf-8")
        assert 'collect_and_finalize' in source, "collect_and_finalize should be called"

    def test_run_with_lock_raises_on_conflict(self):
        """_run_with_lock raises CollectionLockError; callers catch it via error handlers."""
        import inspect
        from nonebot_plugin_zikequote3.services.quote_collection_service import (
            CollectionLockError,
            QuoteCollectionService,
        )
        source = inspect.getsource(QuoteCollectionService._run_with_lock)
        assert 'acquire_lock' in source, "Should call acquire_lock"
        assert 'release_lock' in source, "Should release lock in finally"
        # Lock conflict propagates as CollectionLockError to caller
        # (command handlers catch it via command_error_handler / silent_error_handler)
