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
from nonebot_plugin_zikequote3.msgtexts import general, quote_write
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
        matcher_add_quote.send.assert_awaited_once_with(quote_write.add_quote_success())

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
        assert matcher_add_quote.finish.call_args.args[0] == quote_write.add_quote_reply_required()

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
        assert matcher_add_quote.finish.call_args.args[0] == quote_write.add_quote_reply_to_self()

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
        assert matcher_add_quote.finish.call_args.args[0] == quote_write.add_quote_empty_content()

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

        assert matcher_add_quote.finish.call_args.args[0] == general.unexpected_error("database error")

    async def test_add_image_quote_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复含图片消息：使用 add_quote_with_image_data 添加语录成功。"""
        from pathlib import Path

        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.add_quote_with_image_data = AsyncMock(return_value="Q-IMG-1")
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.ensure_member = AsyncMock(return_value=None)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_image_store.upload.return_value = "abc123uuid"
        mock_image_store.get_path.return_value = Path("/fake/ab/c1/abc123uuid.png")
        mock_image_store.get_sha256.return_value = "deadbeef" * 8

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"

        # 构造含图片的回复
        reply = MagicMock()
        reply.message_id = 66666
        reply.sender = MagicMock()
        reply.sender.user_id = 111111
        reply.message = MagicMock()
        reply.message.extract_plain_text.return_value = "图片语录文本"
        reply.message.count.return_value = 1  # 有 1 张图片
        reply.message.only.return_value = False
        img_seg = MagicMock()
        img_seg.data = {"url": "https://example.com/img.png"}
        reply.message.get.return_value = [img_seg]
        mock_group_event.reply = reply

        # mock _fetch_image_from_url_or_file
        with patch(
            "nonebot_plugin_zikequote3.command.cmds.add_quote_cmd._fetch_image_from_url_or_file",
            new_callable=AsyncMock,
            return_value=b"\x89PNG fake image data",
        ):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # 验证使用了 add_quote_with_image_data 而非 add_quote
        mock_write_svc.add_quote_with_image_data.assert_awaited_once_with(
            group_id="123456",
            author_id="111111",
            content="图片语录文本",
            image_uuid="abc123uuid",
            original_filename="https://example.com/img.png",
            stored_filename="abc123uuid.png",
            file_path=str(Path("/fake/ab/c1/abc123uuid.png")),
            checksum_sha256="deadbeef" * 8,
        )
        mock_write_svc.add_quote.assert_not_awaited()
        matcher_add_quote.send.assert_awaited_once_with(quote_write.add_quote_success())

    async def test_add_image_only_quote_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复纯图片消息（无文本）：content 为 None。"""
        from pathlib import Path

        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.add_quote_with_image_data = AsyncMock(return_value="Q-IMG-2")
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.ensure_member = AsyncMock(return_value=None)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_image_store.upload.return_value = "def456uuid"
        mock_image_store.get_path.return_value = Path("/fake/de/f4/def456uuid.jpg")
        mock_image_store.get_sha256.return_value = "cafebabe" * 8

        patch_container({
            QuoteWriteService: mock_write_svc,
            GroupService: mock_group_svc,
            ImageStore: mock_image_store,
        })

        mock_bot.self_id = "999999"

        # 构造纯图片回复（无文本）
        reply = MagicMock()
        reply.message_id = 77777
        reply.sender = MagicMock()
        reply.sender.user_id = 222222
        reply.message = MagicMock()
        reply.message.extract_plain_text.return_value = ""
        reply.message.count.return_value = 1  # 有 1 张图片
        reply.message.only.return_value = True  # 仅图片
        img_seg = MagicMock()
        img_seg.data = {"file": "local_img.jpg"}
        reply.message.get.return_value = [img_seg]
        mock_group_event.reply = reply

        with patch(
            "nonebot_plugin_zikequote3.command.cmds.add_quote_cmd._fetch_image_from_url_or_file",
            new_callable=AsyncMock,
            return_value=b"\xff\xd8\xff fake jpg",
        ):
            await handle_add_quote(
                event=mock_group_event,
                bot=mock_bot,
                quote_write_svc=mock_write_svc,
                group_svc=mock_group_svc,
                image_store=mock_image_store,
            )

        # content 应为 None（纯图片）
        mock_write_svc.add_quote_with_image_data.assert_awaited_once_with(
            group_id="123456",
            author_id="222222",
            content=None,
            image_uuid="def456uuid",
            original_filename="local_img.jpg",
            stored_filename="def456uuid.jpg",
            file_path=str(Path("/fake/de/f4/def456uuid.jpg")),
            checksum_sha256="cafebabe" * 8,
        )
        matcher_add_quote.send.assert_awaited_once_with(quote_write.add_quote_success())
