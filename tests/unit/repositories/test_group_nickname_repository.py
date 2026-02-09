"""GroupNicknameRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.group_nicknames import GroupNickname
from nonebot_plugin_zikequote3.database.repositories.group_nickname_repository import GroupNicknameRepository
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed(group_repo: GroupRepository, user_repo: UserRepository, group_id: str, qq_id: str):
    """创建前置 group 和 user 记录（外键约束）。"""
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"group_{group_id}")
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)


class TestGroupNicknameCreate:
    """创建相关测试。"""

    async def test_add_group_nickname(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g1", "gn_u1")
        result = await group_nickname_repo.add_group_nickname("gn_u1", "gn_g1", False, "群名片A")
        assert isinstance(result, GroupNickname)
        assert result.qq_id == "gn_u1"
        assert result.group_id == "gn_g1"
        assert result.name == "群名片A"
        assert result.current_using is False

    async def test_add_group_nickname_current(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g2", "gn_u2")
        result = await group_nickname_repo.add_group_nickname("gn_u2", "gn_g2", True, "当前名片")
        assert result.current_using is True


class TestGroupNicknameRead:
    """查询相关测试。"""

    async def test_get_current_group_nickname(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g10", "gn_u10")
        await group_nickname_repo.add_group_nickname("gn_u10", "gn_g10", False, "旧名片")
        await group_nickname_repo.add_group_nickname("gn_u10", "gn_g10", True, "当前名片")
        result = await group_nickname_repo.get_current_group_nickname("gn_u10", "gn_g10")
        assert result == "当前名片"

    async def test_get_current_group_nickname_none(
        self, group_nickname_repo: GroupNicknameRepository,
    ):
        result = await group_nickname_repo.get_current_group_nickname("no_u", "no_g")
        assert result is None

    async def test_get_all_group_nicknames(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g11", "gn_u11")
        await group_nickname_repo.add_group_nickname("gn_u11", "gn_g11", False, "名片1")
        await group_nickname_repo.add_group_nickname("gn_u11", "gn_g11", False, "名片2")
        results = await group_nickname_repo.get_all_group_nicknames("gn_u11", "gn_g11")
        assert len(results) == 2

    async def test_get_nicknames_by_group(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g12", "gn_u12a")
        await _seed(group_repo, user_repo, "gn_g12", "gn_u12b")
        await group_nickname_repo.add_group_nickname("gn_u12a", "gn_g12", False, "A名片")
        await group_nickname_repo.add_group_nickname("gn_u12b", "gn_g12", False, "B名片")
        results = await group_nickname_repo.get_nicknames_by_group("gn_g12")
        assert len(results) == 2

    async def test_get_user_all_group_nicknames(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g13a", "gn_u13")
        await _seed(group_repo, user_repo, "gn_g13b", "gn_u13")
        await group_nickname_repo.add_group_nickname("gn_u13", "gn_g13a", False, "群A名片")
        await group_nickname_repo.add_group_nickname("gn_u13", "gn_g13b", False, "群B名片")
        results = await group_nickname_repo.get_user_all_group_nicknames("gn_u13")
        assert len(results) == 2

    async def test_search_users_by_nickname_in_group(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g14", "gn_u14")
        await group_nickname_repo.add_group_nickname("gn_u14", "gn_g14", False, "搜索目标名片")
        results = await group_nickname_repo.search_users_by_nickname_in_group("%搜索%", "gn_g14")
        assert len(results) >= 1
        assert any(r.name == "搜索目标名片" for r in results)

    async def test_search_no_match(
        self, group_nickname_repo: GroupNicknameRepository,
    ):
        results = await group_nickname_repo.search_users_by_nickname_in_group("%不存在%", "no_g")
        assert len(results) == 0

    async def test_get_group_nickname_statistics(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g15", "gn_u15a")
        await _seed(group_repo, user_repo, "gn_g15", "gn_u15b")
        await group_nickname_repo.add_group_nickname("gn_u15a", "gn_g15", True, "名片X")
        await group_nickname_repo.add_group_nickname("gn_u15a", "gn_g15", False, "名片Y")
        await group_nickname_repo.add_group_nickname("gn_u15b", "gn_g15", True, "名片Z")
        stats = await group_nickname_repo.get_group_nickname_statistics("gn_g15")
        assert stats["total_nicknames"] == 3
        assert stats["users_with_nicknames"] == 2
        assert stats["current_nicknames"] == 2

    async def test_get_group_nickname_statistics_empty(
        self, group_nickname_repo: GroupNicknameRepository,
    ):
        stats = await group_nickname_repo.get_group_nickname_statistics("empty_group")
        assert stats["total_nicknames"] == 0
        assert stats["users_with_nicknames"] == 0
        assert stats["current_nicknames"] == 0


class TestGroupNicknameSetCurrent:
    """current_using 切换逻辑测试。"""

    async def test_set_current_existing(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g20", "gn_u20")
        await group_nickname_repo.add_group_nickname("gn_u20", "gn_g20", True, "旧当前")
        await group_nickname_repo.add_group_nickname("gn_u20", "gn_g20", False, "新目标")

        ok = await group_nickname_repo.set_current_group_nickname("gn_u20", "gn_g20", "新目标")
        assert ok is True

        current = await group_nickname_repo.get_current_group_nickname("gn_u20", "gn_g20")
        assert current == "新目标"

    async def test_set_current_creates_if_not_exists(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g21", "gn_u21")
        ok = await group_nickname_repo.set_current_group_nickname("gn_u21", "gn_g21", "全新名片")
        assert ok is True

        current = await group_nickname_repo.get_current_group_nickname("gn_u21", "gn_g21")
        assert current == "全新名片"

    async def test_set_current_clears_all_previous(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g22", "gn_u22")
        await group_nickname_repo.add_group_nickname("gn_u22", "gn_g22", True, "A")
        await group_nickname_repo.add_group_nickname("gn_u22", "gn_g22", True, "B")
        await group_nickname_repo.add_group_nickname("gn_u22", "gn_g22", False, "C")

        await group_nickname_repo.set_current_group_nickname("gn_u22", "gn_g22", "C")

        all_nicks = await group_nickname_repo.get_all_group_nicknames("gn_u22", "gn_g22")
        current_count = sum(1 for n in all_nicks if n.current_using)
        assert current_count == 1
        current = [n for n in all_nicks if n.current_using][0]
        assert current.name == "C"


class TestGroupNicknameDelete:
    """删除相关测试。"""

    async def test_remove_group_nickname(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g30", "gn_u30")
        await group_nickname_repo.add_group_nickname("gn_u30", "gn_g30", False, "待删除")
        ok = await group_nickname_repo.remove_group_nickname("gn_u30", "gn_g30", "待删除")
        assert ok is True

    async def test_remove_nonexistent(
        self, group_nickname_repo: GroupNicknameRepository,
    ):
        ok = await group_nickname_repo.remove_group_nickname("no_u", "no_g", "no_n")
        assert ok is False

    async def test_clear_user_group_nicknames(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g31", "gn_u31")
        await group_nickname_repo.add_group_nickname("gn_u31", "gn_g31", False, "N1")
        await group_nickname_repo.add_group_nickname("gn_u31", "gn_g31", True, "N2")
        ok = await group_nickname_repo.clear_user_group_nicknames("gn_u31", "gn_g31")
        assert ok is True
        all_nicks = await group_nickname_repo.get_all_group_nicknames("gn_u31", "gn_g31")
        assert len(all_nicks) == 0

    async def test_clear_group_all_nicknames(
        self, group_nickname_repo: GroupNicknameRepository,
        group_repo: GroupRepository, user_repo: UserRepository,
    ):
        await _seed(group_repo, user_repo, "gn_g32", "gn_u32a")
        await _seed(group_repo, user_repo, "gn_g32", "gn_u32b")
        await group_nickname_repo.add_group_nickname("gn_u32a", "gn_g32", False, "X")
        await group_nickname_repo.add_group_nickname("gn_u32b", "gn_g32", False, "Y")
        ok = await group_nickname_repo.clear_group_all_nicknames("gn_g32")
        assert ok is True
        results = await group_nickname_repo.get_nicknames_by_group("gn_g32")
        assert len(results) == 0
