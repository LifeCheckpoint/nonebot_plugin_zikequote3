"""
remove_quote_cmd 命令处理器单元测试。

覆盖：
- handle_remove_quote：删除自己的语录 / 删除他人的语录
- 未提供语录 ID
- 语录不存在
- 命令层已放行但服务层归属校验仍拒绝删除
- 命令层权限不足时直接拦截
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import (
    PermissionDeniedError,
    QuoteNotFoundError,
)
from nonebot_plugin_zikequote3.msgtexts import general, quote_write
from nonebot_plugin_zikequote3.services.quote_write_service import (
    QuoteWriteService,
)

# 运行时从 stub 模块获取 mock matcher / 权限节点
_stub_cmd_def = sys.modules["nonebot_plugin_zikequote3.command.command_definition"]
matcher_remove_quote: MagicMock = getattr(_stub_cmd_def, "matcher_remove_quote")
perm_nodes = getattr(_stub_cmd_def, "perm_nodes")

# handler 函数：由 conftest stub 保证 @matcher.handle() 透传，
# 因此 handle_remove_quote 仍是原始 async 函数
from nonebot_plugin_zikequote3.command.cmds.remove_quote_cmd import (  # noqa: E402
    handle_remove_quote,
)


class TestRemoveQuoteByArg:
    """通过命令参数指定语录 ID 删除语录。"""

    async def test_delete_self_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """删除自己的语录时应命中 self 权限路径。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_by_id = AsyncMock(
            return_value=MagicMock(author_id="654321")
        )
        mock_write_svc.delete_quote = AsyncMock(return_value=None)
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-12345"

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        perm_nodes.n_quote_delete_self.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        perm_nodes.n_quote_delete_others.check.assert_not_awaited()
        mock_write_svc.delete_quote.assert_awaited_once_with(
            "Q-12345",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote.finish.call_args.args[0] == quote_write.remove_quote_success()

    async def test_delete_others_success_uses_others_permission(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """删除他人语录时应命中 others 权限路径。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_by_id = AsyncMock(
            return_value=MagicMock(author_id="10001")
        )
        mock_write_svc.delete_quote = AsyncMock(return_value=None)
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-others"

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        perm_nodes.n_quote_delete_self.check.assert_not_awaited()
        perm_nodes.n_quote_delete_others.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        mock_write_svc.delete_quote.assert_awaited_once_with(
            "Q-others",
            operator_id="654321",
            allow_delete_others=True,
        )
        assert matcher_remove_quote.finish.call_args.args[0] == quote_write.remove_quote_success()

    async def test_no_quote_id_provided(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """未提供语录 ID（无回复、无参数）：提示用户。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = ""
        mock_group_event.reply = None

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        mock_write_svc.delete_quote.assert_not_awaited()
        assert matcher_remove_quote.finish.call_args.args[0] == quote_write.remove_quote_target_required()


class TestRemoveQuoteErrorHandling:
    """删除语录的错误处理路径。"""

    async def test_quote_not_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """语录不存在时应保持未找到提示。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_by_id = AsyncMock(return_value=None)
        mock_write_svc.delete_quote = AsyncMock(
            side_effect=QuoteNotFoundError("语录 Q-99999 不存在")
        )
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-99999"

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        perm_nodes.n_quote_delete_self.check.assert_not_awaited()
        perm_nodes.n_quote_delete_others.check.assert_not_awaited()
        mock_write_svc.delete_quote.assert_awaited_once_with(
            "Q-99999",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote.finish.call_args.args[0] == general.resource_not_found_error("语录 Q-99999 不存在")

    async def test_command_layer_blocks_without_others_permission(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """删除他人语录但 others 权限不足时，命令层直接拒绝。"""
        perm_nodes.n_quote_delete_others.check.return_value = False

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_by_id = AsyncMock(
            return_value=MagicMock(author_id="10001")
        )
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-no-perm"

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        mock_write_svc.delete_quote.assert_not_awaited()
        assert matcher_remove_quote.finish.call_args.args[0] == general.permission_denied_error(
            "缺少删除他人语录权限（quote_id=Q-no-perm）"
        )

    async def test_service_layer_still_blocks_after_command_allows(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """命令层按 self 路径放行后，服务层归属失配仍应拒绝删除。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.get_quote_by_id = AsyncMock(
            return_value=MagicMock(author_id="654321")
        )
        mock_write_svc.delete_quote = AsyncMock(
            side_effect=PermissionDeniedError("仅可删除自己的语录（quote_id=Q-race）")
        )
        patch_container({QuoteWriteService: mock_write_svc})

        mock_message.extract_plain_text.return_value = "Q-race"

        with pytest.raises(FinishedException):
            await handle_remove_quote(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        perm_nodes.n_quote_delete_self.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        mock_write_svc.delete_quote.assert_awaited_once_with(
            "Q-race",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote.finish.call_args.args[0] == general.permission_denied_error(
            "仅可删除自己的语录（quote_id=Q-race）"
        )
