"""
remove_quote_comment_cmd 命令处理器单元测试。

覆盖：
- handle_remove_quote_comment：删除评论（成功 / 参数缺失 / 评论不存在 / 其他异常）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import ResourceNotFoundError
from nonebot_plugin_zikequote3.services.review_service import ReviewService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_remove_quote_comment: MagicMock = getattr(
    _stub_cmd_def, "matcher_remove_quote_comment"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.remove_quote_comment_cmd import (  # noqa: E402
    handle_remove_quote_comment,
)


class TestHandleRemoveQuoteComment:
    """删除评论命令。"""

    async def test_delete_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """提供有效评论 ID：删除成功。"""
        # Arrange
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.delete_review = AsyncMock(return_value=None)
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-42"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        # 验证服务调用
        mock_review_svc.delete_review.assert_awaited_once_with("R-42")
        # 验证成功消息
        finish_calls = matcher_remove_quote_comment.finish.call_args_list
        assert any("删除成功" in str(c) for c in finish_calls)

    async def test_no_review_id_provided(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """未提供评论 ID：提示用法。"""
        # Arrange
        mock_review_svc = AsyncMock(spec=ReviewService)
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        # 验证 delete_review 未被调用
        mock_review_svc.delete_review.assert_not_awaited()
        # 验证 finish 包含用法提示
        finish_calls = matcher_remove_quote_comment.finish.call_args_list
        assert any("评论 ID" in str(c) for c in finish_calls)

    async def test_review_not_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """评论不存在：command_error_handler 捕获 ResourceNotFoundError。"""
        # Arrange
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.delete_review = AsyncMock(
            side_effect=ResourceNotFoundError("评论 R-999 不存在")
        )
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-999"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        # 验证 delete_review 被调用
        mock_review_svc.delete_review.assert_awaited_once_with("R-999")
        # 验证 finish 包含 "未找到" 错误消息
        finish_calls = matcher_remove_quote_comment.finish.call_args_list
        assert any("未找到" in str(c) for c in finish_calls)

    async def test_unexpected_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """服务抛出非业务异常：command_error_handler 捕获并发送通用错误。"""
        # Arrange
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.delete_review = AsyncMock(
            side_effect=RuntimeError("database connection lost")
        )
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-100"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_remove_quote_comment.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)
