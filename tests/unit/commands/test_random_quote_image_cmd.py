"""
random_quote_image_cmd 命令处理器单元测试。

覆盖：
- handle_random_quote_image：随机语录图（成功 / 无语录 / 关键词过滤 / 服务异常）
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock

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
matcher_random_quote_image: MagicMock = getattr(
    _stub_cmd_def, "matcher_random_quote_image"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.random_quote_image_cmd import (  # noqa: E402
    handle_random_quote_image,
)


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Alconna Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_quote(
    *,
    quote_id: str = "Q-IMG-1",
    content: str | None = "图片语录",
    image_content_uuid: str | None = "uuid-abc-123",
    group_id: str = "123456",
) -> MagicMock:
    """创建模拟的语录对象。"""
    q = MagicMock()
    q.quote_id = quote_id
    q.content = content
    q.image_content_uuid = image_content_uuid
    q.group_id = group_id
    return q


class TestHandleRandomQuoteImage:
    """随机语录图命令。"""

    async def test_image_quote_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """获取含图片的语录：发送图片成功。"""
        # Arrange
        quotes = [
            _make_quote(quote_id="Q-1", image_content_uuid="uuid-1"),
            _make_quote(quote_id="Q-2", image_content_uuid=None),  # 无图片
            _make_quote(quote_id="Q-3", image_content_uuid="uuid-3"),
        ]
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=quotes)
        mock_read_svc.increment_show_time = AsyncMock(return_value=None)

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.create_msg_quote_mapping = AsyncMock(return_value=None)

        mock_user_svc = AsyncMock(spec=UserService)
        mock_user_svc.search_users_by_name = AsyncMock(return_value=[])

        mock_image_store = MagicMock(spec=ImageStore)
        mock_path = MagicMock(spec=Path)
        mock_path.read_bytes.return_value = b"\x89PNG_FAKE_IMAGE"
        mock_image_store.get_path = MagicMock(return_value=mock_path)

        patch_container({
            QuoteReadService: mock_read_svc,
            QuoteWriteService: mock_write_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
        })

        # Act — 成功路径使用 send() 而非 finish()，不抛出 FinishedException
        await handle_random_quote_image(
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
        # send 被调用（发送图片）
        matcher_random_quote_image.send.assert_awaited()

    async def test_no_image_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """所有语录均无图片：提示用户。"""
        # Arrange
        quotes = [
            _make_quote(quote_id="Q-1", image_content_uuid=None),
            _make_quote(quote_id="Q-2", image_content_uuid=None),
        ]
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=quotes)

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
            await handle_random_quote_image(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
            )

        # 验证 finish 包含 "没有找到" 提示
        finish_calls = matcher_random_quote_image.finish.call_args_list
        assert any("没有找到" in str(c) for c in finish_calls)

    async def test_empty_group_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """群组无任何语录：提示用户。"""
        # Arrange
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_read_svc.get_quotes_by_group = AsyncMock(return_value=[])

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
            await handle_random_quote_image(
                event=mock_group_event,
                bot=mock_bot,
                at_user=_make_match(),
                text=_make_match(),
                quote_read_svc=mock_read_svc,
                quote_write_svc=mock_write_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
            )

        # 验证 finish 包含 "没有找到" 提示
        finish_calls = matcher_random_quote_image.finish.call_args_list
        assert any("没有找到" in str(c) for c in finish_calls)

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
            await handle_random_quote_image(
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
        finish_calls = matcher_random_quote_image.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
