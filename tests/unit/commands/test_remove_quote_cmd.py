"""
remove_quote_cmd 命令处理器单元测试 —— 概念验证。

验证命令层测试基础设施可用：
- patch_container fixture 正确注入 mock 服务
- stub matcher 的 finish() 正确抛出 FinishedException
- mock event / bot / message fixture 正常工作
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import QuoteNotFoundError
from nonebot_plugin_zikequote3.services.quote_write_service import (
    QuoteWriteService,
)

# 运行时从 stub 模块获取 mock matcher（Pylance 无法感知 stub 替换）
_stub_cmd_def = sys.modules["nonebot_plugin_zikequote3.command.command_definition"]
matcher_remove_quote: MagicMock = getattr(_stub_cmd_def, "matcher_remove_quote")

# handler 函数：由 conftest stub 保证 @matcher.handle() 透传，
# 因此 handle_remove_quote 仍是原始 async 函数
from nonebot_plugin_zikequote3.command.cmds.remove_quote_cmd import (  # noqa: E402
    handle_remove_quote,
)


class TestRemoveQuoteByArg:
    """通过命令参数指定语录 ID 删除语录。"""

    async def test_delete_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """正常删除语录：提供有效 quote_id，delete_quote 成功。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.delete_quote = AsyncMock(return_value=None)
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-12345"

        # Act & Assert — finish() 抛出 FinishedException
        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        # 验证 delete_quote 被正确调用
        mock_write_svc.delete_quote.assert_awaited_once_with("Q-12345")
        # 验证 finish 被调用且包含成功消息
        matcher_remove_quote.finish.assert_awaited()
        last_call_args = matcher_remove_quote.finish.call_args
        assert "删除成功" in str(last_call_args)

    async def test_no_quote_id_provided(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """未提供语录 ID（无回复、无参数）：提示用户。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = ""
        mock_group_event.reply = None

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        # 验证 delete_quote 未被调用
        mock_write_svc.delete_quote.assert_not_awaited()
        # 验证 finish 被调用且包含提示消息
        first_call_args = matcher_remove_quote.finish.call_args_list[0]
        assert "请回复一条语录消息或提供语录 ID" in str(first_call_args)


class TestRemoveQuoteErrorHandling:
    """删除语录的错误处理路径。"""

    async def test_quote_not_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """语录不存在：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.delete_quote = AsyncMock(
            side_effect=QuoteNotFoundError("语录 Q-99999 不存在")
        )
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-99999"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        # 验证 delete_quote 被调用
        mock_write_svc.delete_quote.assert_awaited_once_with("Q-99999")
        # 验证 finish 被调用且包含 "未找到" 错误消息
        # command_error_handler 对 ResourceNotFoundError 发送 "未找到：..."
        finish_calls = matcher_remove_quote.finish.call_args_list
        error_call = finish_calls[0]
        assert "未找到" in str(error_call)
