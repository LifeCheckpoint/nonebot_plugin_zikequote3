"""
update_quote_force_cmd 命令处理器单元测试。

覆盖：
- handle_update_quote_force：强制更新语录（成功 / 已有任务进行中 / 收集异常）
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectedQuote,
    QuoteCollectionService,
)
from nonebot_plugin_zikequote3.services.review_service import ReviewService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_update_quote_force: MagicMock = getattr(
    _stub_cmd_def, "matcher_update_quote_force"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.update_quote_force_cmd import (  # noqa: E402
    handle_update_quote_force,
)


class TestHandleUpdateQuoteForce:
    """强制更新语录命令。"""

    async def test_collect_success_with_comments(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """收集成功且有 AI 评论：返回新增数量。"""
        # Arrange
        collected = [
            CollectedQuote(quote_id="Q-1", comment="好语录"),
            CollectedQuote(quote_id="Q-2", comment=None),
            CollectedQuote(quote_id="Q-3", comment="精彩"),
        ]
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_save = AsyncMock(return_value=collected)
        mock_collection_svc.clear_queue = AsyncMock(return_value=None)

        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.add_review = AsyncMock(return_value=None)

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ReviewService: mock_review_svc,
        })

        mock_state = {}

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state=mock_state,
                collection_svc=mock_collection_svc,
                review_svc=mock_review_svc,
            )

        # 验证服务调用
        mock_collection_svc.collect_and_save.assert_awaited_once_with("123456")
        mock_collection_svc.clear_queue.assert_awaited_once_with("123456")
        # 只有 comment 非 None 的才调用 add_review（Q-1 和 Q-3）
        assert mock_review_svc.add_review.await_count == 2
        # 验证 finish 包含数量
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("3" in str(c) for c in finish_calls)

    async def test_already_collecting(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """已有收集任务进行中：提示稍后再试。"""
        # Arrange
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=True)

        mock_review_svc = AsyncMock(spec=ReviewService)

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ReviewService: mock_review_svc,
        })

        mock_state = {}

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state=mock_state,
                collection_svc=mock_collection_svc,
                review_svc=mock_review_svc,
            )

        # 验证 collect_and_save 未被调用
        mock_collection_svc.collect_and_save.assert_not_awaited()
        # 验证 finish 包含 "已有" 提示
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("已有" in str(c) for c in finish_calls)

    async def test_collect_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """收集过程异常：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_save = AsyncMock(
            side_effect=RuntimeError("LLM service unavailable")
        )

        mock_review_svc = AsyncMock(spec=ReviewService)

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ReviewService: mock_review_svc,
        })

        mock_state = {}

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state=mock_state,
                collection_svc=mock_collection_svc,
                review_svc=mock_review_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)

    async def test_collect_success_no_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """收集成功但无新语录：返回 0 条。"""
        # Arrange
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_save = AsyncMock(return_value=[])
        mock_collection_svc.clear_queue = AsyncMock(return_value=None)

        mock_review_svc = AsyncMock(spec=ReviewService)

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ReviewService: mock_review_svc,
        })

        mock_state = {}

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state=mock_state,
                collection_svc=mock_collection_svc,
                review_svc=mock_review_svc,
            )

        # 验证 add_review 未被调用
        mock_review_svc.add_review.assert_not_awaited()
        # 验证 finish 包含 "0"
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("0" in str(c) for c in finish_calls)
