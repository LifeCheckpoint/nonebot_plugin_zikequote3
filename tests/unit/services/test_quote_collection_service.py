"""QuoteCollectionService 单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from nonebot_plugin_zikequote3.database.models.msgs_queue import MsgQueue
from nonebot_plugin_zikequote3.exceptions import ValidationException
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectedQuote,
    CollectionLockError,
    CollectionLockManager,
    QuoteCollectionService,
    SelectedQuote,
)
from nonebot_plugin_zikequote3.services.review_service import AUTHOR_AI, ReviewService


# ------------------------------------------------------------------ #
#  辅助工厂
# ------------------------------------------------------------------ #

def _make_msg(
    msg_id: str = "msg_001",
    group_id: str = "12345",
    qq_id: str = "10001",
    content: str = "hello world",
) -> MsgQueue:
    return MsgQueue(
        msg_id=msg_id,
        group_id=group_id,
        qq_id=qq_id,
        content=content,
        time_stamp=datetime.now(),
    )


def _build_collection_service(
    *,
    mock_msg_queue_repo: AsyncMock,
    mock_quote_repo: AsyncMock,
    mock_image_repo: AsyncMock,
    mock_mapping_repo: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_user_nickname_repo: AsyncMock,
    mock_group_nickname_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
    mock_group_repo: AsyncMock,
    message_filter: AsyncMock | None = None,
    review_service: AsyncMock | ReviewService | None = None,
    lock_manager: CollectionLockManager | None = None,
) -> QuoteCollectionService:
    from nonebot_plugin_zikequote3.services.config_service import ConfigService
    from nonebot_plugin_zikequote3.services.group_service import GroupService
    from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
    from nonebot_plugin_zikequote3.services.user_service import UserService

    user_service = UserService(
        user_repo=mock_user_repo,
        user_nickname_repo=mock_user_nickname_repo,
        group_nickname_repo=mock_group_nickname_repo,
        group_member_repo=mock_group_member_repo,
    )
    config_service = AsyncMock(spec=ConfigService)
    quote_write_service = QuoteWriteService(
        quote_repo=mock_quote_repo,
        image_repo=mock_image_repo,
        mapping_repo=mock_mapping_repo,
        user_service=user_service,
        config_service=config_service,
        group_repo=mock_group_repo,
    )
    group_service = GroupService(
        group_repo=mock_group_repo,
        group_member_repo=mock_group_member_repo,
        group_nickname_repo=mock_group_nickname_repo,
    )
    return QuoteCollectionService(
        msg_queue_repo=mock_msg_queue_repo,
        quote_write_service=quote_write_service,
        user_service=user_service,
        group_service=group_service,
        review_service=review_service or AsyncMock(spec=ReviewService),
        lock_manager=lock_manager or CollectionLockManager(),
        message_filter=message_filter,
    )


# ------------------------------------------------------------------ #
#  入队操作
# ------------------------------------------------------------------ #

class TestEnqueueMessage:
    """测试 enqueue_message 方法。"""

    @pytest.mark.asyncio
    async def test_enqueue_message_success(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
        mock_user_repo: AsyncMock,
    ) -> None:
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None

        await quote_collection_service.enqueue_message(
            group_id="12345",
            msg_id="msg_001",
            user_id="10001",
            content="  hello world  ",
        )

        mock_msg_queue_repo.create_msg.assert_awaited_once_with(
            msg_id="msg_001",
            group_id="12345",
            qq_id="10001",
            content="hello world",
        )

    @pytest.mark.asyncio
    async def test_enqueue_ensures_user_exists(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_user_repo: AsyncMock,
    ) -> None:
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None

        await quote_collection_service.enqueue_message(
            group_id="12345",
            msg_id="msg_002",
            user_id="10002",
            content="test",
        )

        # get_or_create_user 内部会调用 get_by_qq_id
        mock_user_repo.get_by_qq_id.assert_awaited()


# ------------------------------------------------------------------ #
#  队列计数
# ------------------------------------------------------------------ #

class TestGetQueueCount:
    """测试 get_queue_count 方法。"""

    @pytest.mark.asyncio
    async def test_returns_count(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.count_msgs_by_group.return_value = 42

        result = await quote_collection_service.get_queue_count("12345")

        assert result == 42
        mock_msg_queue_repo.count_msgs_by_group.assert_awaited_once_with("12345")

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_queue(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.count_msgs_by_group.return_value = 0

        result = await quote_collection_service.get_queue_count("99999")

        assert result == 0


# ------------------------------------------------------------------ #
#  阈值检查
# ------------------------------------------------------------------ #

class TestShouldTriggerCollection:
    """测试 should_trigger_collection 方法。"""

    @pytest.mark.asyncio
    async def test_below_threshold(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.count_msgs_by_group.return_value = 5

        result = await quote_collection_service.should_trigger_collection("12345", 10)

        assert result is False

    @pytest.mark.asyncio
    async def test_at_threshold(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.count_msgs_by_group.return_value = 10

        result = await quote_collection_service.should_trigger_collection("12345", 10)

        assert result is True

    @pytest.mark.asyncio
    async def test_above_threshold(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.count_msgs_by_group.return_value = 15

        result = await quote_collection_service.should_trigger_collection("12345", 10)

        assert result is True


# ------------------------------------------------------------------ #
#  队列清空
# ------------------------------------------------------------------ #

class TestClearQueue:
    """测试 clear_queue 方法。"""

    @pytest.mark.asyncio
    async def test_clear_queue(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.clear_group_queue.return_value = True

        await quote_collection_service.clear_queue("12345")

        mock_msg_queue_repo.clear_group_queue.assert_awaited_once_with("12345")


# ------------------------------------------------------------------ #
#  收集锁
# ------------------------------------------------------------------ #

class TestCollectionLock:
    """测试收集锁机制。"""

    def test_lock_acquire_and_release(
        self,
        quote_collection_service: QuoteCollectionService,
    ) -> None:
        assert not quote_collection_service.is_collecting("12345")

        quote_collection_service.acquire_lock("12345")
        assert quote_collection_service.is_collecting("12345")

        quote_collection_service.release_lock("12345")
        assert not quote_collection_service.is_collecting("12345")

    def test_double_acquire_raises(
        self,
        quote_collection_service: QuoteCollectionService,
    ) -> None:
        quote_collection_service.acquire_lock("12345")

        with pytest.raises(CollectionLockError):
            quote_collection_service.acquire_lock("12345")

        quote_collection_service.release_lock("12345")

    def test_different_groups_independent(
        self,
        quote_collection_service: QuoteCollectionService,
    ) -> None:
        quote_collection_service.acquire_lock("11111")
        quote_collection_service.acquire_lock("22222")

        assert quote_collection_service.is_collecting("11111")
        assert quote_collection_service.is_collecting("22222")

        quote_collection_service.release_lock("11111")
        quote_collection_service.release_lock("22222")


class TestCollectionLockAcrossInstances:
    """测试共享锁跨服务实例生效。"""

    @pytest.mark.asyncio
    async def test_shared_lock_manager_prevents_cross_instance_collect(
        self,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        shared_lock = CollectionLockManager()
        svc1 = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            lock_manager=shared_lock,
        )
        svc2 = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            lock_manager=shared_lock,
        )

        svc1.acquire_lock("12345")
        assert svc2.is_collecting("12345")

        with pytest.raises(CollectionLockError):
            await svc2.collect_and_save("12345", allow_duplicate=False)

        mock_msg_queue_repo.get_msgs_by_group.assert_not_awaited()
        svc1.release_lock("12345")


# ------------------------------------------------------------------ #
#  收集保存流程
# ------------------------------------------------------------------ #

class TestCollectAndSave:
    """测试 collect_and_save 方法。"""

    @pytest.mark.asyncio
    async def test_empty_queue_raises(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.get_msgs_by_group.return_value = []

        with pytest.raises(ValidationException, match="队列为空"):
            await quote_collection_service.collect_and_save(
                "12345",
                allow_duplicate=False,
            )

    @pytest.mark.asyncio
    async def test_collect_saves_quotes(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_user_repo: AsyncMock,
    ) -> None:
        msg = _make_msg()
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_msg_queue_repo.get_msg_by_id.return_value = msg
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_image_repo.image_exists.return_value = False

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="99999999999",
        ):
            mock_quote_repo.create_quote.return_value = None
            result = await quote_collection_service.collect_and_save(
                "12345",
                allow_duplicate=True,
            )

        assert len(result) == 1
        assert isinstance(result[0], CollectedQuote)
        assert result[0].quote_id == "99999999999"
        assert result[0].comment is None

    @pytest.mark.asyncio
    async def test_collect_skips_duplicates_when_disabled(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_user_repo: AsyncMock,
    ) -> None:
        msg = _make_msg(content="重复内容")
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_quote_repo.check_quote_exists_by_author_content.return_value = True

        result = await quote_collection_service.collect_and_save(
            "12345",
            allow_duplicate=False,
        )

        assert result == []
        mock_quote_repo.check_quote_exists_by_author_content.assert_awaited_once_with(
            "10001",
            "重复内容",
        )
        mock_quote_repo.create_quote.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_collect_allows_duplicates_when_enabled(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_user_repo: AsyncMock,
    ) -> None:
        msg = _make_msg(content="重复内容")
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_quote_repo.check_quote_exists_by_author_content.return_value = True

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="12345678901",
        ):
            mock_quote_repo.create_quote.return_value = None
            result = await quote_collection_service.collect_and_save(
                "12345",
                allow_duplicate=True,
            )

        assert [item.quote_id for item in result] == ["12345678901"]
        mock_quote_repo.check_quote_exists_by_author_content.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_collect_releases_lock_on_error(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.get_msgs_by_group.return_value = []

        with pytest.raises(ValidationException):
            await quote_collection_service.collect_and_save(
                "12345",
                allow_duplicate=False,
            )

        # 锁应该已释放
        assert not quote_collection_service.is_collecting("12345")

    @pytest.mark.asyncio
    async def test_collect_lock_prevents_concurrent(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        # 手动持有锁
        quote_collection_service.acquire_lock("12345")

        with pytest.raises(CollectionLockError):
            await quote_collection_service.collect_and_save(
                "12345",
                allow_duplicate=False,
            )

        quote_collection_service.release_lock("12345")


class TestCollectAndFinalize:
    """测试 collect_and_finalize 方法。"""

    @pytest.mark.asyncio
    async def test_finalize_adds_ai_reviews_and_clears_queue(
        self,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        msg = _make_msg(content="这是一句名言")
        mock_filter = AsyncMock()
        mock_filter.filter_messages.return_value = [
            SelectedQuote(
                msg_id="msg_001",
                content="这是一句名言",
                comment="AI点评",
            ),
        ]
        mock_review_service = AsyncMock(spec=ReviewService)
        svc = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            message_filter=mock_filter,
            review_service=mock_review_service,
        )
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_image_repo.image_exists.return_value = False

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="66666666666",
        ):
            mock_quote_repo.create_quote.return_value = None
            result = await svc.collect_and_finalize(
                "12345",
                allow_duplicate=True,
            )

        assert len(result) == 1
        mock_review_service.add_review.assert_awaited_once_with(
            quote_id="66666666666",
            author_id=AUTHOR_AI,
            content="AI点评",
        )
        mock_msg_queue_repo.clear_group_queue.assert_awaited_once_with("12345")

    @pytest.mark.asyncio
    async def test_finalize_review_failure_keeps_queue_uncleared_and_releases_lock(
        self,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        msg = _make_msg(content="这是一句名言")
        mock_filter = AsyncMock()
        mock_filter.filter_messages.return_value = [
            SelectedQuote(
                msg_id="msg_001",
                content="这是一句名言",
                comment="AI点评",
            ),
        ]
        mock_review_service = AsyncMock(spec=ReviewService)
        mock_review_service.add_review.side_effect = RuntimeError("AI review failed")
        svc = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            message_filter=mock_filter,
            review_service=mock_review_service,
        )
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_image_repo.image_exists.return_value = False

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="55555555555",
        ):
            mock_quote_repo.create_quote.return_value = None
            with pytest.raises(RuntimeError, match="AI review failed"):
                await svc.collect_and_finalize(
                    "12345",
                    allow_duplicate=True,
                )

        mock_msg_queue_repo.clear_group_queue.assert_not_awaited()
        assert not svc.is_collecting("12345")


# ------------------------------------------------------------------ #
#  CollectedQuote 数据类
# ------------------------------------------------------------------ #

class TestCollectedQuote:
    """测试 CollectedQuote 数据类。"""

    def test_default_comment_is_none(self) -> None:
        cq = CollectedQuote(quote_id="q001")
        assert cq.quote_id == "q001"
        assert cq.comment is None

    def test_with_comment(self) -> None:
        cq = CollectedQuote(quote_id="q002", comment="好句子！")
        assert cq.quote_id == "q002"
        assert cq.comment == "好句子！"

    def test_equality(self) -> None:
        a = CollectedQuote(quote_id="q003", comment="评论")
        b = CollectedQuote(quote_id="q003", comment="评论")
        assert a == b


# ------------------------------------------------------------------ #
#  收集流程 — comment 传递
# ------------------------------------------------------------------ #

class TestCollectAndSaveWithComment:
    """测试 collect_and_save 返回 CollectedQuote 含 comment。"""

    @pytest.mark.asyncio
    async def test_collect_with_filter_preserves_comment(
        self,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        """当 MessageFilter 返回带 comment 的 SelectedQuote 时，
        collect_and_save 应返回含 comment 的 CollectedQuote。"""
        # 构造 mock MessageFilter，返回带 comment 的 SelectedQuote
        mock_filter = AsyncMock()
        mock_filter.filter_messages.return_value = [
            SelectedQuote(
                msg_id="msg_001",
                content="这是一句名言",
                comment="AI觉得这句话很有哲理",
            ),
        ]

        svc = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            message_filter=mock_filter,
        )

        msg = _make_msg(content="这是一句名言")
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_msg_queue_repo.get_msg_by_id.return_value = msg
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_image_repo.image_exists.return_value = False

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="88888888888",
        ):
            mock_quote_repo.create_quote.return_value = None
            result = await svc.collect_and_save(
                "12345",
                allow_duplicate=True,
            )

        assert len(result) == 1
        assert isinstance(result[0], CollectedQuote)
        assert result[0].quote_id == "88888888888"
        assert result[0].comment == "AI觉得这句话很有哲理"

    @pytest.mark.asyncio
    async def test_collect_empty_comment_becomes_none(
        self,
        mock_msg_queue_repo: AsyncMock,
        mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        """当 SelectedQuote.comment 为空字符串时，
        CollectedQuote.comment 应为 None。"""
        # comment 为空字符串（SelectedQuote 默认值）
        mock_filter = AsyncMock()
        mock_filter.filter_messages.return_value = [
            SelectedQuote(msg_id="msg_001", content="普通消息", comment=""),
        ]

        svc = _build_collection_service(
            mock_msg_queue_repo=mock_msg_queue_repo,
            mock_quote_repo=mock_quote_repo,
            mock_image_repo=mock_image_repo,
            mock_mapping_repo=mock_mapping_repo,
            mock_user_repo=mock_user_repo,
            mock_user_nickname_repo=mock_user_nickname_repo,
            mock_group_nickname_repo=mock_group_nickname_repo,
            mock_group_member_repo=mock_group_member_repo,
            mock_group_repo=mock_group_repo,
            message_filter=mock_filter,
        )

        msg = _make_msg(content="普通消息")
        mock_msg_queue_repo.get_msgs_by_group.return_value = [msg]
        mock_msg_queue_repo.get_msg_by_id.return_value = msg
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_image_repo.image_exists.return_value = False

        with patch(
            "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
            return_value="77777777777",
        ):
            mock_quote_repo.create_quote.return_value = None
            result = await svc.collect_and_save(
                "12345",
                allow_duplicate=True,
            )

        assert len(result) == 1
        assert result[0].quote_id == "77777777777"
        assert result[0].comment is None
