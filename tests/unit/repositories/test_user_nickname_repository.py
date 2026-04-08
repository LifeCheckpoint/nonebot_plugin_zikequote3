"""UserNicknameRepository 单元测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from nonebot_plugin_zikequote3.database.models.user_nicknames import UserNickname
from nonebot_plugin_zikequote3.database.repositories.user_nickname_repository import UserNicknameRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed_user(user_repo: UserRepository, qq_id: str):
    """创建前置 user 记录（外键约束）。"""
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)


class TestUserNicknameCreate:
    """创建相关测试。"""

    async def test_add_nickname(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u1")
        result = await user_nickname_repo.add_nickname("un_u1", False, "昵称A")
        assert isinstance(result, UserNickname)
        assert result.qq_id == "un_u1"
        assert result.name == "昵称A"
        assert result.current_using is False

    async def test_add_nickname_current_using(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u2")
        result = await user_nickname_repo.add_nickname("un_u2", True, "当前昵称")
        assert result.current_using is True


class TestUserNicknameRead:
    """查询相关测试。"""

    async def test_get_current_nickname(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u10")
        await user_nickname_repo.add_nickname("un_u10", False, "旧昵称")
        await user_nickname_repo.add_nickname("un_u10", True, "当前昵称")
        result = await user_nickname_repo.get_current_nickname("un_u10")
        assert result is not None
        assert result.name == "当前昵称"
        assert result.current_using is True

    async def test_get_current_nickname_none(
        self, user_nickname_repo: UserNicknameRepository,
    ):
        result = await user_nickname_repo.get_current_nickname("nonexistent")
        assert result is None

    async def test_get_all_nicknames(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u11")
        await user_nickname_repo.add_nickname("un_u11", False, "昵称1")
        await user_nickname_repo.add_nickname("un_u11", False, "昵称2")
        results = await user_nickname_repo.get_all_nicknames("un_u11")
        assert len(results) == 2
        names = {r.name for r in results}
        assert "昵称1" in names
        assert "昵称2" in names

    async def test_get_all_nicknames_empty(
        self, user_nickname_repo: UserNicknameRepository,
    ):
        results = await user_nickname_repo.get_all_nicknames("no_such_user")
        assert len(results) == 0

    async def test_search_user_by_nickname(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u12")
        await user_nickname_repo.add_nickname("un_u12", False, "测试搜索昵称")
        results = await user_nickname_repo.search_user_by_nickname("%搜索%")
        assert len(results) >= 1
        assert any(r.name == "测试搜索昵称" for r in results)

    async def test_search_user_by_nickname_no_match(
        self, user_nickname_repo: UserNicknameRepository,
    ):
        results = await user_nickname_repo.search_user_by_nickname("%不存在的模式%")
        assert len(results) == 0


class TestUserNicknameSetCurrent:
    """current_using 切换逻辑测试。"""

    async def test_set_current_nickname_existing(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u20")
        await user_nickname_repo.add_nickname("un_u20", True, "旧当前")
        await user_nickname_repo.add_nickname("un_u20", False, "新目标")

        ok = await user_nickname_repo.set_current_nickname("un_u20", "新目标")
        assert ok is True

        current = await user_nickname_repo.get_current_nickname("un_u20")
        assert current is not None
        assert current.name == "新目标"

        # 旧的应该被取消
        all_nicks = await user_nickname_repo.get_all_nicknames("un_u20")
        old = [n for n in all_nicks if n.name == "旧当前"]
        assert len(old) == 1
        assert old[0].current_using is False

    async def test_set_current_nickname_creates_if_not_exists(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u21")
        ok = await user_nickname_repo.set_current_nickname("un_u21", "全新昵称")
        assert ok is True

        current = await user_nickname_repo.get_current_nickname("un_u21")
        assert current is not None
        assert current.name == "全新昵称"
        assert current.current_using is True

    async def test_set_current_clears_all_previous(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u22")
        await user_nickname_repo.add_nickname("un_u22", True, "A")
        await user_nickname_repo.add_nickname("un_u22", False, "B")
        await user_nickname_repo.add_nickname("un_u22", False, "C")

        await user_nickname_repo.set_current_nickname("un_u22", "C")

        all_nicks = await user_nickname_repo.get_all_nicknames("un_u22")
        current_count = sum(1 for n in all_nicks if n.current_using)
        assert current_count == 1
        current = [n for n in all_nicks if n.current_using][0]
        assert current.name == "C"

    async def test_unique_current_nickname_is_enforced_by_database(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
        async_session,
    ):
        await _seed_user(user_repo, "un_u23")
        await user_nickname_repo.add_nickname("un_u23", True, "A")

        with pytest.raises(IntegrityError):
            await user_nickname_repo.add_nickname("un_u23", True, "B")
        await async_session.rollback()


class TestUserNicknameDelete:
    """删除相关测试。"""

    async def test_remove_nickname(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u30")
        await user_nickname_repo.add_nickname("un_u30", False, "待删除")
        ok = await user_nickname_repo.remove_nickname("un_u30", "待删除")
        assert ok is True
        all_nicks = await user_nickname_repo.get_all_nicknames("un_u30")
        assert all(n.name != "待删除" for n in all_nicks)

    async def test_remove_nonexistent_nickname(
        self, user_nickname_repo: UserNicknameRepository,
    ):
        ok = await user_nickname_repo.remove_nickname("no_user", "no_nick")
        assert ok is False

    async def test_clear_user_nicknames(
        self, user_nickname_repo: UserNicknameRepository, user_repo: UserRepository,
    ):
        await _seed_user(user_repo, "un_u31")
        await user_nickname_repo.add_nickname("un_u31", False, "N1")
        await user_nickname_repo.add_nickname("un_u31", True, "N2")
        ok = await user_nickname_repo.clear_user_nicknames("un_u31")
        assert ok is True
        all_nicks = await user_nickname_repo.get_all_nicknames("un_u31")
        assert len(all_nicks) == 0
