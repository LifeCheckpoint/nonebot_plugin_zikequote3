"""
Repository 测试 conftest —— 为每个 Repository 创建 fixture，注入 async_session。
"""

import pytest

from nonebot_plugin_zikequote3.database.repositories.group_config_repository import GroupConfigRepository
from nonebot_plugin_zikequote3.database.repositories.group_member_repository import GroupMemberRepository
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.image_repository import ImageRepository
from nonebot_plugin_zikequote3.database.repositories.mapping_repository import MappingRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


@pytest.fixture
def user_repo(async_session) -> UserRepository:
    return UserRepository(async_session)


@pytest.fixture
def group_repo(async_session) -> GroupRepository:
    return GroupRepository(async_session)


@pytest.fixture
def group_member_repo(async_session) -> GroupMemberRepository:
    return GroupMemberRepository(async_session)


@pytest.fixture
def image_repo(async_session) -> ImageRepository:
    return ImageRepository(async_session)


@pytest.fixture
def mapping_repo(async_session) -> MappingRepository:
    return MappingRepository(async_session)


@pytest.fixture
def group_config_repo(async_session) -> GroupConfigRepository:
    return GroupConfigRepository(async_session)
