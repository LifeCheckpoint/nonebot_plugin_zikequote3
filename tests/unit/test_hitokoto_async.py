"""
Verify get_hitokoto is now async (fix #7).
"""

import asyncio
import inspect


class TestHitokotoAsync:
    def test_get_hitokoto_is_async_function(self):
        """get_hitokoto is now an async coroutine function."""
        from nonebot_plugin_zikequote3.utils.hitokoto import get_hitokoto
        assert asyncio.iscoroutinefunction(get_hitokoto)

    def test_get_hitokoto_uses_async_http(self):
        """get_hitokoto uses httpx.AsyncClient, not synchronous requests."""
        from pathlib import Path
        hitokoto_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "utils" / "hitokoto.py"
        source = hitokoto_file.read_text(encoding="utf-8")
        assert 'AsyncClient' in source or 'await' in source, "Should use async HTTP"
        assert 'requests.get' not in source, "Should NOT use synchronous requests.get"

    def test_get_hitokoto_empty_url_returns_none(self):
        """Empty URL returns (None, None) gracefully."""
        from nonebot_plugin_zikequote3.utils.hitokoto import get_hitokoto
        result = asyncio.run(get_hitokoto(""))
        assert result == (None, None)
