"""
remove_quote_comment_cmd 命令处理器单元测试。

覆盖：
- handle_remove_quote_comment：删除自己的评论 / 删除他人的评论
- 未提供评论 ID
- 评论不存在
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
    ResourceNotFoundError,
)
from nonebot_plugin_zikequote3.msgtexts import general, quote_write
from nonebot_plugin_zikequote3.services.review_service import ReviewService

# 运行时从 stub 模块获取 mock matcher / 权限节点
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_remove_quote_comment: MagicMock = getattr(
    _stub_cmd_def, "matcher_remove_quote_comment"
)
perm_nodes = getattr(_stub_cmd_def, "perm_nodes")

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.remove_quote_comment_cmd import (  # noqa: E402
    handle_remove_quote_comment,
)


class TestHandleRemoveQuoteComment:
    """删除评论命令。"""

    async def test_delete_self_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """删除自己的评论时应命中 self 权限路径。"""
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.get_review_by_id = AsyncMock(
            return_value=MagicMock(author_id="654321")
        )
        mock_review_svc.delete_review = AsyncMock(return_value=None)
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-self"

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        perm_nodes.n_review_delete_self.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        perm_nodes.n_review_delete_others.check.assert_not_awaited()
        mock_review_svc.delete_review.assert_awaited_once_with(
            "R-self",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote_comment.finish.call_args.args[0] == quote_write.remove_quote_comment_success()

    async def test_delete_others_success_uses_others_permission(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """删除他人评论时应命中 others 权限路径。"""
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.get_review_by_id = AsyncMock(
            return_value=MagicMock(author_id="10001")
        )
        mock_review_svc.delete_review = AsyncMock(return_value=None)
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-others"

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        perm_nodes.n_review_delete_self.check.assert_not_awaited()
        perm_nodes.n_review_delete_others.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        mock_review_svc.delete_review.assert_awaited_once_with(
            "R-others",
            operator_id="654321",
            allow_delete_others=True,
        )
        assert matcher_remove_quote_comment.finish.call_args.args[0] == quote_write.remove_quote_comment_success()

    async def test_no_review_id_provided(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """未提供评论 ID：提示用法。"""
        mock_review_svc = AsyncMock(spec=ReviewService)
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = ""

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        mock_review_svc.delete_review.assert_not_awaited()
        assert matcher_remove_quote_comment.finish.call_args.args[0] == quote_write.remove_quote_comment_required()

    async def test_review_not_found(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """评论不存在时应保持未找到提示。"""
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.get_review_by_id = AsyncMock(return_value=None)
        mock_review_svc.delete_review = AsyncMock(
            side_effect=ResourceNotFoundError("评论 R-999 不存在")
        )
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-999"

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        perm_nodes.n_review_delete_self.check.assert_not_awaited()
        perm_nodes.n_review_delete_others.check.assert_not_awaited()
        mock_review_svc.delete_review.assert_awaited_once_with(
            "R-999",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote_comment.finish.call_args.args[0] == general.resource_not_found_error("评论 R-999 不存在")

    async def test_command_layer_blocks_without_others_permission(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """删除他人评论但 others 权限不足时，命令层直接拒绝。"""
        perm_nodes.n_review_delete_others.check.return_value = False

        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.get_review_by_id = AsyncMock(
            return_value=MagicMock(author_id="10001")
        )
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-no-perm"

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        mock_review_svc.delete_review.assert_not_awaited()
        assert matcher_remove_quote_comment.finish.call_args.args[0] == general.permission_denied_error(
            "缺少删除他人评论权限（review_id=R-no-perm）"
        )

    async def test_service_layer_still_blocks_after_command_allows(
        self,
        patch_container,
        mock_group_event: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """命令层按 self 路径放行后，服务层归属失配仍应拒绝删除。"""
        mock_review_svc = AsyncMock(spec=ReviewService)
        mock_review_svc.get_review_by_id = AsyncMock(
            return_value=MagicMock(author_id="654321")
        )
        mock_review_svc.delete_review = AsyncMock(
            side_effect=PermissionDeniedError("仅可删除自己的评论（review_id=R-race）")
        )
        patch_container({ReviewService: mock_review_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "R-race"

        with pytest.raises(FinishedException):
            await handle_remove_quote_comment(
                event=mock_group_event,
                bot=mock_bot,
                arg=mock_arg,
                review_svc=mock_review_svc,
            )

        perm_nodes.n_review_delete_self.check.assert_awaited_once_with(
            mock_bot,
            mock_group_event,
            throw_on_fail=False,
        )
        mock_review_svc.delete_review.assert_awaited_once_with(
            "R-race",
            operator_id="654321",
            allow_delete_others=False,
        )
        assert matcher_remove_quote_comment.finish.call_args.args[0] == general.permission_denied_error(
            "仅可删除自己的评论（review_id=R-race）"
        )
