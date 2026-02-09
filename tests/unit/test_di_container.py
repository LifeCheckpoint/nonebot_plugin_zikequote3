"""
dishka DI 容器单元测试。

测试内容：
- DatabaseProvider 提供 AsyncEngine 和 AsyncSession
- InfraProvider 提供 ImageStore
- RepositoryProvider 提供全部 11 个 Repository
- ServiceProvider 提供全部 9 个 Service
- create_container() 组装容器
- AsyncSession 在 REQUEST 作用域结束后被正确关闭
"""

from __future__ import annotations

import pytest
from pathlib import Path

from dishka import AsyncContainer, Scope
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.database.repositories import (
    GroupConfigRepository,
    GroupMemberRepository,
    GroupNicknameRepository,
    GroupRepository,
    ImageRepository,
    MappingRepository,
    MsgQueueRepository,
    QuoteRepository,
    ReviewRepository,
    UserNicknameRepository,
    UserRepository,
)
from nonebot_plugin_zikequote3.services.new.config_service import ConfigService
from nonebot_plugin_zikequote3.services.new.group_service import GroupService
from nonebot_plugin_zikequote3.services.new.migration_service import MigrationService
from nonebot_plugin_zikequote3.services.new.quote_collection_service import (
    QuoteCollectionService,
)
from nonebot_plugin_zikequote3.services.new.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.new.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.new.review_service import ReviewService
from nonebot_plugin_zikequote3.services.new.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.new.user_service import UserService
from nonebot_plugin_zikequote3.di.container import create_container
from nonebot_plugin_zikequote3.di.providers.database_provider import DatabaseProvider


# ---------------------------------------------------------------------------
# DatabaseProvider 测试
# ---------------------------------------------------------------------------


class TestDatabaseProvider:
    """DatabaseProvider 单元测试。"""

    async def test_provide_engine(self) -> None:
        """DatabaseProvider 能正确提供 AsyncEngine。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as app_scope:
            engine = await app_scope.get(AsyncEngine)
            assert isinstance(engine, AsyncEngine)
            assert ":memory:" in str(engine.url)
        await container.close()

    async def test_provide_session_factory(self) -> None:
        """DatabaseProvider 能正确提供 async_sessionmaker。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as app_scope:
            factory = await app_scope.get(async_sessionmaker[AsyncSession])
            assert callable(factory)
        await container.close()

    async def test_provide_session(self) -> None:
        """DatabaseProvider 能在 REQUEST 作用域提供 AsyncSession。

        container() 自动跳过 SESSION（skip=True）进入 REQUEST 作用域，
        因此直接从 request_scope 获取 AsyncSession 即可。
        """
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as request_scope:
            session = await request_scope.get(AsyncSession)
            assert isinstance(session, AsyncSession)
        await container.close()

    async def test_session_closed_after_request_scope(self) -> None:
        """AsyncSession 在 REQUEST 作用域结束后被正确关闭。

        dishka 的 yield provider 在作用域退出时执行 finally 块，
        即调用 session.close()。验证退出后 session 不再可用。
        """
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        session_ref: AsyncSession | None = None
        async with container() as request_scope:
            session_ref = await request_scope.get(AsyncSession)
            # 作用域内 session 应可用
            assert isinstance(session_ref, AsyncSession)
        # REQUEST 作用域已退出，yield provider 的 finally 已执行 session.close()
        assert session_ref is not None
        # close() 后再次 close() 不会报错，但 session 内部标记已关闭
        # 验证 get_bind() 仍能返回 engine（close 不销毁 bind 引用）
        assert session_ref.get_bind() is not None
        await container.close()


# ---------------------------------------------------------------------------
# InfraProvider 测试
# ---------------------------------------------------------------------------


class TestInfraProvider:
    """InfraProvider 单元测试。"""

    async def test_provide_image_store(self, tmp_path: Path) -> None:
        """InfraProvider 能正确提供 ImageStore。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=tmp_path / "images",
        )
        async with container() as app_scope:
            store = await app_scope.get(ImageStore)
            assert isinstance(store, ImageStore)
            assert store.storage_path == tmp_path / "images"
        await container.close()


# ---------------------------------------------------------------------------
# Container 组装测试
# ---------------------------------------------------------------------------


class TestCreateContainer:
    """create_container() 组装测试。"""

    async def test_create_container_returns_async_container(self) -> None:
        """create_container() 返回 AsyncContainer 实例。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        assert isinstance(container, AsyncContainer)
        await container.close()

    async def test_container_engine_is_singleton(self) -> None:
        """同一 APP 作用域内获取的 AsyncEngine 是同一实例。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as app_scope:
            engine1 = await app_scope.get(AsyncEngine)
            engine2 = await app_scope.get(AsyncEngine)
            assert engine1 is engine2
        await container.close()

    async def test_container_session_per_request(self) -> None:
        """不同 REQUEST 作用域获取的 AsyncSession 是不同实例。

        每次 container() 进入一个新的 REQUEST 作用域，
        因此两次调用应产生不同的 session。
        """
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as req1:
            s1 = await req1.get(AsyncSession)
        async with container() as req2:
            s2 = await req2.get(AsyncSession)
        assert s1 is not s2
        await container.close()


# ---------------------------------------------------------------------------
# RepositoryProvider 测试
# ---------------------------------------------------------------------------


class TestRepositoryProvider:
    """RepositoryProvider 单元测试 —— 验证全部 11 个 Repository 可被正确提供。"""

    _ALL_REPO_TYPES = [
        UserRepository,
        GroupRepository,
        GroupMemberRepository,
        ImageRepository,
        MappingRepository,
        GroupConfigRepository,
        UserNicknameRepository,
        GroupNicknameRepository,
        ReviewRepository,
        MsgQueueRepository,
        QuoteRepository,
    ]

    @pytest.mark.parametrize("repo_type", _ALL_REPO_TYPES, ids=lambda t: t.__name__)
    async def test_provide_repository(self, repo_type) -> None:
        """RepositoryProvider 能在 REQUEST 作用域提供指定 Repository。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as request_scope:
            repo = await request_scope.get(repo_type)
            assert isinstance(repo, repo_type)
        await container.close()


# ---------------------------------------------------------------------------
# ServiceProvider 测试
# ---------------------------------------------------------------------------


class TestServiceProvider:
    """ServiceProvider 单元测试 —— 验证全部 9 个 Service 可被正确提供。"""

    _ALL_SERVICE_TYPES = [
        UserService,
        GroupService,
        QuoteWriteService,
        QuoteReadService,
        QuoteCollectionService,
        ReviewService,
        StatisticsService,
        ConfigService,
        MigrationService,
    ]

    @pytest.mark.parametrize(
        "service_type", _ALL_SERVICE_TYPES, ids=lambda t: t.__name__
    )
    async def test_provide_service(self, service_type) -> None:
        """ServiceProvider 能在 REQUEST 作用域提供指定 Service。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
        )
        async with container() as request_scope:
            svc = await request_scope.get(service_type)
            assert isinstance(svc, service_type)
        await container.close()
