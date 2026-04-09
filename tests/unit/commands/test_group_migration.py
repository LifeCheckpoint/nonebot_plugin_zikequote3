"""
group_migration 命令处理器单元测试。

覆盖：
- handle_group_migration：群语录迁移
  - 参数缺失（source/target 不可用）
  - 源群不存在
  - 目标群不存在
  - 源群与目标群相同
  - 源群无语录
  - 用户超时取消且不写入
  - 用户输入格式错误取消且不写入
  - Token 验证失败且不写入
  - 迁移成功且显式分阶段解析依赖
  - 预览漂移后提示重新预览
  - 图片渲染失败降级为纯文本
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import OperationError
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.migration_service import MigrationService
from nonebot_plugin_zikequote3.utils.token_generate import TokenManager

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_group_migration: MagicMock = getattr(
    _stub_cmd_def, "matcher_group_migration"
)

# Stub nonebot_plugin_waiter —— group_migration.py 在函数体内延迟导入
if "nonebot_plugin_waiter" not in sys.modules:
    _stub_waiter = types.ModuleType("nonebot_plugin_waiter")
    _stub_waiter.prompt = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    sys.modules["nonebot_plugin_waiter"] = _stub_waiter

# patch 模板渲染函数，避免 jinja2 模板文件依赖
with patch(
    "nonebot_plugin_zikequote3.command.cmds.group_migration.render_migration_diff",
    return_value="<html>migration</html>",
):
    from nonebot_plugin_zikequote3.command.cmds.group_migration import (
        handle_group_migration,
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Match 对象。"""
    match = MagicMock()
    match.available = available
    match.result = result
    return match



def _make_query(available: bool = True, result=None) -> MagicMock:
    """创建模拟的 Query 对象。"""
    query = MagicMock()
    query.available = available
    query.result = result
    return query



def _build_services() -> dict[str, MagicMock | AsyncMock]:
    """构建所有 mock 服务。"""
    return {
        "migration_svc": AsyncMock(spec=MigrationService),
        "group_svc": AsyncMock(spec=GroupService),
        "token_mgr": MagicMock(spec=TokenManager),
        "html_render_svc": AsyncMock(spec=HtmlRenderServiceBase),
    }



def _prepare_preview(
    *,
    source_count: int = 10,
    target_count: int = 5,
    final_count: int = 15,
    before_members: int = 3,
    after_members: int = 5,
    snapshot: object | None = None,
) -> SimpleNamespace:
    """构建 prepare_migration 的默认预览返回值。"""
    return SimpleNamespace(
        source_count=source_count,
        target_count=target_count,
        final_count=final_count,
        before_members=before_members,
        after_members=after_members,
        snapshot=object() if snapshot is None else snapshot,
    )



def _patch_stage_container(patch_container, svcs: dict[str, MagicMock | AsyncMock]):
    return patch_container({
        MigrationService: svcs["migration_svc"],
        GroupService: svcs["group_svc"],
        TokenManager: svcs["token_mgr"],
        HtmlRenderServiceBase: svcs["html_render_svc"],
    })


# ---------------------------------------------------------------------------
# 参数验证阶段
# ---------------------------------------------------------------------------


class TestHandleGroupMigrationValidation:
    """群迁移命令 —— 参数验证阶段。"""

    async def test_source_not_available(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=False),
                target=_make_match(available=True, result="999999"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("请提供源群号和目标群号" in str(call) for call in finish_calls)

    async def test_target_not_available(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=False),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("请提供源群号和目标群号" in str(call) for call in finish_calls)

    async def test_source_group_not_exists(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(
            side_effect=lambda gid: False if gid == "111111" else True
        )
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("找不到来源群" in str(call) for call in finish_calls)

    async def test_target_group_not_exists(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(
            side_effect=lambda gid: False if gid == "222222" else True
        )
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("目标群" in str(call) for call in finish_calls)

    async def test_same_source_and_target(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="111111"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("不能与目标群相同" in str(call) for call in finish_calls)


# ---------------------------------------------------------------------------
# 预览阶段
# ---------------------------------------------------------------------------


class TestHandleGroupMigrationPrepare:
    """群迁移命令 —— 预览阶段。"""

    async def test_source_no_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_preview(source_count=0, final_count=5, after_members=3)
        )
        _patch_stage_container(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("没有语录" in str(call) for call in finish_calls)


# ---------------------------------------------------------------------------
# 确认阶段
# ---------------------------------------------------------------------------


class TestHandleGroupMigrationConfirm:
    """群迁移命令 —— 确认阶段（waiter 交互）。"""

    async def test_timeout_cancel_does_not_write(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_preview()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=None)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        svcs["migration_svc"].execute_migration.assert_not_awaited()
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("已取消" in str(call) for call in finish_calls)

    async def test_wrong_format_cancel_does_not_write(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_preview()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "取消"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        svcs["migration_svc"].execute_migration.assert_not_awaited()
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("已取消" in str(call) for call in finish_calls)

    async def test_token_verify_failed_does_not_write(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_preview()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(
            return_value=(False, "Token 已过期")
        )
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 wrong-token"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        svcs["migration_svc"].execute_migration.assert_not_awaited()
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("Token 验证失败" in str(call) for call in finish_calls)


# ---------------------------------------------------------------------------
# 执行阶段
# ---------------------------------------------------------------------------


class TestHandleGroupMigrationExecute:
    """群迁移命令 —— 执行阶段。"""

    async def test_migration_success_uses_explicit_stage_scopes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        preview = _prepare_preview(snapshot=object())
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=preview)
        svcs["migration_svc"].execute_migration = AsyncMock(return_value=None)
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(return_value=(True, "成功"))
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        ctx = _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        svcs["migration_svc"].execute_migration.assert_awaited_once_with(
            snapshot=preview.snapshot,
            clear_member_info=False,
        )
        assert ctx.container.call_count == 6
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("迁移成功" in str(call) for call in finish_calls)

    async def test_prepare_and_execute_propagate_non_default_options(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        preview = _prepare_preview(snapshot=object())
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=preview)
        svcs["migration_svc"].execute_migration = AsyncMock(return_value=None)
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(return_value=(True, "成功"))
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=True),
                duplicate=_make_query(result=True),
                exclude_member=_make_query(result=True),
                clear_member_info=_make_query(result=True),
                keep_source=_make_query(result=True),
            )

        svcs["migration_svc"].prepare_migration.assert_awaited_once_with(
            source="111111",
            target="222222",
            overwrite=True,
            deduplicate=True,
            exclude_non_member=True,
            keep_source=True,
        )
        svcs["migration_svc"].execute_migration.assert_awaited_once_with(
            snapshot=preview.snapshot,
            clear_member_info=True,
        )

    async def test_preview_drift_requires_repreview(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        preview = _prepare_preview(snapshot=object())
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=preview)
        svcs["migration_svc"].execute_migration = AsyncMock(
            side_effect=OperationError(
                "迁移预览已过期，底层数据已发生变化，请重新预览后再执行"
            )
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(return_value=(True, "成功"))
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("重新预览" in str(call) for call in finish_calls)

    async def test_migration_failure_is_reported(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        preview = _prepare_preview(snapshot=object())
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=preview)
        svcs["migration_svc"].execute_migration = AsyncMock(
            side_effect=OperationError("迁移群名片失败")
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(return_value=(True, "成功"))
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("操作失败：迁移群名片失败" in str(call) for call in finish_calls)

    async def test_render_fallback_to_text(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        preview = _prepare_preview(snapshot=object())
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=preview)
        svcs["migration_svc"].execute_migration = AsyncMock(return_value=None)
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(return_value=(True, "成功"))
        svcs["html_render_svc"].render = AsyncMock(
            side_effect=RuntimeError("render failed")
        )
        _patch_stage_container(patch_container, svcs)

        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with pytest.raises(FinishedException):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
            )

        waiter_prompt_args = waiter_mod.prompt.await_args.args
        assert isinstance(waiter_prompt_args[0], str)
        assert "确认 test-token-123" in waiter_prompt_args[0]
        svcs["migration_svc"].execute_migration.assert_awaited_once()
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("迁移成功" in str(call) for call in finish_calls)
