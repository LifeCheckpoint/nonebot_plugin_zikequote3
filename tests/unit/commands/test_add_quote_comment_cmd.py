"""
add_quote_comment_cmd 命令处理器单元测试。

覆盖：
- handle_add_quote_comment：添加评论（成功 / 无回复或内容 / 语录不存在 / 服务异常）
- handle_add_quote_comment_no_prefix：静默评论（成功 / 无回复 / 语录不存在静默返回）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.review_service import ReviewService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_add_quote_comment: MagicMock = getattr(
    _stub_cmd_def, "matcher_add_quote_comment"
)
matcher_add_quote_comment_no_prefix: MagicMock = getattr(
    _stub_cmd_def, "matcher_add_quote_comment_no_prefix"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.add_quote_comment_cmd import (  # noqa: E402
    handle_add_quote_comment,
    handle_add_quote_comment_no_prefix,
)


# ===================================================================
# handle_add_quote_comment 测试
# ===================================================================


class TestHandleAddQuoteComment:
    """添加评论命令（带前缀）。"""

    async def test_add_comment_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复语录并输入评论内容：添加成功。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_id_by_msg_id = AsyncMock(return_value="Q-100")
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.add_review = AsyncMock(return_value=None)
        mock_group_svc = AsyncMock(spec=GroupService)
        mock_group_svc.ensure_member = AsyncMock(return_value=None)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            GroupService: mock_group_svc,
        })

        # 模拟回复消息
        mock_reply = MagicMock()
        mock_reply.message_id = 88888
        mock_group_event.reply = mock_reply
        mock_group_event.sender.user_id = 654321

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "这条语录太棒了"

        # Act — 成功路径使用 send() 而非 finish()，不抛出 FinishedException
        await handle_add_quote_comment(
            event=mock_group_event,
            bot=mock_bot,
            arg=mock_arg,
            quote_write_svc=mock_write_svc,
            review_svc=mock_review_svc,
            group_svc=mock_group_svc,
        )

        # 验证服务调用
        mock_write_svc.get_quote_id_by_msg_id.assert_awaited_once_with("88888")
        mock_review_svc.add_review.assert_awaited_once_with(
            quote_id="Q-100",
            author_id="654321",
            content="这条语录太棒了",
        )

    async def test_no_reply_or_empty_content(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """未回复消息：提示用法。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_group_svc = AsyncMock(spec=GroupService)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            GroupService: mock_group_svc,
        })

        mock_group_event.reply = None
        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "评论内容"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                quote_write_svc=mock_write_svc,
                review_svc=mock_review_svc,
                group_svc=mock_group_svc,
            )

        # 验证 get_quote_id_by_msg_id 未被调用
        mock_write_svc.get_quote_id_by_msg_id.assert_not_awaited()
        # 验证 finish 包含提示
        finish_calls = matcher_add_quote_comment.finish.call_args_list
        assert any("回复" in str(c) for c in finish_calls)

    async def test_empty_content(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """有回复但评论内容为空：提示用法。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_group_svc = AsyncMock(spec=GroupService)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            GroupService: mock_group_svc,
        })

        mock_reply = MagicMock()
        mock_reply.message_id = 88888
        mock_group_event.reply = mock_reply

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                quote_write_svc=mock_write_svc,
                review_svc=mock_review_svc,
                group_svc=mock_group_svc,
            )

        # 验证 get_quote_id_by_msg_id 未被调用
        mock_write_svc.get_quote_id_by_msg_id.assert_not_awaited()

    async def test_quote_not_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复的消息不是语录：quote_id 为 None，走资源未找到分支。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_id_by_msg_id = AsyncMock(return_value=None)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_group_svc = AsyncMock(spec=GroupService)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            GroupService: mock_group_svc,
        })

        mock_reply = MagicMock()
        mock_reply.message_id = 99999
        mock_group_event.reply = mock_reply
        mock_group_event.sender.user_id = 654321

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "评论内容"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_add_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                quote_write_svc=mock_write_svc,
                review_svc=mock_review_svc,
                group_svc=mock_group_svc,
            )

        # 验证 add_review 未被调用
        mock_review_svc.add_review.assert_not_awaited()
        # 验证 finish 进入资源未找到分支，而不是通用内部错误分支
        finish_calls = matcher_add_quote_comment.finish.call_args_list
        assert any("未找到" in str(c) for c in finish_calls)
        assert all("发生错误" not in str(c) for c in finish_calls)


# ===================================================================
# handle_add_quote_comment_no_prefix 测试
# ===================================================================


class TestHandleAddQuoteCommentNoPrefix:
    """静默评论语录（无前缀）。"""

    async def test_silent_comment_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复语录并有文本内容：静默添加评论。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_id_by_msg_id = AsyncMock(return_value="Q-200")
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.add_review = AsyncMock(return_value=None)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.comment.enable_comment_without_prefix = True
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            ConfigService: mock_config_svc,
        })

        mock_reply = MagicMock()
        mock_reply.message_id = 77777
        mock_group_event.reply = mock_reply
        mock_group_event.get_plaintext = MagicMock(return_value="静默评论内容")
        mock_group_event.sender.user_id = 654321

        # Act — 不应抛出异常（静默模式）
        await handle_add_quote_comment_no_prefix(
            event=mock_group_event,
            bot=mock_bot,
        )

        # 验证服务调用
        mock_write_svc.get_quote_id_by_msg_id.assert_awaited_once_with("77777")
        mock_review_svc.add_review.assert_awaited_once_with(
            quote_id="Q-200",
            author_id="654321",
            content="静默评论内容",
        )

    async def test_no_reply_silent_return(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """无回复消息：静默返回，不处理。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_config_svc = AsyncMock(spec=ConfigService)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            ConfigService: mock_config_svc,
        })

        mock_group_event.reply = None
        mock_group_event.get_plaintext = MagicMock(return_value="一些文本")

        # Act — 静默返回
        await handle_add_quote_comment_no_prefix(
            event=mock_group_event,
            bot=mock_bot,
        )

        # 验证 get_quote_id_by_msg_id 未被调用
        mock_write_svc.get_quote_id_by_msg_id.assert_not_awaited()

    async def test_quote_not_found_silent_return(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """回复的消息不是语录：quote_id 为 None，静默返回。"""
        # Arrange
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_id_by_msg_id = AsyncMock(return_value=None)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.comment.enable_comment_without_prefix = True
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            ConfigService: mock_config_svc,
        })

        mock_reply = MagicMock()
        mock_reply.message_id = 66666
        mock_group_event.reply = mock_reply
        mock_group_event.get_plaintext = MagicMock(return_value="评论内容")

        # Act — 静默返回
        await handle_add_quote_comment_no_prefix(
            event=mock_group_event,
            bot=mock_bot,
        )

    async def test_no_prefix_disabled_returns_early(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """运行时关闭无前缀评论时，matcher 常驻但 handler 应提前返回。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.comment.enable_comment_without_prefix = False
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        patch_container({
            QuoteWriteService: mock_write_svc,
            ReviewService: mock_review_svc,
            ConfigService: mock_config_svc,
        })

        mock_reply = MagicMock()
        mock_reply.message_id = 55555
        mock_group_event.reply = mock_reply
        mock_group_event.get_plaintext = MagicMock(return_value="评论内容")

        await handle_add_quote_comment_no_prefix(
            event=mock_group_event,
            bot=mock_bot,
        )

        mock_config_svc.get_parsed_config.assert_awaited_once_with("123456")
        mock_write_svc.get_quote_id_by_msg_id.assert_not_awaited()

        # 验证 add_review 未被调用
        mock_review_svc.add_review.assert_not_awaited()
