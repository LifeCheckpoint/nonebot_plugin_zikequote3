"""
Verify increment_queue_count uses atomic SQL UPDATE (fix #10).
"""

import inspect

import pytest


pytestmark = pytest.mark.anyio


def _seed_group(session, group_id: str) -> None:
    from nonebot_plugin_zikequote3.database.sa.models.group import GroupModel
    session.add(GroupModel(group_id=group_id, name=f"g_{group_id}"))


class TestQueueCountAtomic:
    def test_increment_uses_sql_update(self):
        """increment_queue_count uses SQLAlchemy update with expression (atomic)."""
        from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
            MsgQueueRepository,
        )
        source = inspect.getsource(MsgQueueRepository.increment_queue_count)
        assert 'update(' in source or 'sa_update' in source, "Should use atomic UPDATE"
        assert 'message_count +' in source, "Should increment via SQL expression"

    def test_increment_has_fallback_insert(self):
        """Missing row falls back to INSERT (upsert pattern)."""
        from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
            MsgQueueRepository,
        )
        source = inspect.getsource(MsgQueueRepository.increment_queue_count)
        assert 'insert(' in source or 'INSERT' in source, "Should have insert fallback"
        assert 'rowcount' in source, "Should check rowcount for missing-row case"

    async def test_increment_queue_count_creates_new_row(self, async_session):
        """Increment creates a new queue count row for unseen group_id."""
        from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
            MsgQueueRepository,
        )
        from nonebot_plugin_zikequote3.database.sa.models.queue_count import (
            QueueGroupMessageCountModel,
        )
        test_gid = "test_atomic_new_group"
        _seed_group(async_session, test_gid)
        await async_session.flush()

        repo = MsgQueueRepository(async_session)
        result = await repo.increment_queue_count(test_gid, delta=5)
        assert result.group_id == test_gid
        assert result.message_count == 5

    async def test_increment_queue_count_updates_existing_row(self, async_session):
        """Increment atomically updates an existing row."""
        from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
            MsgQueueRepository,
        )
        test_gid = "test_atomic_existing_group"
        _seed_group(async_session, test_gid)
        await async_session.flush()

        repo = MsgQueueRepository(async_session)
        await repo.increment_queue_count(test_gid, delta=3)
        result = await repo.increment_queue_count(test_gid, delta=7)
        assert result.message_count == 10

    async def test_increment_queue_count_flushes_changes(self, async_session):
        """Increment flushes changes so they are visible to subsequent reads."""
        from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
            MsgQueueRepository,
        )
        from nonebot_plugin_zikequote3.database.sa.models.queue_count import (
            QueueGroupMessageCountModel,
        )
        test_gid = "test_atomic_flush"
        _seed_group(async_session, test_gid)
        await async_session.flush()

        repo = MsgQueueRepository(async_session)
        await repo.increment_queue_count(test_gid, delta=1)
        instance = await async_session.get(QueueGroupMessageCountModel, test_gid)
        assert instance is not None
        assert instance.message_count == 1
