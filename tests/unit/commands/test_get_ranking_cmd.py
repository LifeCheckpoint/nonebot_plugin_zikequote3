"""
get_ranking_cmd 命令处理器单元测试。

覆盖：
- handle_get_ranking：获取排行榜（成功渲染 / 语录数为0 / 排行数据为空 / 渲染失败）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_collection_service import QuoteCollectionService
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_ranking: MagicMock = getattr(
    _stub_cmd_def, "matcher_get_ranking"
)

# patch 模板渲染函数，避免 jinja2 依赖
with patch(
    "nonebot_plugin_zikequote3.command.cmds.get_ranking_cmd.render_rank",
    return_value="<html>rank</html>",
):
    from nonebot_plugin_zikequote3.command.cmds.get_ranking_cmd import (
        handle_get_ranking,
    )


def _make_group_info(name: str = "测试群") -> MagicMock:
    """创建模拟的群组信息。"""
    g = MagicMock()
    g.name = name
    return g


def _make_quote_with_timestamp(ts) -> MagicMock:
    """创建带时间戳的模拟语录。"""
    q = MagicMock()
    q.time_stamp = ts
    return q


class TestHandleGetRanking:
    """获取排行榜命令。"""

    async def test_ranking_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """成功获取排行榜：渲染图片。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.get_group_statistics = AsyncMock(return_value={
            "total_quotes": 50,
            "unique_authors": 5,
            "total_shows": 100,
        })
        mock_stats_svc.get_group_member_quote_counts = AsyncMock(
            return_value=[
                {"qq_id": "111111", "quote_count": 20},
                {"qq_id": "222222", "quote_count": 15},
            ],
        )

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="用户A")
        mock_user_svc.get_avatar = AsyncMock(return_value=b"\x89PNG")

        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.get_group = AsyncMock(
            return_value=_make_group_info("测试群"),
        )

        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group_and_author = AsyncMock(
            return_value=[],
        )

        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")

        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.get_queue_count = AsyncMock(return_value=3)

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.max_rank_user_num = 40
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            GroupService: mock_group_svc,
            QuoteReadService: mock_read_svc,
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_ranking(
                event=mock_group_event,
                arg=mock_arg,
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                group_svc=mock_group_svc,
                quote_read_svc=mock_read_svc,
                collection_svc=mock_collection_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证服务调用
        mock_stats_svc.get_group_statistics.assert_awaited_once_with("123456")
        mock_render_svc.render.assert_awaited_once()

    async def test_zero_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """语录数为 0：走操作失败分支，而不是通用内部错误分支。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.get_group_statistics = AsyncMock(return_value={
            "total_quotes": 0,
            "unique_authors": 0,
            "total_shows": 0,
        })

        mock_user_svc = AsyncMock(spec=UserService)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.get_queue_count = AsyncMock(return_value=0)

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.max_rank_user_num = 40
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            GroupService: mock_group_svc,
            QuoteReadService: mock_read_svc,
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_ranking(
                event=mock_group_event,
                arg=mock_arg,
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                group_svc=mock_group_svc,
                quote_read_svc=mock_read_svc,
                collection_svc=mock_collection_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 进入操作失败分支，而不是通用内部错误分支
        finish_calls = matcher_get_ranking.finish.call_args_list
        assert any("操作失败" in str(c) for c in finish_calls)
        assert any("语录数为 0" in str(c) for c in finish_calls)
        assert all("发生错误" not in str(c) for c in finish_calls)

    async def test_render_failure(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """渲染失败：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.get_group_statistics = AsyncMock(return_value={
            "total_quotes": 10,
            "unique_authors": 2,
            "total_shows": 20,
        })
        mock_stats_svc.get_group_member_quote_counts = AsyncMock(
            return_value=[
                {"qq_id": "111111", "quote_count": 10},
            ],
        )

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="用户A")
        mock_user_svc.get_avatar = AsyncMock(return_value=None)

        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.get_group = AsyncMock(
            return_value=_make_group_info("测试群"),
        )

        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group_and_author = AsyncMock(
            return_value=[],
        )

        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed"),
        )

        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.get_queue_count = AsyncMock(return_value=0)

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.max_rank_user_num = 40
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            StatisticsService: mock_stats_svc,
            UserService: mock_user_svc,
            GroupService: mock_group_svc,
            QuoteReadService: mock_read_svc,
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_ranking(
                event=mock_group_event,
                arg=mock_arg,
                stats_svc=mock_stats_svc,
                user_svc=mock_user_svc,
                group_svc=mock_group_svc,
                quote_read_svc=mock_read_svc,
                collection_svc=mock_collection_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_get_ranking.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
