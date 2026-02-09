"""QuoteCollectionService 单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from nonebot_plugin_zikequote3.database.models.msgs_queue import MsgQueue
from nonebot_plugin_zikequote3.exceptions import ValidationException
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectionLockError,
    QuoteCollectionService,
    SelectedQuote,
)


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
            await quote_collection_service.collect_and_save("12345")

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
            result = await quote_collection_service.collect_and_save("12345")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_collect_releases_lock_on_error(
        self,
        quote_collection_service: QuoteCollectionService,
        mock_msg_queue_repo: AsyncMock,
    ) -> None:
        mock_msg_queue_repo.get_msgs_by_group.return_value = []

        with pytest.raises(ValidationException):
            await quote_collection_service.collect_and_save("12345")

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
            await quote_collection_service.collect_and_save("12345")

        quote_collection_service.release_lock("12345")
