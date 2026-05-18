"""
P1 Bug #1: CollectingConfig allows at_least > at_most with no validation.
P1 Bug #2: set_group_config writes without concurrency lock.
"""

import pytest


class TestCollectingConfigValidation:
    def test_rejects_at_least_greater_than_at_most(self):
        """at_least_selections > at_most_selections should raise validation error."""
        from nonebot_plugin_zikequote3.config import CollectingConfig
        with pytest.raises(ValueError):
            CollectingConfig(at_least_selections=5, at_most_selections=3)

    def test_rejects_negative_selections(self):
        """Negative selection counts should raise validation error."""
        from nonebot_plugin_zikequote3.config import CollectingConfig
        with pytest.raises(ValueError):
            CollectingConfig(at_least_selections=-1, at_most_selections=3)

    def test_accepts_valid_range(self):
        """Valid range passes validation."""
        from nonebot_plugin_zikequote3.config import CollectingConfig
        cfg = CollectingConfig(at_least_selections=2, at_most_selections=5)
        assert cfg.at_least_selections == 2
        assert cfg.at_most_selections == 5


class TestSetGroupConfigNoLock:
    def test_set_group_config_has_no_concurrency_protection(self):
        """set_group_config should use a lock but doesn't."""
        import inspect
        from nonebot_plugin_zikequote3.services.config_service import ConfigService
        source = inspect.getsource(ConfigService.set_group_config)
        has_lock = 'lock' in source.lower() or 'async with' in source
        # BUG: no lock → concurrent calls overwrite each other
        assert has_lock, (
            "BUG CONFIRMED: set_group_config has no concurrency protection.\n"
            "Unlike modify_single_value which uses asyncio.Lock, this method\n"
            "can lose writes when called concurrently."
        )
