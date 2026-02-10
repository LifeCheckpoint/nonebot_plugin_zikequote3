"""
add_quote_cmd 命令处理器单元测试。

覆盖：
- handle_add_quote：添加语录（成功-纯文本 / 成功-含图片 / 无回复 / 回复自己 / 空内容 / 服务异常）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_add_quote: MagicMock = getattr(_stub_cmd_def, "matcher_add_quote")

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.add_quote_cmd import (  # noqa: E402
    handle_add_quote,
)


def _make_text_reply(text: str, *, sender_id: int | str = 111111) -> MagicMock:
    """创建纯文本回复消息 mock。"""
    reply = MagicMock()
    reply.message_id = 55555
    reply.sender = MagicMock()
    reply.sender.user_id = sender_id
    reply.message = MagicMock()
    reply.message.extract_plain_text.return_value = text
    reply.message.count.return_value = 0  # 无图片
    reply.message.only.return_value = False
    return reply


class TestHandleAddQuote:
    """添加语录命令。"""

    async def test_add_text_quote_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复纯文本消息：添加语录成功。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.add_quote = AsyncMock(return_value="Q-NEW-1")
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.ensure_member = AsyncMock(return_value=None)
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"
        reply = _make_text_reply("这是一条经典语录")
        mock_group_event.reply = reply

        # Act — 成功路径使用 send() 而非 finish()，不抛出 FinishedException
        await handle_add_quote(
            event=mock_group_event,
            bot=mock_bot,
            quote_write_svc=mock_write_svc,
            group_svc=mock_group_svc,
            image_store=mock_image_store,
        )

        # 验证服务调用
        mock_write_svc.add_quote.assert_awaited_once_with(
            group_id="123456",
            author_id="111111",
            content="这是一条经典语录",
            image_content_uuid=None,
        )

    async def test_no_reply(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """未回复消息：提示用户。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_group_event.reply = None

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # 验证 add_quote 未被调用
        mock_write_svc.add_quote.assert_not_awaited()
        # 验证 finish 包含提示
        finish_calls = matcher_add_quote.finish.call_args_list
        assert any("回复" in str(c) for c in finish_calls)

    async def test_reply_to_bot_self(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复机器人自己的消息：拒绝添加。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"
        reply = _make_text_reply("机器人的消息", sender_id="999999")
        mock_group_event.reply = reply

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # 验证 add_quote 未被调用
        mock_write_svc.add_quote.assert_not_awaited()

    async def test_empty_content(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复消息内容为空（无文本无图片）：提示用户。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"
        reply = _make_text_reply("")  # 空文本
        mock_group_event.reply = reply

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # 验证 add_quote 未被调用
        mock_write_svc.add_quote.assert_not_awaited()
        # 验证 finish 包含 "空" 提示
        finish_calls = matcher_add_quote.finish.call_args_list
        assert any("空" in str(c) for c in finish_calls)

    async def test_add_quote_service_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """add_quote 服务异常：command_error_handler 捕获。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.add_quote = AsyncMock(
            side_effect=RuntimeError("database error")
        )
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_image_store = MagicMock(spec=ImageStore)

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"
        reply = _make_text_reply("一条语录")
        mock_group_event.reply = reply

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_add_quote.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
