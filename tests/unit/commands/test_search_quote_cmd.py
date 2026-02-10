"""
search_quote_cmd 命令处理器单元测试。

覆盖：
- handle_search_quote：搜索语录（成功搜索 / 无结果 / max_result 参数校验）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_search_quote: MagicMock = getattr(
    _stub_cmd_def, "matcher_search_quote"
)

# patch 模板渲染和辅助函数，避免 jinja2 依赖
with (
    patch(
        "nonebot_plugin_zikequote3.command.cmds.search_quote_cmd.render_list",
        return_value="<html>search</html>",
    ),
    patch(
        "nonebot_plugin_zikequote3.command.cmds.search_quote_cmd.transform_quotes_to_template_boxes",
        new_callable=AsyncMock,
        return_value=[],
    ),
):
    from nonebot_plugin_zikequote3.command.cmds.search_quote_cmd import (
        handle_search_quote,
    )


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_query(available: bool = True, result=None) -> MagicMock:
    """创建模拟的 Query 对象。"""
    q = MagicMock()
    q.available = available
    q.result = result
    return q


def _make_keyword_match(text: str) -> MagicMock:
    """创建模拟的 keyword Match（UniMessage 类型）。"""
    uni_msg = MagicMock()
    uni_msg.extract_plain_text.return_value = text
    return _make_match(available=True, result=uni_msg)


class TestHandleSearchQuote:
    """搜索语录命令。"""

    async def test_search_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """关键词搜索成功：渲染列表图片。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.search_quotes = AsyncMock(return_value=([], 0))
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                qq=_make_match(),
                max_result=_make_match(),
                keyword=_make_keyword_match("测试关键词"),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证搜索服务调用
        mock_stats_svc.search_quotes.assert_awaited_once()
        mock_render_svc.render.assert_awaited_once()

    async def test_max_result_too_small(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """max_result < 1：提示用户。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                qq=_make_match(),
                max_result=_make_match(available=True, result=0),
                keyword=_make_keyword_match("测试"),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含提示
        finish_calls = matcher_search_quote.finish.call_args_list
        assert any("至少为 1" in str(c) for c in finish_calls)

    async def test_render_failure(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """渲染失败：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.search_quotes = AsyncMock(return_value=([], 0))
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed"),
        )

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                qq=_make_match(),
                max_result=_make_match(),
                keyword=_make_keyword_match("测试"),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_search_quote.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
