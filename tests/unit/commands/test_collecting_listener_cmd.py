"""
collecting_listener_cmd 命令处理器单元测试。

覆盖：
- handle_collecting_listener：自动收集监听器
  - 空消息 → 直接返回
  - 消息过长 → 直接返回
  - 正常消息、未达阈值 → 入队但不触发收集
  - 正常消息、达到阈值、已有收集任务 → 跳过
  - 正常消息、达到阈值、收集成功（含 AI 评论）
  - 正常消息、达到阈值、收集成功（无评论）
  - 概率更新用户信息
  - 入队异常 → silent_error_handler 捕获
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectedQuote,
    QuoteCollectionService,
)
from nonebot_plugin_zikequote3.services.review_service import ReviewService
from nonebot_plugin_zikequote3.services.user_service import UserService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_collecting_listener: MagicMock = getattr(
    _stub_cmd_def, "matcher_collecting_listener"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.collecting_listener_cmd import (
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
) -> MagicMock:
    """创建模拟的 parsed config 对象。"""
    cfg = MagicMock()
    cfg.collecting.enable_auto_collect = enable_auto_collect
    cfg.collecting.msg_max_length = msg_max_length
    cfg.collecting.update_personal_info_probability = update_prob
    cfg.collecting.pickup_interval = pickup_interval
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


def _build_services(parsed_cfg=None):
    """构建所有 mock 服务。"""
    mock_config_svc = AsyncMock(spec=ConfigService)
    mock_config_svc.get_parsed_config = AsyncMock(
        return_value=parsed_cfg or _make_parsed_cfg()
    )

    mock_collection_svc = AsyncMock(spec=QuoteCollectionService)
    mock_collection_svc.enqueue_message = AsyncMock(return_value=None)
    mock_collection_svc.should_trigger_collection = AsyncMock(
        return_value=False
    )
    mock_collection_svc.is_collecting = MagicMock(return_value=False)
    mock_collection_svc.collect_and_save = AsyncMock(return_value=[])
    mock_collection_svc.clear_queue = AsyncMock(return_value=None)

    mock_group_svc = AsyncMock(spec=GroupService)
    mock_group_svc.ensure_member = AsyncMock(return_value=None)

    mock_review_svc = AsyncMock(spec=ReviewService)
    mock_review_svc.add_review = AsyncMock(return_value=None)

    mock_user_svc = AsyncMock(spec=UserService)
    mock_user_svc.sync_nickname = AsyncMock(return_value=None)
    mock_user_svc.sync_group_card = AsyncMock(return_value=None)

    return {
        "config_svc": mock_config_svc,
        "collection_svc": mock_collection_svc,
        "group_svc": mock_group_svc,
        "review_svc": mock_review_svc,
        "user_svc": mock_user_svc,
    }


class TestHandleCollectingListenerEarlyReturn:
    """收集监听器 —— 消息验证阶段（提前返回）。"""

    async def test_auto_collect_disabled(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """enable_auto_collect=False：直接返回，不入队。"""
        svcs = _build_services(
            parsed_cfg=_make_parsed_cfg(enable_auto_collect=False)
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证 enqueue_message 未被调用
        svcs["collection_svc"].enqueue_message.assert_not_awaited()

    async def test_empty_message(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """空消息：直接返回，不入队。"""
        svcs = _build_services()
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="")

        # 正常返回，不抛异常
        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证 enqueue_message 未被调用
        svcs["collection_svc"].enqueue_message.assert_not_awaited()

    async def test_whitespace_only_message(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """纯空白消息：strip 后为空，直接返回。"""
        svcs = _build_services()
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="   \n  ")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        svcs["collection_svc"].enqueue_message.assert_not_awaited()

    async def test_message_too_long(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """消息超过 max_length：直接返回。"""
        svcs = _build_services(
            parsed_cfg=_make_parsed_cfg(msg_max_length=10)
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="这条消息超过了十个字符的限制哦")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        svcs["collection_svc"].enqueue_message.assert_not_awaited()


class TestHandleCollectingListenerEnqueue:
    """收集监听器 —— 入队与阈值检查阶段。"""

    async def test_enqueue_not_threshold(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """正常消息、未达阈值：入队但不触发收集。"""
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(
            return_value=False
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证入队被调用
        svcs["collection_svc"].enqueue_message.assert_awaited_once()
        # 验证 collect_and_save 未被调用
        svcs["collection_svc"].collect_and_save.assert_not_awaited()

    async def test_enqueue_error_raises_finished(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """入队异常：silent_error_handler 捕获并抛出 FinishedException。"""
        svcs = _build_services()
        svcs["collection_svc"].enqueue_message = AsyncMock(
            side_effect=RuntimeError("DB connection lost")
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        with pytest.raises(FinishedException):
            await handle_collecting_listener(
                event=event,
                bot=mock_bot,
                config_svc=svcs["config_svc"],
                collection_svc=svcs["collection_svc"],
                group_svc=svcs["group_svc"],
                review_svc=svcs["review_svc"],
                user_svc=svcs["user_svc"],
            )


class TestHandleCollectingListenerCollection:
    """收集监听器 —— 收集执行阶段。"""

    async def test_already_collecting_skip(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """达到阈值但已有收集任务：跳过收集。"""
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(
            return_value=True
        )
        svcs["collection_svc"].is_collecting = MagicMock(return_value=True)
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证 collect_and_save 未被调用
        svcs["collection_svc"].collect_and_save.assert_not_awaited()

    async def test_collect_success_with_comments(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """达到阈值、收集成功且有 AI 评论。"""
        collected = [
            CollectedQuote(quote_id="Q-1", comment="好语录"),
            CollectedQuote(quote_id="Q-2", comment=None),
            CollectedQuote(quote_id="Q-3", comment="精彩"),
        ]
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(
            return_value=True
        )
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_save = AsyncMock(
            return_value=collected
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证 collect_and_save 被调用
        svcs["collection_svc"].collect_and_save.assert_awaited_once_with(
            "123456"
        )
        # 只有 comment 非 None 的才调用 add_review（Q-1 和 Q-3）
        assert svcs["review_svc"].add_review.await_count == 2
        # 验证 clear_queue 被调用
        svcs["collection_svc"].clear_queue.assert_awaited_once_with("123456")

    async def test_collect_success_no_comments(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """达到阈值、收集成功但无 AI 评论。"""
        collected = [
            CollectedQuote(quote_id="Q-1", comment=None),
            CollectedQuote(quote_id="Q-2", comment=None),
        ]
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(
            return_value=True
        )
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_save = AsyncMock(
            return_value=collected
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # add_review 不应被调用
        svcs["review_svc"].add_review.assert_not_awaited()
        # clear_queue 仍应被调用
        svcs["collection_svc"].clear_queue.assert_awaited_once()

    async def test_collect_empty_result(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """达到阈值、收集结果为空列表。"""
        svcs = _build_services()
        svcs["collection_svc"].should_trigger_collection = AsyncMock(
            return_value=True
        )
        svcs["collection_svc"].is_collecting = MagicMock(return_value=False)
        svcs["collection_svc"].collect_and_save = AsyncMock(return_value=[])
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        svcs["review_svc"].add_review.assert_not_awaited()
        svcs["collection_svc"].clear_queue.assert_awaited_once()


class TestHandleCollectingListenerUserInfo:
    """收集监听器 —— 用户信息更新。"""

    async def test_update_user_info_triggered(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """概率触发用户信息更新：调用 sync_nickname 和 sync_group_card。"""
        # update_prob=1.0 确保一定触发
        svcs = _build_services(
            parsed_cfg=_make_parsed_cfg(update_prob=1.0)
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")
        mock_bot.get_group_member_info = AsyncMock(
            return_value={"nickname": "测试昵称", "card": "测试群名片"}
        )

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证用户信息更新被调用
        svcs["user_svc"].sync_nickname.assert_awaited_once_with(
            "654321", "测试昵称"
        )
        svcs["user_svc"].sync_group_card.assert_awaited_once_with(
            "654321", "123456", "测试群名片"
        )

    async def test_update_user_info_not_triggered(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """概率为 0 不触发用户信息更新。"""
        # update_prob=0.0 确保不触发
        svcs = _build_services(
            parsed_cfg=_make_parsed_cfg(update_prob=0.0)
        )
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        # 验证用户信息更新未被调用
        svcs["user_svc"].sync_nickname.assert_not_awaited()
        svcs["user_svc"].sync_group_card.assert_not_awaited()

    async def test_ensure_member_called(
        self,
        patch_container,
        mock_bot: MagicMock,
    ) -> None:
        """ensure_member 始终被调用（在 suppress_error 中）。"""
        svcs = _build_services()
        patch_container({
            ConfigService: svcs["config_svc"],
            QuoteCollectionService: svcs["collection_svc"],
            GroupService: svcs["group_svc"],
            ReviewService: svcs["review_svc"],
            UserService: svcs["user_svc"],
        })

        event = _make_event(plaintext="正常消息")

        await handle_collecting_listener(
            event=event,
            bot=mock_bot,
            config_svc=svcs["config_svc"],
            collection_svc=svcs["collection_svc"],
            group_svc=svcs["group_svc"],
            review_svc=svcs["review_svc"],
            user_svc=svcs["user_svc"],
        )

        svcs["group_svc"].ensure_member.assert_awaited_once_with(
            "123456", "654321"
        )
