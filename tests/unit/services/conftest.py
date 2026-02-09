"""
Service 单元测试 conftest —— 为所有 Service 提供 mock Repository fixtures。

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
from nonebot_plugin_zikequote3.database.repositories.image_repository import (
    ImageRepository,
)
from nonebot_plugin_zikequote3.database.repositories.mapping_repository import (
    MappingRepository,
)
from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
    MsgQueueRepository,
)
from nonebot_plugin_zikequote3.database.repositories.quote_repository import (
    QuoteRepository,
)
from nonebot_plugin_zikequote3.database.repositories.review_repository import (
    ReviewRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_nickname_repository import (
    UserNicknameRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_repository import (
    UserRepository,
)
from nonebot_plugin_zikequote3.database.repositories.group_config_repository import (
    GroupConfigRepository,
)
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.migration_service import MigrationService
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    QuoteCollectionService,
)
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.review_service import ReviewService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService


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


@pytest.fixture
def mock_quote_repo() -> AsyncMock:
    return AsyncMock(spec=QuoteRepository)


@pytest.fixture
def mock_image_repo() -> AsyncMock:
    return AsyncMock(spec=ImageRepository)


@pytest.fixture
def mock_mapping_repo() -> AsyncMock:
    return AsyncMock(spec=MappingRepository)


@pytest.fixture
def mock_review_repo() -> AsyncMock:
    return AsyncMock(spec=ReviewRepository)


@pytest.fixture
def mock_msg_queue_repo() -> AsyncMock:
    return AsyncMock(spec=MsgQueueRepository)


@pytest.fixture
def mock_group_config_repo() -> AsyncMock:
    return AsyncMock(spec=GroupConfigRepository)


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


@pytest.fixture
def quote_write_service(
    mock_quote_repo: AsyncMock,
    mock_image_repo: AsyncMock,
    mock_mapping_repo: AsyncMock,
    user_service: UserService,
) -> QuoteWriteService:
    return QuoteWriteService(
        quote_repo=mock_quote_repo,
        image_repo=mock_image_repo,
        mapping_repo=mock_mapping_repo,
        user_service=user_service,
    )


@pytest.fixture
def quote_read_service(
    mock_quote_repo: AsyncMock,
    mock_review_repo: AsyncMock,
    mock_image_repo: AsyncMock,
    user_service: UserService,
) -> QuoteReadService:
    return QuoteReadService(
        quote_repo=mock_quote_repo,
        review_repo=mock_review_repo,
        image_repo=mock_image_repo,
        user_service=user_service,
    )


@pytest.fixture
def quote_collection_service(
    mock_msg_queue_repo: AsyncMock,
    mock_quote_repo: AsyncMock,
    mock_image_repo: AsyncMock,
    mock_mapping_repo: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_user_nickname_repo: AsyncMock,
    mock_group_nickname_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
    mock_group_repo: AsyncMock,
) -> QuoteCollectionService:
    us = UserService(
        user_repo=mock_user_repo,
        user_nickname_repo=mock_user_nickname_repo,
        group_nickname_repo=mock_group_nickname_repo,
        group_member_repo=mock_group_member_repo,
    )
    qws = QuoteWriteService(
        quote_repo=mock_quote_repo,
        image_repo=mock_image_repo,
        mapping_repo=mock_mapping_repo,
        user_service=us,
    )
    gs = GroupService(
        group_repo=mock_group_repo,
        group_member_repo=mock_group_member_repo,
        group_nickname_repo=mock_group_nickname_repo,
    )
    return QuoteCollectionService(
        msg_queue_repo=mock_msg_queue_repo,
        quote_write_service=qws,
        user_service=us,
        group_service=gs,
    )


@pytest.fixture
def review_service(
    mock_review_repo: AsyncMock,
    mock_quote_repo: AsyncMock,
) -> ReviewService:
    return ReviewService(
        review_repo=mock_review_repo,
        quote_repo=mock_quote_repo,
    )


@pytest.fixture
def statistics_service(
    mock_quote_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
) -> StatisticsService:
    return StatisticsService(
        quote_repo=mock_quote_repo,
        group_member_repo=mock_group_member_repo,
    )


@pytest.fixture
def config_service(
    mock_group_config_repo: AsyncMock,
) -> ConfigService:
    return ConfigService(
        group_config_repo=mock_group_config_repo,
    )


@pytest.fixture
def migration_service(
    mock_quote_repo: AsyncMock,
    mock_group_member_repo: AsyncMock,
    mock_group_nickname_repo: AsyncMock,
) -> MigrationService:
    return MigrationService(
        quote_repo=mock_quote_repo,
        group_member_repo=mock_group_member_repo,
        group_nickname_repo=mock_group_nickname_repo,
    )
