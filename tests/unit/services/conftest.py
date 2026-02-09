"""
Service 单元测试 conftest —— 为 UserService / GroupService 提供 mock Repository fixtures。

所有 Repository 均使用 ``AsyncMock``，不需要真实数据库。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.repositories.group_member_repository import (
    GroupMemberRepository,
)
from nonebot_plugin_zikequote3.database.repositories.group_nickname_repository import (
    GroupNicknameRepository,
)
from nonebot_plugin_zikequote3.database.repositories.group_repository import (
    GroupRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_nickname_repository import (
    UserNicknameRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_repository import (
    UserRepository,
)
from nonebot_plugin_zikequote3.services.new.group_service import GroupService
from nonebot_plugin_zikequote3.services.new.user_service import UserService


# ---- Mock Repository fixtures ---- #


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_user_nickname_repo() -> AsyncMock:
    return AsyncMock(spec=UserNicknameRepository)


@pytest.fixture
def mock_group_nickname_repo() -> AsyncMock:
    return AsyncMock(spec=GroupNicknameRepository)


@pytest.fixture
def mock_group_repo() -> AsyncMock:
    return AsyncMock(spec=GroupRepository)


@pytest.fixture
def mock_group_member_repo() -> AsyncMock:
    return AsyncMock(spec=GroupMemberRepository)


# ---- Service fixtures ---- #


@pytest.fixture
def user_service(
    mock_user_repo: AsyncMock,
    mock_user_nickname_repo: AsyncMock,
    mock_group_nickname_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
) -> UserService:
    return UserService(
        user_repo=mock_user_repo,
        user_nickname_repo=mock_user_nickname_repo,
        group_nickname_repo=mock_group_nickname_repo,
        group_member_repo=mock_group_member_repo,
    )


@pytest.fixture
def group_service(
    mock_group_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
    mock_group_nickname_repo: AsyncMock,
) -> GroupService:
    return GroupService(
        group_repo=mock_group_repo,
        group_member_repo=mock_group_member_repo,
        group_nickname_repo=mock_group_nickname_repo,
    )
