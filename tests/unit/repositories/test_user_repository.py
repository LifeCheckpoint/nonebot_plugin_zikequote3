"""UserRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.users import User
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


class TestUserRepositoryCreate:
    """创建相关测试。"""

    async def test_create_user(self, user_repo: UserRepository):
        result = await user_repo.create_user("10001")
        assert isinstance(result, User)
        assert result.qq_id == "10001"
        assert result.avatar is None

    async def test_create_user_with_avatar(self, user_repo: UserRepository):
        avatar_data = b"\x89PNG_FAKE"
        result = await user_repo.create_user("10002", avatar=avatar_data)
        assert result.qq_id == "10002"
        assert result.avatar == avatar_data

    async def test_batch_create_users(self, user_repo: UserRepository):
        users = [{"qq_id": "20001"}, {"qq_id": "20002", "avatar": b"img"}]
        ok = await user_repo.batch_create_users(users)
        assert ok is True
        assert await user_repo.user_exists("20001")
        assert await user_repo.user_exists("20002")

    async def test_batch_create_users_empty(self, user_repo: UserRepository):
        ok = await user_repo.batch_create_users([])
        assert ok is True


class TestUserRepositoryRead:
    """查询相关测试。"""

    async def test_get_by_qq_id(self, user_repo: UserRepository):
        await user_repo.create_user("30001")
        result = await user_repo.get_by_qq_id("30001")
        assert result is not None
        assert result.qq_id == "30001"

    async def test_get_by_qq_id_not_found(self, user_repo: UserRepository):
        result = await user_repo.get_by_qq_id("nonexistent")
        assert result is None

    async def test_user_exists(self, user_repo: UserRepository):
        await user_repo.create_user("30002")
        assert await user_repo.user_exists("30002") is True
        assert await user_repo.user_exists("no_such_user") is False

    async def test_get_users_by_qq_ids(self, user_repo: UserRepository):
        await user_repo.create_user("40001")
        await user_repo.create_user("40002")
        results = await user_repo.get_users_by_qq_ids(["40001", "40002", "40003"])
        assert len(results) == 2
        ids = {u.qq_id for u in results}
        assert "40001" in ids
        assert "40002" in ids

    async def test_get_users_by_qq_ids_empty(self, user_repo: UserRepository):
        results = await user_repo.get_users_by_qq_ids([])
        assert results == []

    async def test_get_users_with_avatar(self, user_repo: UserRepository):
        await user_repo.create_user("50001", avatar=b"avatar")
        await user_repo.create_user("50002")
        with_avatar = await user_repo.get_users_with_avatar()
        ids = {u.qq_id for u in with_avatar}
        assert "50001" in ids
        assert "50002" not in ids

    async def test_get_users_without_avatar(self, user_repo: UserRepository):
        await user_repo.create_user("50003")
        await user_repo.create_user("50004", avatar=b"data")
        without = await user_repo.get_users_without_avatar()
        ids = {u.qq_id for u in without}
        assert "50003" in ids
        assert "50004" not in ids

    async def test_count_users(self, user_repo: UserRepository):
        initial = await user_repo.count_users()
        await user_repo.create_user("60001")
        assert await user_repo.count_users() == initial + 1

    async def test_list_all(self, user_repo: UserRepository):
        await user_repo.create_user("70001")
        all_users = await user_repo.list_all(limit=1000)
        assert any(u.qq_id == "70001" for u in all_users)


class TestUserRepositoryUpdate:
    """更新相关测试。"""

    async def test_update_user_avatar(self, user_repo: UserRepository):
        await user_repo.create_user("80001")
        ok = await user_repo.update_user("80001", avatar=b"new_avatar")
        assert ok is True
        user = await user_repo.get_by_qq_id("80001")
        assert user is not None
        assert user.avatar == b"new_avatar"

    async def test_update_user_no_change(self, user_repo: UserRepository):
        await user_repo.create_user("80002")
        ok = await user_repo.update_user("80002")
        assert ok is True

    async def test_update_nonexistent_user(self, user_repo: UserRepository):
        ok = await user_repo.update_user("no_such_user", avatar=b"data")
        assert ok is False


class TestUserRepositoryDelete:
    """删除相关测试。"""

    async def test_delete_user(self, user_repo: UserRepository):
        await user_repo.create_user("90001")
        ok = await user_repo.delete_user("90001")
        assert ok is True
        assert await user_repo.get_by_qq_id("90001") is None

    async def test_delete_nonexistent_user(self, user_repo: UserRepository):
        ok = await user_repo.delete_user("no_such_user")
        assert ok is False
