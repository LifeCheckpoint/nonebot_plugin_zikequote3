"""
collecting_listener_cmd 命令处理器单元测试。

覆盖：
- handle_collecting_listener：自动收集监听器
  - 自动收集关闭 / 空消息 / 过长消息直接返回
  - 正常消息、未达阈值仅入队
  - 达到阈值且已有收集任务时跳过
  - 达到阈值时只调用统一的 collect_and_finalize 边界
  - 入队异常或收集闭环异常由 silent_error_handler 收敛为 FinishedException
  - 概率更新用户信息
  - ensure_member 始终调用
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectedQuote,
    QuoteCollectionService,
)
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_collecting_listener: MagicMock = getattr(
    _stub_cmd_def, "matcher_collecting_listener"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.collecting_listener_cmd import (  # noqa: E402
    handle_collecting_listener,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_parsed_cfg(
    msg_max_length: int = 200,
    update_prob: float = 0.0,
    pickup_interval: int = 50,
    enable_auto_collect: bool = True,
    enable_duplicate: bool = False,
) -> MagicMock:
    """创建模拟的 parsed config 对象。"""
    cfg = MagicMock()
    cfg.collecting.enable_auto_collect = enable_auto_collect
    cfg.collecting.msg_max_length = msg_max_length
    cfg.collecting.update_personal_info_probability = update_prob
    cfg.collecting.pickup_interval = pickup_interval
    cfg.collecting.enable_duplicate = enable_duplicate
    return cfg


def _make_event(
    group_id: int = 123456,
    user_id: int = 654321,
    message_id: int = 99999,
    plaintext: str = "这是一条测试消息",
) -> MagicMock:
    """创建模拟的 GroupMessageEvent，包含 get_plaintext() 方法。"""
    event = MagicMock()
    event.group_id = group_id
    event.user_id = user_id
    event.message_id = message_id
    event.get_plaintext.return_value = plaintext
    return event


def _build_services(parsed_cfg: MagicMock | None = None) -> dict[str, AsyncMock | MagicMock]:
    """构建命令测试所需 mock 服务。"""
    mock_config_svc = AsyncMock(spec=ConfigService)
    mock_config_svc.get_parsed_config = AsyncMock(
        return_value=parsed_cfg or _make_parsed_cfg()
    )

    mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
    mock_collection_svc.enqueue_message = AsyncMock(return_value=None)
    mock_collection_svc.should_trigger_collection = AsyncMock(return_value=False)
    mock_collection_svc.is_collecting = MagicMock(return_value=False)
    mock_collection_svc.collect_and_finalize = AsyncMock(return_value=[])
    mock_collection_svc.collect_and_save = AsyncMock(return_value=[])
    mock_collection_svc.clear_queue = AsyncMock(return_value=None)

    mock_group_svc = AsyncMock(spec=GroupService)
    mock_group_svc.ensure_group_exists = AsyncMock(return_value=None)
    mock_group_svc.ensure_member = AsyncMock(return_value=None)

    mock_user_svc = AsyncMock(spec=UserService)
    mock_user_svc.sync_nickname = AsyncMock(return_value=None)
    mock_user_svc.sync_group_card = AsyncMock(return_value=None)

    return {
        "config_svc": mock_config_svc,
        "collection_svc": mock_collection_svc,
        "group_svc": mock_group_svc,
        "user_svc": mock_user_svc,
    }


def _patch_services(patch_container, svcs: dict[str, AsyncMock | MagicMock]) -> None:
    patch_container({
        ConfigService: svcs["config_svc"],
        QuoteCollectionService: svcs["collection_svc"],
        GroupService: svcs["group_svc"],
        UserService: svcs["user_svc"],
    })


# ---------------------------------------------------------------------------
# 提前返回
# ---------------------------------------------------------------------------


class TestHandleCollectingListenerEarlyReturn:
    """收集监听器 —— 消息验证阶段（提前返回）。"""

    async def test_auto_collect_disabled(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(enable_auto_collect=False))
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(event=_make_event(), bot=mock_bot)

        svcs["collection_svc"].enqueue_message.assert_not_awaited()
        svcs["collection_svc"].collect_and_finalize.assert_not_awaited()

    async def test_empty_message(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(event=_make_event(plaintext=""), bot=mock_bot)

        svcs["collection_svc"].enqueue_message.assert_not_awaited()

    async def test_whitespace_only_message(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="   \n  "),
            bot=mock_bot,
        )

        svcs["collection_svc"].enqueue_message.assert_not_awaited()

    async def test_message_too_long(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(msg_max_length=10))
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="这条消息超过了十个字符的限制哦"),
            bot=mock_bot,
        )

        svcs["collection_svc"].enqueue_message.assert_not_awaited()


# ---------------------------------------------------------------------------
# 入队与阈值检查
# ---------------------------------------------------------------------------


class TestHandleCollectingListenerEnqueue:
    """收集监听器 —— 入队与阈值检查阶段。"""

    async def test_enqueue_not_threshold(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=False)
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["collection_svc"].enqueue_message.assert_awaited_once()
        svcs["collection_svc"].collect_and_finalize.assert_not_awaited()
        svcs["collection_svc"].collect_and_save.assert_not_awaited()
        svcs["collection_svc"].clear_queue.assert_not_awaited()

    async def test_enqueue_error_raises_finished(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["collection_svc"].enqueue_message = AsyncMock(
            side_effect=RuntimeError("DB connection lost")
        )
        _patch_services(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_collecting_listener(
                event=_make_event(plaintext="正常消息"),
                bot=mock_bot,
            )


# ---------------------------------------------------------------------------
# 收集执行阶段
# ---------------------------------------------------------------------------


class TestHandleCollectingListenerCollection:
    """收集监听器 —— 收集执行阶段。"""

    async def test_already_collecting_skip(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=True)
        svcs["collection_svc"].is_collecting = MagicMock(return_value=True)
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["collection_svc"].collect_and_finalize.assert_not_awaited()
        svcs["collection_svc"].collect_and_save.assert_not_awaited()

    async def test_collect_success_uses_unified_finalize_boundary(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        collected = [
            CollectedQuote(quote_id="Q-1", comment="好语录"),
            CollectedQuote(quote_id="Q-2", comment=None),
        ]
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(enable_duplicate=False))
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=True)
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_finalize = AsyncMock(return_value=collected)
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["collection_svc"].collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=False,
        )
        svcs["collection_svc"].collect_and_save.assert_not_awaited()
        svcs["collection_svc"].clear_queue.assert_not_awaited()

    async def test_collect_empty_result_still_uses_finalize_boundary(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(enable_duplicate=False))
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=True)
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_finalize = AsyncMock(return_value=[])
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["collection_svc"].collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=False,
        )
        svcs["collection_svc"].clear_queue.assert_not_awaited()

    async def test_collect_passes_duplicate_enabled_from_config(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(enable_duplicate=True))
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=True)
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_finalize = AsyncMock(return_value=[])
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["collection_svc"].collect_and_finalize.assert_awaited_once_with(
            "123456",
            allow_duplicate=True,
        )

    async def test_collect_finalize_error_raises_finished(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(return_value=True)
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_finalize = AsyncMock(
            side_effect=RuntimeError("collect failed")
        )
        _patch_services(patch_container, svcs)

        with pytest.raises(FinishedException):
            await handle_collecting_listener(
                event=_make_event(plaintext="正常消息"),
                bot=mock_bot,
            )


# ---------------------------------------------------------------------------
# 用户信息更新 / 群成员关系
# ---------------------------------------------------------------------------


class TestHandleCollectingListenerUserInfo:
    """收集监听器 —— 用户信息更新与成员关系。"""

    async def test_update_user_info_triggered(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(update_prob=1.0))
        _patch_services(patch_container, svcs)

        mock_bot.get_group_member_info = AsyncMock(
            return_value={"nickname": "测试昵称", "card": "测试群名片"}
        )

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["user_svc"].sync_nickname.assert_awaited_once_with("654321", "测试昵称")
        svcs["user_svc"].sync_group_card.assert_awaited_once_with(
            "654321", "123456", "测试群名片"
        )

    async def test_update_user_info_not_triggered(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services(parsed_cfg=_make_parsed_cfg(update_prob=0.0))
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["user_svc"].sync_nickname.assert_not_awaited()
        svcs["user_svc"].sync_group_card.assert_not_awaited()

    async def test_ensure_member_called(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        svcs = _build_services()
        _patch_services(patch_container, svcs)

        await handle_collecting_listener(
            event=_make_event(plaintext="正常消息"),
            bot=mock_bot,
        )

        svcs["group_svc"].ensure_group_exists.assert_awaited_once_with("123456")
        svcs["group_svc"].ensure_member.assert_awaited_once_with("123456", "654321")
