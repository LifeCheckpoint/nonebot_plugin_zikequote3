"""
random_quote_cmd 命令处理器单元测试。

覆盖：
- handle_random_quote：随机语录（成功-纯文本 / 成功-含图片 / 无语录 / 服务异常 / 关键词搜索）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_random_quote: MagicMock = getattr(
    _stub_cmd_def, "matcher_random_quote"
)

# patch send_quote 模板函数，避免 jinja2 模板渲染依赖
with patch(
    "nonebot_plugin_zikequote3.command.cmds.random_quote_cmd.send_quote",
    side_effect=lambda author, content: f"「{content}」—— {author}",
):
    # handler 函数（conftest stub 保证 @matcher.handle() 透传）
    from nonebot_plugin_zikequote3.command.cmds.random_quote_cmd import (  # noqa: E402
        handle_random_quote,
    )


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Alconna Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_quote_result(
    *,
    quote_id: str = "Q-42",
    author_id: str = "111111",
    content: str | None = "经典语录内容",
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


class TestHandleRandomQuote:
    """随机语录命令。"""

    async def test_text_quote_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """获取纯文本语录：发送成功。"""
        # Arrange
        q_result = _make_quote_result()
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=[q_result])
        mock_read_svc.increment_show_time = AsyncMock(return_value=None)

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="语录作者")
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
        })

        # Act — 成功路径使用 send() 而非 finish()，不抛出 FinishedException
        await handle_random_quote(
            event=mock_group_event,
            bot=mock_bot,
            at_user=_make_match(),
            text=_make_match(),
            quote_read_svc=mock_read_svc,
            quote_write_svc=mock_write_svc,
            user_svc=mock_user_svc,
            image_store=mock_image_store,
        )

        # 验证服务调用
        mock_read_svc.get_quotes_by_group.assert_awaited_once_with("123456")
        mock_user_svc.get_display_name.assert_awaited_once_with(
            "111111", "123456",
        )
        # send 被调用（发送语录消息）
        matcher_random_quote.send.assert_awaited()

    async def test_no_quote_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """无符合条件的语录：提示用户。"""
        # Arrange
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.search_quotes = AsyncMock(return_value=[])

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_random_quote(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(available=True, result="不存在的关键词"),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
            )

        # 验证 finish 包含 "没有找到" 提示
        finish_calls = matcher_random_quote.finish.call_args_list
        assert any("没有找到" in str(c) for c in finish_calls)

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
        mock_read_svc.increment_show_time = AsyncMock(return_value=None)

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.get_display_name = AsyncMock(return_value="作者")
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
        })

        # Act — 成功路径使用 send() 而非 finish()
        await handle_random_quote(
            event=mock_group_event,
            bot=mock_bot,
            at_user=_make_match(),
            text=_make_match(available=True, result="关键词"),
            quote_read_svc=mock_read_svc,
            quote_write_svc=mock_write_svc,
            user_svc=mock_user_svc,
            image_store=mock_image_store,
        )

        # 验证 search_quotes 被调用（关键词搜索路径）
        mock_read_svc.search_quotes.assert_awaited_once_with(
            "关键词", "123456",
        )

    async def test_service_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """服务异常：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(
            side_effect=RuntimeError("database error")
        )

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_random_quote(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_random_quote.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
