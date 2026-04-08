"""
update_quote_force_cmd 命令处理器单元测试。

覆盖：
- handle_update_quote_force：强制更新语录
  - 成功 / 已有任务进行中 / 收集闭环异常 / 无新语录
  - 命令层仅依赖 collect_and_finalize，不再手工编排评论与清队列
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectedQuote,
    QuoteCollectionService,
)

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
        collected = [
            CollectedQuote(quote_id="Q-1", comment="好语录"),
            CollectedQuote(quote_id="Q-2", comment=None),
            CollectedQuote(quote_id="Q-3", comment="精彩"),
        ]
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_finalize = AsyncMock(return_value=collected)
        mock_collection_svc.collect_and_save = AsyncMock(return_value=collected)
        mock_collection_svc.clear_queue = AsyncMock(return_value=None)

        patch_container({QuoteCollectionService: mock_collection_svc})

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_awaited_once_with("123456")
        mock_collection_svc.collect_and_save.assert_not_awaited()
        mock_collection_svc.clear_queue.assert_not_awaited()
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("3" in str(c) for c in finish_calls)

    async def test_already_collecting(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=True)

        patch_container({QuoteCollectionService: mock_collection_svc})

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_not_awaited()
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("已有" in str(c) for c in finish_calls)

    async def test_collect_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_finalize = AsyncMock(
            side_effect=RuntimeError("LLM service unavailable")
        )

        patch_container({QuoteCollectionService: mock_collection_svc})

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)

    async def test_collect_success_no_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_finalize = AsyncMock(return_value=[])
        mock_collection_svc.collect_and_save = AsyncMock(return_value=[])
        mock_collection_svc.clear_queue = AsyncMock(return_value=None)

        patch_container({QuoteCollectionService: mock_collection_svc})

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_awaited_once_with("123456")
        mock_collection_svc.collect_and_save.assert_not_awaited()
        mock_collection_svc.clear_queue.assert_not_awaited()
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("0" in str(c) for c in finish_calls)
