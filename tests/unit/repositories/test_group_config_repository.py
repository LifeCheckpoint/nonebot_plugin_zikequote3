"""GroupConfigRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.group_configs import GroupConfigs
from nonebot_plugin_zikequote3.database.repositories.group_config_repository import GroupConfigRepository
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository


pytestmark = pytest.mark.anyio


async def _seed_group(group_repo: GroupRepository, group_id: str):
    """确保 group 存在（外键约束）。"""
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"cfg_group_{group_id}")


class TestGroupConfigCreate:
    """创建相关测试。"""

    async def test_create_group_config(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg001")
        result = await group_config_repo.create_group_config("cg001", "[section]\nkey=1")
        assert isinstance(result, GroupConfigs)
        assert result.group_id == "cg001"
        assert result.toml_config == "[section]\nkey=1"

    async def test_batch_create_group_configs(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg010")
        await _seed_group(group_repo, "cg011")
        ok = await group_config_repo.batch_create_group_configs([
            {"group_id": "cg010", "toml_config": "a=1"},
            {"group_id": "cg011", "toml_config": "b=2"},
        ])
        assert ok is True
        assert await group_config_repo.group_config_exists("cg010")
        assert await group_config_repo.group_config_exists("cg011")

    async def test_batch_create_empty(self, group_config_repo: GroupConfigRepository):
        ok = await group_config_repo.batch_create_group_configs([])
        assert ok is True


class TestGroupConfigRead:
    """查询相关测试。"""

    async def test_get_group_config_by_id(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg100")
        await group_config_repo.create_group_config("cg100", "x=1")
        result = await group_config_repo.get_group_config_by_id("cg100")
        assert result is not None
        assert result.toml_config == "x=1"

    async def test_get_group_config_by_id_not_found(self, group_config_repo: GroupConfigRepository):
        result = await group_config_repo.get_group_config_by_id("nonexistent")
        assert result is None

    async def test_group_config_exists(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg101")
        await group_config_repo.create_group_config("cg101", "y=2")
        assert await group_config_repo.group_config_exists("cg101") is True
        assert await group_config_repo.group_config_exists("no_such") is False

    async def test_get_toml_config_by_group_id(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg102")
        await group_config_repo.create_group_config("cg102", "z=3")
        toml = await group_config_repo.get_toml_config_by_group_id("cg102")
        assert toml == "z=3"

    async def test_get_toml_config_by_group_id_not_found(self, group_config_repo: GroupConfigRepository):
        toml = await group_config_repo.get_toml_config_by_group_id("no_such")
        assert toml is None

    async def test_get_group_configs_by_ids(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg200")
        await _seed_group(group_repo, "cg201")
        await group_config_repo.create_group_config("cg200", "a=1")
        await group_config_repo.create_group_config("cg201", "b=2")
        results = await group_config_repo.get_group_configs_by_ids(["cg200", "cg201", "cg999"])
        assert len(results) == 2

    async def test_get_group_configs_by_ids_empty(self, group_config_repo: GroupConfigRepository):
        results = await group_config_repo.get_group_configs_by_ids([])
        assert results == []

    async def test_get_all_group_configs(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg300")
        await group_config_repo.create_group_config("cg300", "all=1")
        results = await group_config_repo.get_all_group_configs()
        assert any(c.group_id == "cg300" for c in results)

    async def test_count_group_configs(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        initial = await group_config_repo.count_group_configs()
        await _seed_group(group_repo, "cg400")
        await group_config_repo.create_group_config("cg400", "cnt=1")
        assert await group_config_repo.count_group_configs() == initial + 1


class TestGroupConfigUpdate:
    """更新相关测试。"""

    async def test_update_group_config(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg500")
        await group_config_repo.create_group_config("cg500", "old=1")
        ok = await group_config_repo.update_group_config("cg500", "new=2")
        assert ok is True
        cfg = await group_config_repo.get_group_config_by_id("cg500")
        assert cfg is not None
        assert cfg.toml_config == "new=2"

    async def test_update_nonexistent_config(self, group_config_repo: GroupConfigRepository):
        ok = await group_config_repo.update_group_config("no_such", "x=1")
        assert ok is False

    async def test_update_or_create_group_config_create(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg600")
        result = await group_config_repo.update_or_create_group_config("cg600", "created=1")
        assert isinstance(result, GroupConfigs)
        assert result.toml_config == "created=1"

    async def test_update_or_create_group_config_update(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg601")
        await group_config_repo.create_group_config("cg601", "orig=1")
        result = await group_config_repo.update_or_create_group_config("cg601", "updated=2")
        assert result.toml_config == "updated=2"

    async def test_set_toml_config(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg700")
        result = await group_config_repo.set_toml_config("cg700", "set=1")
        assert isinstance(result, GroupConfigs)
        assert result.toml_config == "set=1"


class TestGroupConfigDelete:
    """删除相关测试。"""

    async def test_delete_group_config(
        self, group_config_repo: GroupConfigRepository, group_repo: GroupRepository,
    ):
        await _seed_group(group_repo, "cg800")
        await group_config_repo.create_group_config("cg800", "del=1")
        ok = await group_config_repo.delete_group_config("cg800")
        assert ok is True
        assert await group_config_repo.get_group_config_by_id("cg800") is None

    async def test_delete_nonexistent_config(self, group_config_repo: GroupConfigRepository):
        ok = await group_config_repo.delete_group_config("no_such")
        assert ok is False
