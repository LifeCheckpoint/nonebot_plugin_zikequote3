"""MsgQueueRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.msgs_queue import MsgQueue
from nonebot_plugin_zikequote3.database.models.queue_group_message_counts import QueueGroupMessageCount
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import MsgQueueRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed(group_repo, user_repo, group_id, qq_id):
    """创建前置 group 和 user 记录（外键约束）。"""
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"group_{group_id}")
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)


class TestMsgQueueCreate:
    """创建相关测试。"""

    async def test_create_msg(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g1", "mq_u1")
        result = await msg_queue_repo.create_msg("mq_m1", "mq_g1", "mq_u1", "消息内容")
        assert isinstance(result, MsgQueue)
        assert result.msg_id == "mq_m1"
        assert result.group_id == "mq_g1"
        assert result.qq_id == "mq_u1"
        assert result.content == "消息内容"


class TestMsgQueueRead:
    """查询相关测试。"""

    async def test_get_msg_by_id(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g10", "mq_u10")
        await msg_queue_repo.create_msg("mq_m10", "mq_g10", "mq_u10", "内容")
        result = await msg_queue_repo.get_msg_by_id("mq_m10")
        assert result is not None
        assert result.msg_id == "mq_m10"

    async def test_get_msg_by_id_not_found(self, msg_queue_repo: MsgQueueRepository):
        result = await msg_queue_repo.get_msg_by_id("nonexistent")
        assert result is None

    async def test_get_msgs_by_group(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g11", "mq_u11")
        await msg_queue_repo.create_msg("mq_m11a", "mq_g11", "mq_u11", "A")
        await msg_queue_repo.create_msg("mq_m11b", "mq_g11", "mq_u11", "B")
        results = await msg_queue_repo.get_msgs_by_group("mq_g11")
        assert len(results) == 2

    async def test_get_msgs_by_group_with_limit(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g12", "mq_u12")
        await msg_queue_repo.create_msg("mq_m12a", "mq_g12", "mq_u12", "A")
        await msg_queue_repo.create_msg("mq_m12b", "mq_g12", "mq_u12", "B")
        await msg_queue_repo.create_msg("mq_m12c", "mq_g12", "mq_u12", "C")
        results = await msg_queue_repo.get_msgs_by_group("mq_g12", limit=2)
        assert len(results) == 2

    async def test_get_msgs_by_user(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g13", "mq_u13")
        await msg_queue_repo.create_msg("mq_m13", "mq_g13", "mq_u13", "用户消息")
        results = await msg_queue_repo.get_msgs_by_user("mq_u13")
        assert len(results) >= 1

    async def test_get_recent_msgs_by_group(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g14", "mq_u14")
        await msg_queue_repo.create_msg("mq_m14", "mq_g14", "mq_u14", "最近消息")
        results = await msg_queue_repo.get_recent_msgs_by_group("mq_g14", limit=10)
        assert len(results) >= 1

    async def test_count_msgs_by_group(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g15", "mq_u15")
        await msg_queue_repo.create_msg("mq_m15a", "mq_g15", "mq_u15", "A")
        await msg_queue_repo.create_msg("mq_m15b", "mq_g15", "mq_u15", "B")
        count = await msg_queue_repo.count_msgs_by_group("mq_g15")
        assert count == 2

    async def test_count_msgs_by_group_zero(self, msg_queue_repo: MsgQueueRepository):
        count = await msg_queue_repo.count_msgs_by_group("empty_group")
        assert count == 0


class TestMsgQueueDelete:
    """删除相关测试。"""

    async def test_clear_group_queue(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g20", "mq_u20")
        await msg_queue_repo.create_msg("mq_m20a", "mq_g20", "mq_u20", "A")
        await msg_queue_repo.create_msg("mq_m20b", "mq_g20", "mq_u20", "B")
        ok = await msg_queue_repo.clear_group_queue("mq_g20")
        assert ok is True
        count = await msg_queue_repo.count_msgs_by_group("mq_g20")
        assert count == 0

    async def test_clear_empty_group_queue(self, msg_queue_repo: MsgQueueRepository):
        ok = await msg_queue_repo.clear_group_queue("empty_group")
        assert ok is True

    async def test_delete_old_msgs(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "mq_g21", "mq_u21")
        await msg_queue_repo.create_msg("mq_m21", "mq_g21", "mq_u21", "新消息")
        # 刚创建的消息不应被删除（days=30）
        ok = await msg_queue_repo.delete_old_msgs(days=30)
        assert ok is True
        result = await msg_queue_repo.get_msg_by_id("mq_m21")
        assert result is not None


class TestQueueCount:
    """queue_group_message_counts 相关测试。"""

    async def test_get_queue_count_none(self, msg_queue_repo: MsgQueueRepository):
        result = await msg_queue_repo.get_queue_count("nonexistent_group")
        assert result is None

    async def test_set_queue_count_create(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository,
    ):
        if not await group_repo.group_exists("mq_gc1"):
            await group_repo.create_group("mq_gc1", "group_mq_gc1")
        result = await msg_queue_repo.set_queue_count("mq_gc1", 5)
        assert isinstance(result, QueueGroupMessageCount)
        assert result.group_id == "mq_gc1"
        assert result.message_count == 5

    async def test_set_queue_count_update(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository,
    ):
        if not await group_repo.group_exists("mq_gc2"):
            await group_repo.create_group("mq_gc2", "group_mq_gc2")
        await msg_queue_repo.set_queue_count("mq_gc2", 3)
        result = await msg_queue_repo.set_queue_count("mq_gc2", 10)
        assert result.message_count == 10

    async def test_increment_queue_count_new(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository,
    ):
        if not await group_repo.group_exists("mq_gc3"):
            await group_repo.create_group("mq_gc3", "group_mq_gc3")
        result = await msg_queue_repo.increment_queue_count("mq_gc3")
        assert result.message_count == 1

    async def test_increment_queue_count_existing(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository,
    ):
        if not await group_repo.group_exists("mq_gc4"):
            await group_repo.create_group("mq_gc4", "group_mq_gc4")
        await msg_queue_repo.set_queue_count("mq_gc4", 5)
        result = await msg_queue_repo.increment_queue_count("mq_gc4", delta=3)
        assert result.message_count == 8

    async def test_reset_queue_count(
        self, msg_queue_repo: MsgQueueRepository,
        group_repo: GroupRepository,
    ):
        if not await group_repo.group_exists("mq_gc5"):
            await group_repo.create_group("mq_gc5", "group_mq_gc5")
        await msg_queue_repo.set_queue_count("mq_gc5", 10)
        ok = await msg_queue_repo.reset_queue_count("mq_gc5")
        assert ok is True
        result = await msg_queue_repo.get_queue_count("mq_gc5")
        assert result is not None
        assert result.message_count == 0

    async def test_reset_queue_count_nonexistent(
        self, msg_queue_repo: MsgQueueRepository,
    ):
        ok = await msg_queue_repo.reset_queue_count("nonexistent_group")
        assert ok is False
