"""
UserService 单元测试。

使用 mock Repository 验证方法调用和返回值，覆盖正常流程和异常路径。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientTimeout

from nonebot_plugin_zikequote3.database.models.group_nicknames import GroupNickname
from nonebot_plugin_zikequote3.database.models.user_nicknames import UserNickname
from nonebot_plugin_zikequote3.database.models.users import User
from nonebot_plugin_zikequote3.services.new.user_service import UserService


# ================================================================== #
#  用户基础操作
# ================================================================== #


class TestGetOrCreateUser:
    """测试 get_or_create_user 方法。"""

    async def test_returns_existing_user(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        existing = User(qq_id="12345", avatar=None)
        mock_user_repo.get_by_qq_id.return_value = existing

        result = await user_service.get_or_create_user("12345")

        assert result == existing
        mock_user_repo.get_by_qq_id.assert_awaited_once_with("12345")
        mock_user_repo.create_user.assert_not_awaited()

    async def test_creates_new_user_when_not_exists(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        mock_user_repo.get_by_qq_id.return_value = None
        created = User(qq_id="99999", avatar=None)
        mock_user_repo.create_user.return_value = created

        result = await user_service.get_or_create_user("99999")

        assert result == created
        mock_user_repo.create_user.assert_awaited_once_with("99999")


class TestGetUserInfo:
    """测试 get_user_info 方法。"""

    async def test_returns_user(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        user = User(qq_id="12345", avatar=b"img")
        mock_user_repo.get_by_qq_id.return_value = user

        result = await user_service.get_user_info("12345")

        assert result == user

    async def test_returns_none_when_not_found(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        mock_user_repo.get_by_qq_id.return_value = None

        result = await user_service.get_user_info("00000")

        assert result is None


class TestUserExists:
    """测试 user_exists 方法。"""

    async def test_returns_true(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        mock_user_repo.user_exists.return_value = True
        assert await user_service.user_exists("12345") is True

    async def test_returns_false(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        mock_user_repo.user_exists.return_value = False
        assert await user_service.user_exists("00000") is False


# ================================================================== #
#  昵称 / 群名片查询
# ================================================================== #


class TestGetCurrentNickname:
    """测试 get_current_nickname 方法。"""

    async def test_returns_name(
        self, user_service: UserService, mock_user_nickname_repo: AsyncMock
    ):
        nick = UserNickname(qq_id="12345", current_using=True, name="Alice")
        mock_user_nickname_repo.get_current_nickname.return_value = nick

        result = await user_service.get_current_nickname("12345")

        assert result == "Alice"

    async def test_returns_none(
        self, user_service: UserService, mock_user_nickname_repo: AsyncMock
    ):
        mock_user_nickname_repo.get_current_nickname.return_value = None

        result = await user_service.get_current_nickname("12345")

        assert result is None


class TestGetDisplayName:
    """测试 get_display_name 方法。"""

    async def test_prefers_group_card(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_group_nickname_repo.get_current_group_nickname.return_value = "CardName"

        result = await user_service.get_display_name("12345", group_id="G1")

        assert result == "CardName"
        # 不应查询昵称
        mock_user_nickname_repo.get_current_nickname.assert_not_awaited()

    async def test_falls_back_to_nickname(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_group_nickname_repo.get_current_group_nickname.return_value = None
        nick = UserNickname(qq_id="12345", current_using=True, name="Nick")
        mock_user_nickname_repo.get_current_nickname.return_value = nick

        result = await user_service.get_display_name("12345", group_id="G1")

        assert result == "Nick"

    async def test_falls_back_to_qq_id(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_group_nickname_repo.get_current_group_nickname.return_value = None
        mock_user_nickname_repo.get_current_nickname.return_value = None

        result = await user_service.get_display_name("12345", group_id="G1")

        assert result == "12345"

    async def test_no_group_id_skips_card(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        nick = UserNickname(qq_id="12345", current_using=True, name="Nick")
        mock_user_nickname_repo.get_current_nickname.return_value = nick

        result = await user_service.get_display_name("12345")

        assert result == "Nick"
        mock_group_nickname_repo.get_current_group_nickname.assert_not_awaited()


# ================================================================== #
#  昵称 / 群名片同步
# ================================================================== #


class TestSyncNickname:
    """测试 sync_nickname 方法。"""

    async def test_updates_when_different(
        self, user_service: UserService, mock_user_nickname_repo: AsyncMock
    ):
        old = UserNickname(qq_id="12345", current_using=True, name="OldNick")
        mock_user_nickname_repo.get_current_nickname.return_value = old

        await user_service.sync_nickname("12345", "NewNick")

        mock_user_nickname_repo.set_current_nickname.assert_awaited_once_with(
            "12345", "NewNick"
        )

    async def test_skips_when_same(
        self, user_service: UserService, mock_user_nickname_repo: AsyncMock
    ):
        old = UserNickname(qq_id="12345", current_using=True, name="Same")
        mock_user_nickname_repo.get_current_nickname.return_value = old

        await user_service.sync_nickname("12345", "Same")

        mock_user_nickname_repo.set_current_nickname.assert_not_awaited()

    async def test_creates_when_none(
        self, user_service: UserService, mock_user_nickname_repo: AsyncMock
    ):
        mock_user_nickname_repo.get_current_nickname.return_value = None

        await user_service.sync_nickname("12345", "Brand")

        mock_user_nickname_repo.set_current_nickname.assert_awaited_once_with(
            "12345", "Brand"
        )


class TestSyncGroupCard:
    """测试 sync_group_card 方法。"""

    async def test_updates_when_different(
        self, user_service: UserService, mock_group_nickname_repo: AsyncMock
    ):
        mock_group_nickname_repo.get_current_group_nickname.return_value = "OldCard"

        await user_service.sync_group_card("12345", "G1", "NewCard")

        mock_group_nickname_repo.set_current_group_nickname.assert_awaited_once_with(
            "12345", "G1", "NewCard"
        )

    async def test_skips_when_same(
        self, user_service: UserService, mock_group_nickname_repo: AsyncMock
    ):
        mock_group_nickname_repo.get_current_group_nickname.return_value = "Same"

        await user_service.sync_group_card("12345", "G1", "Same")

        mock_group_nickname_repo.set_current_group_nickname.assert_not_awaited()


# ================================================================== #
#  用户搜索
# ================================================================== #


class TestSearchUsersByName:
    """测试 search_users_by_name 方法。"""

    async def test_finds_by_current_card_first(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
    ):
        mock_group_nickname_repo.search_users_by_nickname_in_group.return_value = [
            GroupNickname(qq_id="111", group_id="G1", current_using=True, name="Alice"),
        ]

        result = await user_service.search_users_by_name("Alice", group_id="G1")

        assert result == ["111"]

    async def test_falls_back_to_current_nickname(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        # 群名片无匹配
        mock_group_nickname_repo.search_users_by_nickname_in_group.return_value = []
        # 昵称有匹配
        mock_user_nickname_repo.search_user_by_nickname.return_value = [
            UserNickname(qq_id="222", current_using=True, name="Bob"),
        ]

        result = await user_service.search_users_by_name("Bob", group_id="G1")

        assert result == ["222"]

    async def test_returns_empty_when_no_match(
        self,
        user_service: UserService,
        mock_group_nickname_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_group_nickname_repo.search_users_by_nickname_in_group.return_value = []
        mock_user_nickname_repo.search_user_by_nickname.return_value = []

        result = await user_service.search_users_by_name("Nobody", group_id="G1")

        assert result == []

    async def test_fuzzy_search(
        self,
        user_service: UserService,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_user_nickname_repo.search_user_by_nickname.return_value = [
            UserNickname(qq_id="333", current_using=True, name="AliceBob"),
        ]

        result = await user_service.search_users_by_name("Alice", exact=False)

        assert result == ["333"]
        mock_user_nickname_repo.search_user_by_nickname.assert_awaited_once_with(
            name_pattern="%Alice%"
        )


# ================================================================== #
#  用户解析辅助
# ================================================================== #


class TestResolveUser:
    """测试 resolve_user 方法。"""

    async def test_empty_key_returns_empty(self, user_service: UserService):
        result = await user_service.resolve_user("")
        assert result == []

    async def test_numeric_key_returns_as_qq(self, user_service: UserService):
        result = await user_service.resolve_user("12345")
        assert result == ["12345"]

    async def test_text_key_searches_by_name(
        self,
        user_service: UserService,
        mock_user_nickname_repo: AsyncMock,
    ):
        mock_user_nickname_repo.search_user_by_nickname.return_value = [
            UserNickname(qq_id="444", current_using=True, name="Charlie"),
        ]

        result = await user_service.resolve_user("Charlie")

        assert result == ["444"]


# ================================================================== #
#  头像管理
# ================================================================== #


class TestFetchAvatar:
    """测试 fetch_avatar 方法。"""

    async def test_fetches_from_cdn(self, user_service: UserService):
        mock_resp = AsyncMock()
        mock_resp.read.return_value = b"avatar_data"
        mock_resp.raise_for_status = MagicMock()

        # 内层 async context manager: session.get(url)
        # aiohttp 的 session.get() 是同步调用，返回异步上下文管理器
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_resp

        # session 对象 —— get 必须是同步方法（MagicMock）
        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_cm

        # 外层 async context manager: aiohttp.ClientSession(...)
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_session

        with patch(
            "nonebot_plugin_zikequote3.services.new.user_service.aiohttp"
        ) as mock_aiohttp:
            mock_aiohttp.ClientTimeout = ClientTimeout
            mock_aiohttp.ClientSession.return_value = mock_client_cm

            result = await user_service.fetch_avatar("12345")

            assert result == b"avatar_data"
            mock_resp.raise_for_status.assert_called_once()


class TestGetAvatar:
    """测试 get_avatar 方法。"""

    async def test_returns_cached_avatar(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        user = User(qq_id="12345", avatar=b"cached")
        mock_user_repo.get_by_qq_id.return_value = user

        result = await user_service.get_avatar("12345")

        assert result == b"cached"

    async def test_returns_none_on_fetch_failure(
        self, user_service: UserService, mock_user_repo: AsyncMock
    ):
        mock_user_repo.get_by_qq_id.return_value = User(qq_id="12345", avatar=None)

        with patch.object(user_service, "fetch_avatar", side_effect=Exception("network")):
            result = await user_service.get_avatar("12345")

        assert result is None
