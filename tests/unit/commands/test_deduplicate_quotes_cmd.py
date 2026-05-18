"""`/语录去重` 命令处理器单元测试。"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.msgtexts import general
from nonebot_plugin_zikequote3.services.quote_write_service import (
    QuoteDeduplicateResult,
    QuoteWriteService,
)

_stub_cmd_def = sys.modules["nonebot_plugin_zikequote3.command.command_definition"]
matcher_quote_deduplicate: MagicMock = getattr(
    _stub_cmd_def,
    "matcher_quote_deduplicate",
)
perm_nodes = getattr(_stub_cmd_def, "perm_nodes")

from nonebot_plugin_zikequote3.command.cmds.deduplicate_quotes_cmd import (  # noqa: E402
    handle_quote_deduplicate,
)


class TestQuoteDeduplicateCommand:
    """测试 `/语录去重` 命令。"""

    async def test_deduplicate_group_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """默认模式应走全群去重权限路径。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.deduplicate_group_quotes = AsyncMock(
            return_value=QuoteDeduplicateResult(
                backup_path="D:/data/backups/zikequote3_dedup_001.db",
                scanned_count=7,
                duplicate_groups=2,
                deleted_count=3,
                kept_count=2,
                user_only=False,
            )
        )
        patch_container({QuoteWriteService: mock_write_svc})
        mock_message.extract_plain_text.return_value = ""

        with pytest.raises(FinishedException):
            await handle_quote_deduplicate(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        perm_nodes.n_quote_delete_others.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        perm_nodes.n_quote_delete_self.check.assert_not_awaited()
        mock_write_svc.deduplicate_group_quotes.assert_awaited_once_with(
            "123456",
            operator_id="654321",
            user_only=False,
        )
        assert matcher_quote_deduplicate.finish.call_args.args[0] == (
            "语录去重完成啦~\n"
            "这次检查的是当前群全部成员的语录哦\n"
            "我先帮你备份好数据库啦，一共检查了 7 条语录，发现 2 组重复内容\n"
        )

    async def test_deduplicate_user_only_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """`--user_only` 模式应走 self 权限路径。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        mock_write_svc.deduplicate_group_quotes = AsyncMock(
            return_value=QuoteDeduplicateResult(
                backup_path="D:/data/backups/zikequote3_dedup_002.db",
                scanned_count=3,
                duplicate_groups=1,
                deleted_count=1,
                kept_count=1,
                user_only=True,
            )
        )
        patch_container({QuoteWriteService: mock_write_svc})
        mock_message.extract_plain_text.return_value = "--user_only"

        with pytest.raises(FinishedException):
            await handle_quote_deduplicate(
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
        mock_write_svc.deduplicate_group_quotes.assert_awaited_once_with(
            "123456",
            operator_id="654321",
            user_only=True,
        )

    async def test_invalid_argument_returns_validation_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """不支持的参数应返回校验错误。"""
        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        patch_container({QuoteWriteService: mock_write_svc})
        mock_message.extract_plain_text.return_value = "--bad"

        with pytest.raises(FinishedException):
            await handle_quote_deduplicate(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        mock_write_svc.deduplicate_group_quotes.assert_not_awaited()
        assert matcher_quote_deduplicate.finish.call_args.args[0] == general.validation_error(
            "仅支持可选参数 --user_only"
        )

    async def test_user_only_without_permission_returns_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """`--user_only` 模式权限不足时应直接拒绝。"""
        perm_nodes.n_quote_delete_self.check.return_value = False

        mock_write_svc = AsyncMock(spec=QuoteWriteService)
        patch_container({QuoteWriteService: mock_write_svc})
        mock_message.extract_plain_text.return_value = "--user_only"

        with pytest.raises(FinishedException):
            await handle_quote_deduplicate(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_message,
            )

        mock_write_svc.deduplicate_group_quotes.assert_not_awaited()
        assert matcher_quote_deduplicate.finish.call_args.args[0] == general.permission_denied_error(
            "缺少去重自己语录权限"
        )
