"""MappingRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.msgid_quoteid_map import MsgQuoteID
from nonebot_plugin_zikequote3.database.repositories.mapping_repository import MappingRepository


pytestmark = pytest.mark.anyio


# MsgIdQuoteIdMapModel 有外键引用 quotes.quote_id，
# 需要先创建 quote 记录。为简化测试，我们用辅助函数插入最小 quote 行。

async def _seed_quote(session, quote_id: str):
    """插入最小 quote 行以满足外键约束。"""
    from nonebot_plugin_zikequote3.database.sa.models.quote import QuoteModel
    from nonebot_plugin_zikequote3.database.sa.models.user import UserModel
    from nonebot_plugin_zikequote3.database.sa.models.group import GroupModel

    # 确保 user 和 group 存在
    if not await session.get(UserModel, f"mu_{quote_id}"):
        session.add(UserModel(qq_id=f"mu_{quote_id}"))
    if not await session.get(GroupModel, f"mg_{quote_id}"):
        session.add(GroupModel(group_id=f"mg_{quote_id}", name="map_group"))
    await session.flush()

    if not await session.get(QuoteModel, quote_id):
        session.add(QuoteModel(
            quote_id=quote_id,
            author_id=f"mu_{quote_id}",
            group_id=f"mg_{quote_id}",
            content="test quote",
        ))
        await session.flush()


class TestMappingCreate:
    """创建相关测试。"""

    async def test_create_mapping(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q001")
        result = await mapping_repo.create_mapping("msg001", "q001")
        assert isinstance(result, MsgQuoteID)
        assert result.msg_id == "msg001"
        assert result.quote_id == "q001"

    async def test_update_or_create_mapping_new(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q002")
        result = await mapping_repo.update_or_create_mapping("msg002", "q002")
        assert result.msg_id == "msg002"

    async def test_update_or_create_mapping_existing(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q003")
        await _seed_quote(async_session, "q003b")
        await mapping_repo.create_mapping("msg003", "q003")
        result = await mapping_repo.update_or_create_mapping("msg003", "q003b")
        assert result.quote_id == "q003b"

    async def test_batch_create_mappings(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q010")
        await _seed_quote(async_session, "q011")
        ok = await mapping_repo.batch_create_mappings([
            {"msg_id": "bm001", "quote_id": "q010"},
            {"msg_id": "bm002", "quote_id": "q011"},
        ])
        assert ok is True
        assert await mapping_repo.mapping_exists("bm001")
        assert await mapping_repo.mapping_exists("bm002")

    async def test_batch_create_mappings_empty(self, mapping_repo: MappingRepository):
        ok = await mapping_repo.batch_create_mappings([])
        assert ok is True


class TestMappingRead:
    """查询相关测试。"""

    async def test_get_mapping_by_msg_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q100")
        await mapping_repo.create_mapping("msg100", "q100")
        result = await mapping_repo.get_mapping_by_msg_id("msg100")
        assert result is not None
        assert result.quote_id == "q100"

    async def test_get_mapping_by_msg_id_not_found(self, mapping_repo: MappingRepository):
        result = await mapping_repo.get_mapping_by_msg_id("nonexistent")
        assert result is None

    async def test_get_quote_id_by_msg_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q101")
        await mapping_repo.create_mapping("msg101", "q101")
        qid = await mapping_repo.get_quote_id_by_msg_id("msg101")
        assert qid == "q101"

    async def test_get_quote_id_by_msg_id_not_found(self, mapping_repo: MappingRepository):
        qid = await mapping_repo.get_quote_id_by_msg_id("no_such")
        assert qid is None

    async def test_get_mappings_by_quote_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q200")
        await mapping_repo.create_mapping("msg200", "q200")
        await mapping_repo.create_mapping("msg201", "q200")
        results = await mapping_repo.get_mappings_by_quote_id("q200")
        assert len(results) == 2

    async def test_mapping_exists(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q300")
        await mapping_repo.create_mapping("msg300", "q300")
        assert await mapping_repo.mapping_exists("msg300") is True
        assert await mapping_repo.mapping_exists("no_such") is False

    async def test_get_mappings_by_msg_ids(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q400")
        await mapping_repo.create_mapping("msg400", "q400")
        await mapping_repo.create_mapping("msg401", "q400")
        results = await mapping_repo.get_mappings_by_msg_ids(["msg400", "msg401", "msg999"])
        assert len(results) == 2

    async def test_get_mappings_by_msg_ids_empty(self, mapping_repo: MappingRepository):
        results = await mapping_repo.get_mappings_by_msg_ids([])
        assert results == []

    async def test_count_mappings_by_quote_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q500")
        await mapping_repo.create_mapping("msg500", "q500")
        count = await mapping_repo.count_mappings_by_quote_id("q500")
        assert count >= 1

    async def test_reassign_mappings_by_quote(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q501")
        await _seed_quote(async_session, "q502")
        await mapping_repo.create_mapping("msg501", "q501")
        await mapping_repo.create_mapping("msg502", "q501")

        ok = await mapping_repo.reassign_mappings_by_quote("q501", "q502")
        assert ok is True
        results = await mapping_repo.get_mappings_by_quote_id("q502")
        assert len(results) == 2

    async def test_get_all_mappings(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q600")
        await mapping_repo.create_mapping("msg600", "q600")
        all_m = await mapping_repo.get_all_mappings()
        assert any(m.msg_id == "msg600" for m in all_m)


class TestMappingDelete:
    """删除相关测试。"""

    async def test_delete_mapping_by_msg_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q700")
        await mapping_repo.create_mapping("msg700", "q700")
        ok = await mapping_repo.delete_mapping_by_msg_id("msg700")
        assert ok is True
        assert await mapping_repo.get_mapping_by_msg_id("msg700") is None

    async def test_delete_nonexistent_mapping(self, mapping_repo: MappingRepository):
        ok = await mapping_repo.delete_mapping_by_msg_id("no_such")
        assert ok is False

    async def test_delete_mappings_by_quote_id(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q800")
        await mapping_repo.create_mapping("msg800", "q800")
        await mapping_repo.create_mapping("msg801", "q800")
        ok = await mapping_repo.delete_mappings_by_quote_id("q800")
        assert ok is True
        results = await mapping_repo.get_mappings_by_quote_id("q800")
        assert len(results) == 0

    async def test_clear_all_mappings(self, mapping_repo: MappingRepository, async_session):
        await _seed_quote(async_session, "q900")
        await mapping_repo.create_mapping("msg900", "q900")
        ok = await mapping_repo.clear_all_mappings()
        assert ok is True
        all_m = await mapping_repo.get_all_mappings()
        assert len(all_m) == 0
