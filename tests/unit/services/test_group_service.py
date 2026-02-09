"""
GroupService 单元测试。

使用 mock Repository 验证方法调用和返回值，覆盖正常流程和异常路径。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.group_members import GroupMember
from nonebot_plugin_zikequote3.database.models.group_nicknames import GroupNickname
from nonebot_plugin_zikequote3.database.models.groups import Group
from nonebot_plugin_zikequote3.services.new.group_service import GroupService


# ================================================================== #
#  群组基础操作
# ================================================================== #


class TestGetOrCreateGroup:
    """测试 get_or_create_group 方法。"""

    async def test_creates_new_group(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        group = Group(group_id="G1", name="TestGroup")
        mock_group_repo.update_or_create_group.return_value = group

        result = await group_service.get_or_create_group("G1", "TestGroup")

        assert result == group
        mock_group_repo.update_or_create_group.assert_awaited_once_with("G1", "TestGroup")

    async def test_returns_existing_group(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        existing = Group(group_id="G1", name="Existing")
        mock_group_repo.update_or_create_group.return_value = existing

        result = await group_service.get_or_create_group("G1", "Existing")

        assert result.group_id == "G1"


class TestGetGroup:
    """测试 get_group 方法。"""

    async def test_returns_group(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        group = Group(group_id="G1", name="MyGroup")
        mock_group_repo.get_group_by_id.return_value = group

        result = await group_service.get_group("G1")

        assert result == group

    async def test_returns_none_when_not_found(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        mock_group_repo.get_group_by_id.return_value = None

        result = await group_service.get_group("G999")

        assert result is None


class TestGroupExists:
    """测试 group_exists 方法。"""

    async def test_returns_true(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        mock_group_repo.group_exists.return_value = True
        assert await group_service.group_exists("G1") is True

    async def test_returns_false(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        mock_group_repo.group_exists.return_value = False
        assert await group_service.group_exists("G999") is False


class TestUpdateGroupName:
    """测试 update_group_name 方法。"""

    async def test_updates_name(
        self, group_service: GroupService, mock_group_repo: AsyncMock
    ):
        mock_group_repo.update_or_create_group.return_value = Group(
            group_id="G1", name="NewName"
        )

        await group_service.update_group_name("G1", "NewName")

        mock_group_repo.update_or_create_group.assert_awaited_once_with("G1", "NewName")


# ================================================================== #
#  群成员关系管理
# ================================================================== #


class TestEnsureMember:
    """测试 ensure_member 方法。"""

    async def test_creates_member_mapping(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        member = GroupMember(group_id="G1", qq_id="12345")
        mock_group_member_repo.update_or_create_member.return_value = member

        result = await group_service.ensure_member("G1", "12345")

        assert result == member
        mock_group_member_repo.update_or_create_member.assert_awaited_once_with(
            "G1", "12345"
        )


class TestIsMember:
    """测试 is_member 方法。"""

    async def test_returns_true(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.group_member_exists.return_value = True
        assert await group_service.is_member("G1", "12345") is True

    async def test_returns_false(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.group_member_exists.return_value = False
        assert await group_service.is_member("G1", "99999") is False


class TestGetGroupMembers:
    """测试 get_group_members 方法。"""

    async def test_returns_members(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        members = [
            GroupMember(group_id="G1", qq_id="111"),
            GroupMember(group_id="G1", qq_id="222"),
        ]
        mock_group_member_repo.get_members_by_group.return_value = members

        result = await group_service.get_group_members("G1")

        assert len(result) == 2
        assert result[0].qq_id == "111"

    async def test_returns_empty_for_no_members(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.get_members_by_group.return_value = []

        result = await group_service.get_group_members("G_EMPTY")

        assert result == []


class TestGetUserGroups:
    """测试 get_user_groups 方法。"""

    async def test_returns_groups(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        groups = [
            GroupMember(group_id="G1", qq_id="12345"),
            GroupMember(group_id="G2", qq_id="12345"),
        ]
        mock_group_member_repo.get_groups_by_user.return_value = groups

        result = await group_service.get_user_groups("12345")

        assert len(result) == 2


class TestCountMembers:
    """测试 count_members 方法。"""

    async def test_returns_count(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.count_members_by_group.return_value = 42

        result = await group_service.count_members("G1")

        assert result == 42


class TestRemoveMember:
    """测试 remove_member 方法。"""

    async def test_returns_true_on_success(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.delete_group_member.return_value = True

        result = await group_service.remove_member("G1", "12345")

        assert result is True

    async def test_returns_false_when_not_found(
        self, group_service: GroupService, mock_group_member_repo: AsyncMock
    ):
        mock_group_member_repo.delete_group_member.return_value = False

        result = await group_service.remove_member("G1", "99999")

        assert result is False


# ================================================================== #
#  群名片查询
# ================================================================== #


class TestGetGroupNicknames:
    """测试 get_group_nicknames 方法。"""

    async def test_returns_nicknames(
        self, group_service: GroupService, mock_group_nickname_repo: AsyncMock
    ):
        nicks = [
            GroupNickname(qq_id="111", group_id="G1", current_using=True, name="A"),
            GroupNickname(qq_id="222", group_id="G1", current_using=False, name="B"),
        ]
        mock_group_nickname_repo.get_nicknames_by_group.return_value = nicks

        result = await group_service.get_group_nicknames("G1")

        assert len(result) == 2


class TestGetGroupNicknameStats:
    """测试 get_group_nickname_stats 方法。"""

    async def test_returns_stats_dict(
        self, group_service: GroupService, mock_group_nickname_repo: AsyncMock
    ):
        stats = {
            "total_nicknames": 10,
            "users_with_nicknames": 5,
            "current_nicknames": 5,
        }
        mock_group_nickname_repo.get_group_nickname_statistics.return_value = stats

        result = await group_service.get_group_nickname_stats("G1")

        assert result["total_nicknames"] == 10
        assert result["users_with_nicknames"] == 5
