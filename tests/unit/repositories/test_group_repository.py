"""GroupRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.groups import Group
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository


pytestmark = pytest.mark.anyio


class TestGroupRepositoryCreate:
    """创建相关测试。"""

    async def test_create_group(self, group_repo: GroupRepository):
        result = await group_repo.create_group("g001", "测试群1")
        assert isinstance(result, Group)
        assert result.group_id == "g001"
        assert result.name == "测试群1"

    async def test_batch_create_groups(self, group_repo: GroupRepository):
        groups = [
            {"group_id": "bg001", "name": "批量群1"},
            {"group_id": "bg002", "name": "批量群2"},
        ]
        ok = await group_repo.batch_create_groups(groups)
        assert ok is True
        assert await group_repo.group_exists("bg001")
        assert await group_repo.group_exists("bg002")

    async def test_batch_create_groups_empty(self, group_repo: GroupRepository):
        ok = await group_repo.batch_create_groups([])
        assert ok is True


class TestGroupRepositoryRead:
    """查询相关测试。"""

    async def test_get_group_by_id(self, group_repo: GroupRepository):
        await group_repo.create_group("g100", "查询群")
        result = await group_repo.get_group_by_id("g100")
        assert result is not None
        assert result.name == "查询群"

    async def test_get_group_by_id_not_found(self, group_repo: GroupRepository):
        result = await group_repo.get_group_by_id("nonexistent")
        assert result is None

    async def test_group_exists(self, group_repo: GroupRepository):
        await group_repo.create_group("g101", "存在群")
        assert await group_repo.group_exists("g101") is True
        assert await group_repo.group_exists("no_such") is False

    async def test_find_groups_by_name(self, group_repo: GroupRepository):
        await group_repo.create_group("g200", "精确名称")
        results = await group_repo.find_groups_by_name("精确名称")
        assert len(results) >= 1
        assert any(g.group_id == "g200" for g in results)

    async def test_search_groups_by_name_like(self, group_repo: GroupRepository):
        await group_repo.create_group("g201", "模糊搜索测试群")
        results = await group_repo.search_groups_by_name_like("%模糊搜索%")
        assert any(g.group_id == "g201" for g in results)

    async def test_get_groups_with_name_containing(self, group_repo: GroupRepository):
        await group_repo.create_group("g202", "关键词匹配群")
        results = await group_repo.get_groups_with_name_containing("关键词")
        assert any(g.group_id == "g202" for g in results)

    async def test_get_groups_by_ids(self, group_repo: GroupRepository):
        await group_repo.create_group("g300", "批量查1")
        await group_repo.create_group("g301", "批量查2")
        results = await group_repo.get_groups_by_ids(["g300", "g301", "g999"])
        assert len(results) == 2

    async def test_get_groups_by_ids_empty(self, group_repo: GroupRepository):
        results = await group_repo.get_groups_by_ids([])
        assert results == []

    async def test_get_all_groups_ordered_by_name(self, group_repo: GroupRepository):
        await group_repo.create_group("g400", "A群")
        await group_repo.create_group("g401", "B群")
        results = await group_repo.get_all_groups_ordered_by_name()
        assert len(results) >= 2

    async def test_count_groups(self, group_repo: GroupRepository):
        initial = await group_repo.count_groups()
        await group_repo.create_group("g500", "计数群")
        assert await group_repo.count_groups() == initial + 1


class TestGroupRepositoryUpdate:
    """更新相关测试。"""

    async def test_update_group(self, group_repo: GroupRepository):
        await group_repo.create_group("g600", "旧名称")
        ok = await group_repo.update_group("g600", "新名称")
        assert ok is True
        g = await group_repo.get_group_by_id("g600")
        assert g is not None
        assert g.name == "新名称"

    async def test_update_nonexistent_group(self, group_repo: GroupRepository):
        ok = await group_repo.update_group("no_such", "名称")
        assert ok is False

    async def test_update_or_create_group_create(self, group_repo: GroupRepository):
        result = await group_repo.update_or_create_group("g700", "新建群")
        assert isinstance(result, Group)
        assert result.name == "新建群"

    async def test_update_or_create_group_update(self, group_repo: GroupRepository):
        await group_repo.create_group("g701", "原名")
        result = await group_repo.update_or_create_group("g701", "改名")
        assert result.name == "改名"


class TestGroupRepositoryDelete:
    """删除相关测试。"""

    async def test_delete_group(self, group_repo: GroupRepository):
        await group_repo.create_group("g800", "待删群")
        ok = await group_repo.delete_group("g800")
        assert ok is True
        assert await group_repo.get_group_by_id("g800") is None

    async def test_delete_nonexistent_group(self, group_repo: GroupRepository):
        ok = await group_repo.delete_group("no_such")
        assert ok is False
