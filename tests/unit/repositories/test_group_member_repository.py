"""GroupMemberRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.group_members import GroupMember
from nonebot_plugin_zikequote3.database.repositories.group_member_repository import GroupMemberRepository
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed_group_and_user(group_repo, user_repo, group_id, qq_id):
    """创建前置的 group 和 user 记录（外键约束）。"""
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"group_{group_id}")
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)


class TestGroupMemberCreate:
    """创建相关测试。"""

    async def test_create_group_member(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g1", "gm_u1")
        result = await group_member_repo.create_group_member("gm_g1", "gm_u1")
        assert isinstance(result, GroupMember)
        assert result.group_id == "gm_g1"
        assert result.qq_id == "gm_u1"

    async def test_update_or_create_member_new(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g2", "gm_u2")
        result = await group_member_repo.update_or_create_member("gm_g2", "gm_u2")
        assert result.group_id == "gm_g2"

    async def test_update_or_create_member_existing(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g3", "gm_u3")
        await group_member_repo.create_group_member("gm_g3", "gm_u3")
        result = await group_member_repo.update_or_create_member("gm_g3", "gm_u3")
        assert result.group_id == "gm_g3"


class TestGroupMemberRead:
    """查询相关测试。"""

    async def test_get_group_member(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g10", "gm_u10")
        await group_member_repo.create_group_member("gm_g10", "gm_u10")
        result = await group_member_repo.get_group_member("gm_g10", "gm_u10")
        assert result is not None
        assert result.qq_id == "gm_u10"

    async def test_get_group_member_not_found(self, group_member_repo: GroupMemberRepository):
        result = await group_member_repo.get_group_member("no_g", "no_u")
        assert result is None

    async def test_group_member_exists(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g11", "gm_u11")
        await group_member_repo.create_group_member("gm_g11", "gm_u11")
        assert await group_member_repo.group_member_exists("gm_g11", "gm_u11") is True
        assert await group_member_repo.group_member_exists("gm_g11", "no_u") is False

    async def test_is_group_member_exists_alias(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g12", "gm_u12")
        await group_member_repo.create_group_member("gm_g12", "gm_u12")
        assert await group_member_repo.is_group_member_exists("gm_g12", "gm_u12") is True

    async def test_get_members_by_group(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g20", "gm_u20")
        await _seed_group_and_user(group_repo, user_repo, "gm_g20", "gm_u21")
        await group_member_repo.create_group_member("gm_g20", "gm_u20")
        await group_member_repo.create_group_member("gm_g20", "gm_u21")
        members = await group_member_repo.get_members_by_group("gm_g20")
        assert len(members) == 2

    async def test_get_groups_by_user(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g30", "gm_u30")
        await _seed_group_and_user(group_repo, user_repo, "gm_g31", "gm_u30")
        await group_member_repo.create_group_member("gm_g30", "gm_u30")
        await group_member_repo.create_group_member("gm_g31", "gm_u30")
        groups = await group_member_repo.get_groups_by_user("gm_u30")
        assert len(groups) == 2

    async def test_count_members_by_group(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g40", "gm_u40")
        await group_member_repo.create_group_member("gm_g40", "gm_u40")
        count = await group_member_repo.count_members_by_group("gm_g40")
        assert count >= 1

    async def test_count_groups_by_user(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g50", "gm_u50")
        await group_member_repo.create_group_member("gm_g50", "gm_u50")
        count = await group_member_repo.count_groups_by_user("gm_u50")
        assert count >= 1


class TestGroupMemberDelete:
    """删除相关测试。"""

    async def test_delete_group_member(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g60", "gm_u60")
        await group_member_repo.create_group_member("gm_g60", "gm_u60")
        ok = await group_member_repo.delete_group_member("gm_g60", "gm_u60")
        assert ok is True
        assert await group_member_repo.get_group_member("gm_g60", "gm_u60") is None

    async def test_delete_nonexistent_member(self, group_member_repo: GroupMemberRepository):
        ok = await group_member_repo.delete_group_member("no_g", "no_u")
        assert ok is False

    async def test_delete_all_members_by_group(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g70", "gm_u70")
        await _seed_group_and_user(group_repo, user_repo, "gm_g70", "gm_u71")
        await group_member_repo.create_group_member("gm_g70", "gm_u70")
        await group_member_repo.create_group_member("gm_g70", "gm_u71")
        await group_member_repo.delete_all_members_by_group("gm_g70")
        members = await group_member_repo.get_members_by_group("gm_g70")
        assert len(members) == 0

    async def test_delete_all_groups_by_user(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g80", "gm_u80")
        await _seed_group_and_user(group_repo, user_repo, "gm_g81", "gm_u80")
        await group_member_repo.create_group_member("gm_g80", "gm_u80")
        await group_member_repo.create_group_member("gm_g81", "gm_u80")
        await group_member_repo.delete_all_groups_by_user("gm_u80")
        groups = await group_member_repo.get_groups_by_user("gm_u80")
        assert len(groups) == 0


class TestGroupMemberBatch:
    """批量操作测试。"""

    async def test_batch_add_members(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_g90", "gm_u90")
        await _seed_group_and_user(group_repo, user_repo, "gm_g90", "gm_u91")
        ok = await group_member_repo.batch_add_members("gm_g90", ["gm_u90", "gm_u91"])
        assert ok is True
        members = await group_member_repo.get_members_by_group("gm_g90")
        assert len(members) == 2

    async def test_batch_add_members_empty(self, group_member_repo: GroupMemberRepository):
        ok = await group_member_repo.batch_add_members("gm_g90", [])
        assert ok is True

    async def test_batch_remove_members(
        self, group_member_repo: GroupMemberRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed_group_and_user(group_repo, user_repo, "gm_ga0", "gm_ua0")
        await _seed_group_and_user(group_repo, user_repo, "gm_ga0", "gm_ua1")
        await group_member_repo.batch_add_members("gm_ga0", ["gm_ua0", "gm_ua1"])
        ok = await group_member_repo.batch_remove_members("gm_ga0", ["gm_ua0"])
        assert ok is True
        members = await group_member_repo.get_members_by_group("gm_ga0")
        ids = {m.qq_id for m in members}
        assert "gm_ua0" not in ids
        assert "gm_ua1" in ids
