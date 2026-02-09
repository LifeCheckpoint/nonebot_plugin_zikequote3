"""
插件入口初始化流程验证测试。

测试内容：
- create_container() 能正常创建容器
- 容器能提供所有必要的依赖（Engine、Session、Repository、Service）
- Base.metadata.create_all 能在内存数据库上正常执行
- 模拟 _startup 的完整初始化流程（不依赖 NoneBot 运行时）

注意：不测试完整的 NoneBot 启动流程（那需要 nonebug 集成测试）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from nonebot_plugin_zikequote3.database.sa import (
    Base,
    create_async_engine_factory,
    create_async_session_factory,
)
from nonebot_plugin_zikequote3.database.sa.models import (  # noqa: F401
    GroupMemberModel,
    GroupModel,
    GroupNicknameModel,
    UserModel,
    UserNicknameModel,
    GroupConfigModel,
    ImageModel,
    MsgIdQuoteIdMapModel,
    MsgQueueModel,
    QueueGroupMessageCountModel,
    QuoteModel,
    ReviewModel,
)
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
from nonebot_plugin_zikequote3.di.container import create_container


# ---------------------------------------------------------------------------
# 数据库表创建测试
# ---------------------------------------------------------------------------


class TestDatabaseTableCreation:
    """验证 Base.metadata.create_all 能在内存数据库上正常执行。"""

    async def test_create_all_tables(self) -> None:
        """create_all 应成功创建所有 ORM 模型对应的表。"""
        engine = create_async_engine_factory(":memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 验证表确实被创建了
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            table_names = {row[0] for row in result.fetchall()}

        # 至少应包含核心表
        expected_tables = {
            "users", "groups", "group_members",
            "quotes", "reviews", "images",
        }
        assert expected_tables.issubset(table_names), (
            f"缺少表: {expected_tables - table_names}"
        )
        await engine.dispose()

    async def test_create_all_idempotent(self) -> None:
        """多次调用 create_all 不应报错（幂等性）。"""
        engine = create_async_engine_factory(":memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()


# ---------------------------------------------------------------------------
# 模拟 _startup 完整初始化流程
# ---------------------------------------------------------------------------


class TestStartupFlow:
    """模拟 __init__.py 中 _startup 的完整初始化流程。"""

    async def test_full_startup_simulation(self, tmp_path: Path) -> None:
        """
        模拟完整的启动流程：
        1. 创建引擎并建表
        2. 创建 DI 容器
        3. 从容器获取核心依赖
        """
        db_path = tmp_path / "test.db"
        image_path = tmp_path / "images"

        # Step 1: 创建引擎并建表（与 _startup 逻辑一致）
        engine = create_async_engine_factory(db_path)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

        # Step 2: 创建 DI 容器
        container = create_container(
            db_path=db_path,
            image_store_path=image_path,
        )

        # Step 3: 验证容器能提供核心依赖
        async with container() as scope:
            engine_from_di = await scope.get(AsyncEngine)
            assert isinstance(engine_from_di, AsyncEngine)

            session = await scope.get(AsyncSession)
            assert isinstance(session, AsyncSession)

        await container.close()

    async def test_startup_with_memory_db(self) -> None:
        """使用内存数据库模拟启动流程。"""
        engine = create_async_engine_factory(":memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_not_used__"),
        )

        # 验证所有层级的依赖都能正常获取
        async with container() as scope:
            # 基础设施层
            assert isinstance(await scope.get(AsyncEngine), AsyncEngine)
            assert isinstance(await scope.get(ImageStore), ImageStore)

            # Repository 层（抽样验证）
            assert isinstance(await scope.get(UserRepository), UserRepository)
            assert isinstance(await scope.get(QuoteRepository), QuoteRepository)
            assert isinstance(await scope.get(GroupRepository), GroupRepository)

            # Service 层（抽样验证）
            assert isinstance(await scope.get(UserService), UserService)
            assert isinstance(await scope.get(QuoteReadService), QuoteReadService)
            assert isinstance(await scope.get(ConfigService), ConfigService)

        await container.close()


# ---------------------------------------------------------------------------
# 容器完整性测试（补充 test_di_container.py 的集成视角）
# ---------------------------------------------------------------------------


class TestContainerCompleteness:
    """验证容器能提供所有必要的依赖，从 Engine 到 Service 全链路。"""

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

    async def test_all_repositories_available(self) -> None:
        """容器能提供全部 11 个 Repository。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_not_used__"),
        )
        async with container() as scope:
            for repo_type in self._ALL_REPO_TYPES:
                repo = await scope.get(repo_type)
                assert isinstance(repo, repo_type), (
                    f"获取 {repo_type.__name__} 失败"
                )
        await container.close()

    async def test_all_services_available(self) -> None:
        """容器能提供全部 9 个 Service。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_not_used__"),
        )
        async with container() as scope:
            for svc_type in self._ALL_SERVICE_TYPES:
                svc = await scope.get(svc_type)
                assert isinstance(svc, svc_type), (
                    f"获取 {svc_type.__name__} 失败"
                )
        await container.close()
