"""
get_quote_list_cmd 命令处理器单元测试。

覆盖：
- handle_get_quote_list：获取语录列表（成功渲染 / 用户不存在 / 昵称匹配多人 / 无匹配用户）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_quote_list: MagicMock = getattr(
    _stub_cmd_def, "matcher_get_quote_list"
)

# handler 函数导入（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.get_quote_list_cmd import (  # noqa: E402
    handle_get_quote_list,
)

# 需要在运行时 patch 的模块路径常量
_CMD_MODULE = "nonebot_plugin_zikequote3.command.cmds.get_quote_list_cmd"


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_quote(
    *,
    quote_id: str = "Q-1",
    author_id: str = "111111",
    content: str = "语录内容",
) -> MagicMock:
    """创建模拟的语录对象。"""
    q = MagicMock()
    q.quote_id = quote_id
    q.author_id = author_id
    q.content = content
    q.image_content_uuid = None
    return q


class TestHandleGetQuoteList:
    """获取语录列表命令。"""

    async def test_list_success_default_user(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """未指定用户时使用发送者 QQ：成功渲染列表图片。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.get_personal_quotes = AsyncMock(
            return_value=([_make_quote()], 1, 0, 0),
        )
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.user_exists = AsyncMock(return_value=True)
        mock_user_svc.get_display_name = AsyncMock(return_value="测试用户")
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            QuoteReadService: mock_read_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
        })

        # Act & Assert — 运行时 patch 模板渲染和辅助函数
        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=[]),
            patch(f"{_CMD_MODULE}.render_list",
                  return_value="<html>list</html>"),
            patch(f"{_CMD_MODULE}.parse_page_range",
                  return_value=(0, 9)),
            pytest.raises(FinishedException),
        ):
            await handle_get_quote_list(
                event=mock_group_event,
                range=_make_match(),
                at_user=_make_match(),
                qq=_make_match(),
                nickname=_make_match(),
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                quote_read_svc=mock_read_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证使用发送者 QQ
        mock_user_svc.user_exists.assert_awaited_once_with("654321")
        mock_render_svc.render.assert_awaited_once()

    async def test_user_not_exists(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """用户不存在：走资源未找到分支，而不是通用内部错误分支。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.user_exists = AsyncMock(return_value=False)
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            QuoteReadService: mock_read_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_quote_list(
                event=mock_group_event,
                range=_make_match(),
                at_user=_make_match(),
                qq=_make_match(),
                nickname=_make_match(),
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                quote_read_svc=mock_read_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 进入资源未找到分支，而不是通用内部错误分支
        finish_calls = matcher_get_quote_list.finish.call_args_list
        assert any("未找到" in str(c) for c in finish_calls)
        assert all("发生错误" not in str(c) for c in finish_calls)

    async def test_nickname_multiple_users(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """昵称匹配到多个用户：提示用户使用 @ 或 QQ 号。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(
            return_value=["111111", "222222"],
        )
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            QuoteReadService: mock_read_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
        })

        nickname_match = _make_match(available=True, result="测试")

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_quote_list(
                event=mock_group_event,
                range=_make_match(),
                at_user=_make_match(),
                qq=_make_match(),
                nickname=nickname_match,
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                quote_read_svc=mock_read_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含多用户提示
        finish_calls = matcher_get_quote_list.finish.call_args_list
        assert any("多个用户" in str(c) for c in finish_calls)

    async def test_nickname_no_user_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """昵称无匹配用户：提示没有找到。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            QuoteReadService: mock_read_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
        })

        nickname_match = _make_match(available=True, result="不存在的人")

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_quote_list(
                event=mock_group_event,
                range=_make_match(),
                at_user=_make_match(),
                qq=_make_match(),
                nickname=nickname_match,
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                quote_read_svc=mock_read_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "没有找到" 提示
        finish_calls = matcher_get_quote_list.finish.call_args_list
        assert any("没有找到" in str(c) for c in finish_calls)
