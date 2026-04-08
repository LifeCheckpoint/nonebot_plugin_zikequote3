"""
group_migration 命令处理器单元测试。

覆盖：
- handle_group_migration：群语录迁移
  - 参数缺失（source/target 不可用）
  - 源群不存在
  - 目标群不存在
  - 源群与目标群相同
  - 源群无语录
  - 用户超时取消
  - 用户输入格式错误取消
  - Token 验证失败
  - 迁移成功
  - 图片渲染失败降级为纯文本
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import OperationError
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.migration_service import MigrationService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
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
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_query(available: bool = True, result=None) -> MagicMock:
    """创建模拟的 Query 对象。"""
    q = MagicMock()
    q.available = available
    q.result = result
    return q


def _build_services():
    """构建所有 mock 服务和默认 service_map。"""
    mock_migration_svc = AsyncMock(spec=MigrationService)
    mock_group_svc = AsyncMock(spec=GroupService)
    mock_token_mgr = MagicMock(spec=TokenManager)
    mock_html_render_svc = AsyncMock(spec=HtmlRenderServiceBase)

    return {
        "migration_svc": mock_migration_svc,
        "group_svc": mock_group_svc,
        "token_mgr": mock_token_mgr,
        "html_render_svc": mock_html_render_svc,
    }


def _prepare_result():
    """构建 prepare_migration 的默认返回值。"""
    return {
        "source_count": 10,
        "target_count": 5,
        "final_quotes": [MagicMock() for _ in range(15)],
        "final_count": 15,
        "before_members": 3,
        "after_members": 5,
    }


class TestHandleGroupMigrationValidation:
    """群迁移命令 —— 参数验证阶段。"""

    async def test_source_not_available(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """source 参数不可用：提示提供群号。"""
        svcs = _build_services()
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("请提供源群号和目标群号" in str(c) for c in finish_calls)

    async def test_target_not_available(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """target 参数不可用：提示提供群号。"""
        svcs = _build_services()
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("请提供源群号和目标群号" in str(c) for c in finish_calls)

    async def test_source_group_not_exists(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """源群不存在：提示找不到来源群。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(
            side_effect=lambda gid: False if gid == "111111" else True
        )
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("找不到来源群" in str(c) for c in finish_calls)

    async def test_target_group_not_exists(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """目标群不存在：提示没有目标群信息。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(
            side_effect=lambda gid: False if gid == "222222" else True
        )
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("目标群" in str(c) for c in finish_calls)

    async def test_same_source_and_target(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """源群与目标群相同：提示不能相同。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("不能与目标群相同" in str(c) for c in finish_calls)


class TestHandleGroupMigrationPrepare:
    """群迁移命令 —— 准备阶段（统计信息）。"""

    async def test_source_no_quotes(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """源群无语录：提示无法迁移。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value={
            "source_count": 0,
            "target_count": 5,
            "final_quotes": [],
            "final_count": 5,
            "before_members": 3,
            "after_members": 3,
        })
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("没有语录" in str(c) for c in finish_calls)


class TestHandleGroupMigrationConfirm:
    """群迁移命令 —— 确认阶段（waiter 交互）。"""

    async def test_timeout_cancel(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """用户超时未响应：取消迁移。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_result()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

        # waiter.prompt 返回 None 表示超时
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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("已取消" in str(c) for c in finish_calls)

    async def test_wrong_format_cancel(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """用户输入格式错误：取消迁移。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_result()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

        # 用户输入了错误格式
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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("已取消" in str(c) for c in finish_calls)

    async def test_token_verify_failed(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """Token 验证失败：提示失败原因。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        svcs["migration_svc"].prepare_migration = AsyncMock(
            return_value=_prepare_result()
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(
            return_value=(False, "Token 已过期")
        )
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

        # 用户输入了正确格式但 token 错误
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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("Token 验证失败" in str(c) for c in finish_calls)


class TestHandleGroupMigrationExecute:
    """群迁移命令 —— 执行阶段。"""

    async def test_migration_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """迁移成功：返回成功消息。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        result = _prepare_result()
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=result)
        svcs["migration_svc"].execute_migration = AsyncMock(return_value=None)
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(
            return_value=(True, "成功")
        )
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

        # 用户输入正确的确认 token
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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        # 验证 execute_migration 被调用且携带一致性相关参数
        svcs["migration_svc"].execute_migration.assert_awaited_once_with(
            final_quotes=result["final_quotes"],
            source="111111",
            target="222222",
            overwrite=False,
            keep_source=False,
            clear_member_info=False,
            deduplicate=False,
            exclude_non_member=False,
        )
        # 验证 finish 包含成功消息
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("迁移成功" in str(c) for c in finish_calls)

    async def test_migration_failure_is_reported(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """迁移失败：应透出可验证的业务失败信息。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        result = _prepare_result()
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=result)
        svcs["migration_svc"].execute_migration = AsyncMock(
            side_effect=OperationError("迁移群名片失败")
        )
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(
            return_value=(True, "成功")
        )
        svcs["html_render_svc"].render = AsyncMock(return_value=b"fake-img")
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

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
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("操作失败：迁移群名片失败" in str(c) for c in finish_calls)

    async def test_render_fallback_to_text(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """图片渲染失败降级为纯文本，但迁移仍可成功。"""
        svcs = _build_services()
        svcs["group_svc"].group_exists = AsyncMock(return_value=True)
        result = _prepare_result()
        svcs["migration_svc"].prepare_migration = AsyncMock(return_value=result)
        svcs["migration_svc"].execute_migration = AsyncMock(return_value=None)
        svcs["token_mgr"].generate = MagicMock(return_value="test-token-123")
        svcs["token_mgr"].verify_and_use = MagicMock(
            return_value=(True, "成功")
        )
        # 渲染失败
        svcs["html_render_svc"].render = AsyncMock(
            side_effect=RuntimeError("render failed")
        )
        patch_container({
            MigrationService: svcs["migration_svc"],
            GroupService: svcs["group_svc"],
            TokenManager: svcs["token_mgr"],
            HtmlRenderServiceBase: svcs["html_render_svc"],
        })

        # 用户输入正确的确认 token
        mock_resp = MagicMock()
        mock_resp.extract_plain_text.return_value = "确认 test-token-123"
        waiter_mod = sys.modules["nonebot_plugin_waiter"]
        waiter_mod.prompt = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.group_migration.render_migration_diff",
                side_effect=RuntimeError("template error"),
            ),
            pytest.raises(FinishedException),
        ):
            await handle_group_migration(
                event=mock_group_event,
                source=_make_match(available=True, result="111111"),
                target=_make_match(available=True, result="222222"),
                overwrite=_make_query(result=False),
                duplicate=_make_query(result=False),
                exclude_member=_make_query(result=False),
                clear_member_info=_make_query(result=False),
                keep_source=_make_query(result=False),
                migration_svc=svcs["migration_svc"],
                group_svc=svcs["group_svc"],
                token_mgr=svcs["token_mgr"],
                html_render_svc=svcs["html_render_svc"],
            )

        # 即使渲染失败，迁移仍应成功执行
        svcs["migration_svc"].execute_migration.assert_awaited_once()
        finish_calls = matcher_group_migration.finish.call_args_list
        assert any("迁移成功" in str(c) for c in finish_calls)
