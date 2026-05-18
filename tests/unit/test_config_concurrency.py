"""
Verify config_service.modify_single_value has concurrency protection (fix #8).
"""

import inspect


class TestConfigConcurrencyProtection:
    def test_modify_single_value_uses_async_lock(self):
        """modify_single_value wraps read-modify-write in asyncio.Lock."""
        from nonebot_plugin_zikequote3.services.config_service import ConfigService
        source = inspect.getsource(ConfigService.modify_single_value)
        assert 'asyncio.Lock' in source or 'Lock' in source, "Should use asyncio.Lock"
        assert 'async with lock' in source or 'async with' in source, "Should use async context manager"

    def test_config_service_init_has_lock_dict(self):
        """ConfigService.__init__ creates _config_locks dictionary."""
        from nonebot_plugin_zikequote3.services.config_service import ConfigService
        source = inspect.getsource(ConfigService.__init__)
        assert '_config_locks' in source, "Should initialize lock dictionary"
