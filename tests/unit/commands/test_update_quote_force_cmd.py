"""
update_quote_force_cmd 命令处理器单元测试。

覆盖：
- handle_update_quote_force：强制更新语录
  - 成功 / 已有任务进行中 / 收集闭环异常 / 无新语录
  - 命令层仅依赖 collect_and_finalize，不再手工编排评论与清队列
  - 显式透传重复策略配置
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
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


def _make_config(enable_duplicate: bool) -> MagicMock:
    cfg = MagicMock()
    cfg.collecting.enable_duplicate = enable_duplicate
    return cfg


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

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_parsed_config = AsyncMock(return_value=_make_config(False))

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
        })

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_config_svc.get_parsed_config.assert_awaited_once_with("123456")
        mock_collection_svc.collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=False,
        )
        mock_collection_svc.collect_and_save.assert_not_awaited()
        mock_collection_svc.clear_queue.assert_not_awaited()
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("3" in str(c) for c in finish_calls)

    async def test_lock_conflict_handled_gracefully(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """强制更新时锁冲突由 _run_with_lock 抛出，被 command_error_handler 处理。"""
        from nonebot_plugin_zikequote3.services.quote_collection_service import CollectionLockError

        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_finalize = AsyncMock(
            side_effect=CollectionLockError("群 123 正在收集中")
        )

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_parsed_config = AsyncMock(return_value=_make_config(False))

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
        })

        # command_error_handler 捕获 CollectionLockError 并调用 finish
        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_awaited_once()

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

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_parsed_config = AsyncMock(return_value=_make_config(False))

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
        })

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

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_parsed_config = AsyncMock(return_value=_make_config(False))

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
        })

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=False,
        )
        mock_collection_svc.collect_and_save.assert_not_awaited()
        mock_collection_svc.clear_queue.assert_not_awaited()
        finish_calls = matcher_update_quote_force.finish.call_args_list
        assert any("0" in str(c) for c in finish_calls)

    async def test_collect_passes_duplicate_enabled_from_config(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
        mock_collection_svc.is_collecting = MagicMock(return_value=False)
        mock_collection_svc.collect_and_finalize = AsyncMock(return_value=[])

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_parsed_config = AsyncMock(return_value=_make_config(True))

        patch_container({
            QuoteCollectionService: mock_collection_svc,
            ConfigService: mock_config_svc,
        })

        with pytest.raises(FinishedException):
            await handle_update_quote_force(
                event=mock_group_event,
                state={},
            )

        mock_collection_svc.collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=True,
        )
