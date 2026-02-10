"""
get_user_info_cmd 命令处理器单元测试。

覆盖：
- handle_get_user_info：获取用户信息卡片（成功 / 用户不存在 / 昵称匹配多人）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_user_info: MagicMock = getattr(
    _stub_cmd_def, "matcher_get_user_info"
)

# patch 模板渲染和 base64 工具，避免 jinja2 依赖
with (
    patch(
        "nonebot_plugin_zikequote3.command.cmds.get_user_info_cmd.render_user_info",
        return_value="<html>user_info</html>",
    ),
    patch(
        "nonebot_plugin_zikequote3.command.cmds.get_user_info_cmd.to_data_uri",
        return_value="data:image/png;base64,FAKE",
    ),
):
    from nonebot_plugin_zikequote3.command.cmds.get_user_info_cmd import (
        handle_get_user_info,
    )


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_nickname_record(name: str) -> MagicMock:
    """创建模拟的昵称记录。"""
    r = MagicMock()
    r.name = name
    return r


class TestHandleGetUserInfo:
    """获取用户信息卡片命令。"""

    async def test_success_default_user(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """未指定用户时使用发送者 QQ：成功渲染用户信息卡片。"""
        # Arrange
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.user_exists = AsyncMock(return_value=True)
        mock_user_svc.get_display_name = AsyncMock(return_value="测试用户")
        mock_user_svc.get_current_nickname = AsyncMock(return_value="昵称")
        mock_user_svc.get_current_group_card = AsyncMock(return_value="群名片")
        mock_user_svc.get_avatar = AsyncMock(return_value=b"\x89PNG")
        mock_user_svc.get_all_nicknames = AsyncMock(return_value=[])
        mock_user_svc.get_all_group_nicknames = AsyncMock(return_value=[])

        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.count_author_quotes_in_group = AsyncMock(return_value=10)
        mock_stats_svc.get_group_member_quote_counts = AsyncMock(
            return_value=[{"qq_id": "654321", "quote_count": 10}],
        )

        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")

        patch_container({
            UserService: mock_user_svc,
            StatisticsService: mock_stats_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_user_info(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                nickname=_make_match(),
                user_svc=mock_user_svc,
                stats_svc=mock_stats_svc,
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
        """用户不存在：抛出 ValueError，被 command_error_handler 捕获。"""
        # Arrange
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.user_exists = AsyncMock(return_value=False)

        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)

        patch_container({
            UserService: mock_user_svc,
            StatisticsService: mock_stats_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_user_info(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                nickname=_make_match(),
                user_svc=mock_user_svc,
                stats_svc=mock_stats_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含错误消息
        finish_calls = matcher_get_user_info.finish.call_args_list
        assert any(
            "发生错误" in str(c) or "没有找到" in str(c)
            for c in finish_calls
        )

    async def test_nickname_multiple_users(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """昵称匹配到多个用户：提示使用 @ 或 QQ 号。"""
        # Arrange
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(
            return_value=["111111", "222222"],
        )

        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)

        patch_container({
            UserService: mock_user_svc,
            StatisticsService: mock_stats_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        nickname_match = _make_match(available=True, result="测试")

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_user_info(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                nickname=nickname_match,
                user_svc=mock_user_svc,
                stats_svc=mock_stats_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含多用户提示
        finish_calls = matcher_get_user_info.finish.call_args_list
        assert any("多个用户" in str(c) for c in finish_calls)

    async def test_render_failure(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """渲染失败：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.user_exists = AsyncMock(return_value=True)
        mock_user_svc.get_display_name = AsyncMock(return_value="测试用户")
        mock_user_svc.get_current_nickname = AsyncMock(return_value="昵称")
        mock_user_svc.get_current_group_card = AsyncMock(return_value="群名片")
        mock_user_svc.get_avatar = AsyncMock(return_value=b"\x89PNG")
        mock_user_svc.get_all_nicknames = AsyncMock(return_value=[])
        mock_user_svc.get_all_group_nicknames = AsyncMock(return_value=[])

        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.count_author_quotes_in_group = AsyncMock(return_value=5)
        mock_stats_svc.get_group_member_quote_counts = AsyncMock(
            return_value=[{"qq_id": "654321", "quote_count": 5}],
        )

        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed"),
        )

        patch_container({
            UserService: mock_user_svc,
            StatisticsService: mock_stats_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_user_info(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                nickname=_make_match(),
                user_svc=mock_user_svc,
                stats_svc=mock_stats_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_get_user_info.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
