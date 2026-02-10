"""
random_quote_card_cmd 命令处理器单元测试。

覆盖：
- handle_random_quote_card：随机语录卡片（成功生成卡片 / 无语录 / 渲染失败降级 / 关键词搜索）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_random_quote_card: MagicMock = getattr(
    _stub_cmd_def, "matcher_random_quote_card"
)

# patch card_template.render_card，避免 jinja2 模板渲染依赖
with patch(
    "nonebot_plugin_zikequote3.command.cmds.random_quote_card_cmd.card_template"
) as _mock_card_tpl:
    _mock_card_tpl.render_card = MagicMock(return_value="<html>card</html>")
    from nonebot_plugin_zikequote3.command.cmds.random_quote_card_cmd import (
        handle_random_quote_card,
    )


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Alconna Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_quote_result(
    *,
    quote_id: str = "Q-100",
    author_id: str = "111111",
    content: str = "经典语录卡片内容",
    image_content_uuid: str | None = None,
    group_id: str = "123456",
) -> MagicMock:
    """创建模拟的语录查询结果。"""
    q = MagicMock()
    q.quote_id = quote_id
    q.author_id = author_id
    q.content = content
    q.image_content_uuid = image_content_uuid
    q.group_id = group_id
    return q


def _make_review(
    *,
    review_id: str = "R-1",
    author_id: str = "222222",
    content: str = "好语录！",
) -> MagicMock:
    """创建模拟的评论对象。"""
    r = MagicMock()
    r.review_id = review_id
    r.author_id = author_id
    r.content = content
    return r


class TestHandleRandomQuoteCard:
    """随机语录卡片命令。"""

    async def test_card_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """成功生成卡片：获取语录、渲染 HTML、发送图片。"""
        # Arrange
        q_result = _make_quote_result()
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=[q_result])
        mock_read_svc.get_quote_with_reviews = AsyncMock(
            return_value=(q_result, [_make_review()]),
        )
        mock_read_svc.increment_show_time = AsyncMock(return_value=None)

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="语录作者")
        mock_user_svc.sync_nickname = AsyncMock(return_value=None)
        mock_user_svc.sync_group_card = AsyncMock(return_value=None)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act — 成功路径使用 send() 发送卡片
        await handle_random_quote_card(
            event=mock_group_event,
            bot=mock_bot,
            at_user=_make_match(),
            text=_make_match(),
            quote_read_svc=mock_read_svc,
            quote_write_svc=mock_write_svc,
            user_svc=mock_user_svc,
            image_store=mock_image_store,
            html_render_svc=mock_render_svc,
        )

        # 验证服务调用
        mock_read_svc.get_quotes_by_group.assert_awaited_once_with("123456")
        mock_render_svc.render.assert_awaited_once()
        matcher_random_quote_card.send.assert_awaited()

    async def test_no_quote_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """无符合条件的语录：提示用户。"""
        # Arrange
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=[])

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_random_quote_card(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "没有找到" 提示
        finish_calls = matcher_random_quote_card.finish.call_args_list
        assert any("没有找到" in str(c) for c in finish_calls)

    async def test_render_failure(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """渲染失败：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        q_result = _make_quote_result()
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=[q_result])
        mock_read_svc.get_quote_with_reviews = AsyncMock(
            return_value=(q_result, []),
        )

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="作者")
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed"),
        )

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_random_quote_card(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_random_quote_card.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)

    async def test_keyword_search(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """带关键词搜索：通过 QueryResolver 解析为 KEYWORD 意图。"""
        # Arrange
        q_result = _make_quote_result(content="包含关键词的语录")
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.search_quotes = AsyncMock(return_value=[q_result])
        mock_read_svc.get_quote_with_reviews = AsyncMock(
            return_value=(q_result, []),
        )
        mock_read_svc.increment_show_time = AsyncMock(return_value=None)

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="作者")
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act
        await handle_random_quote_card(
            event=mock_group_event,
            bot=mock_bot,
            at_user=_make_match(),
            text=_make_match(available=True, result="关键词"),
            quote_read_svc=mock_read_svc,
            quote_write_svc=mock_write_svc,
            user_svc=mock_user_svc,
            image_store=mock_image_store,
            html_render_svc=mock_render_svc,
        )

        # 验证 search_quotes 被调用（关键词搜索路径）
        mock_read_svc.search_quotes.assert_awaited_once_with(
            "关键词", "123456",
        )
