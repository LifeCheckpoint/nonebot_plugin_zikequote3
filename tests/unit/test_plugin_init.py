"""
插件入口相关单元测试。

覆盖：
- 启动前置链路使用 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:101) 而非 [`Base.metadata.create_all()`](nonebot_plugin_zikequote3/database/sa/base.py:1)
- 迁移完成后可以继续组装 DI 容器并获取核心依赖
- 配置文件读取错误具备可诊断边界
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from nonebot_plugin_zikequote3.config import ConfigLoadError, load_config_from_path
from nonebot_plugin_zikequote3.database.alembic_runtime import migrate_database_to_head
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
from nonebot_plugin_zikequote3.di.container import create_container
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.migration_service import MigrationService
from nonebot_plugin_zikequote3.services.quote_collection_service import QuoteCollectionService
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.review_service import ReviewService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService


class TestStartupMigrationPreparation:
    """验证启动前置迁移链路。"""

    async def test_migrate_database_to_head_prepares_database_for_container(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "startup.db"
        image_path = tmp_path / "images"

        await migrate_database_to_head(db_path)

        container = create_container(
            db_path=db_path,
            image_store_path=image_path,
        )

        try:
            async with container() as scope:
                engine = await scope.get(AsyncEngine)
                assert isinstance(engine, AsyncEngine)

                async with engine.connect() as conn:
                    tables = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text("SELECT name FROM sqlite_master WHERE type='table'")
                            )
                        ).fetchall()
                    }
                    assert "quotes" in tables
                    assert "alembic_version" in tables
        finally:
            await container.close()

    async def test_memory_database_can_also_be_prepared_via_migration(self) -> None:
        await migrate_database_to_head(":memory:")

        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_not_used__"),
        )

        try:
            async with container() as scope:
                assert isinstance(await scope.get(AsyncEngine), AsyncEngine)
                assert isinstance(await scope.get(AsyncSession), AsyncSession)
                assert isinstance(await scope.get(ImageStore), ImageStore)
        finally:
            await container.close()


class TestContainerCompleteness:
    """验证迁移完成后的容器完整性。"""

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

    async def test_all_repositories_available_after_migration(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "repos.db"
        await migrate_database_to_head(db_path)

        container = create_container(
            db_path=db_path,
            image_store_path=tmp_path / "images",
        )
        try:
            async with container() as scope:
                for repo_type in self._ALL_REPO_TYPES:
                    repo = await scope.get(repo_type)
                    assert isinstance(repo, repo_type), f"获取 {repo_type.__name__} 失败"
        finally:
            await container.close()

    async def test_all_services_available_after_migration(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "services.db"
        await migrate_database_to_head(db_path)

        container = create_container(
            db_path=db_path,
            image_store_path=tmp_path / "images",
        )
        try:
            async with container() as scope:
                for svc_type in self._ALL_SERVICE_TYPES:
                    svc = await scope.get(svc_type)
                    assert isinstance(svc, svc_type), f"获取 {svc_type.__name__} 失败"
        finally:
            await container.close()


class TestConfigLoadingBoundary:
    """验证启动期配置文件读取边界。"""

    def test_load_config_from_path_missing_file_is_diagnostic(self, tmp_path: Path) -> None:
        missing_path = tmp_path / "missing.toml"

        with pytest.raises(ConfigLoadError, match="配置文件不存在"):
            load_config_from_path(missing_path)

    def test_load_config_from_path_invalid_toml_is_diagnostic(self, tmp_path: Path) -> None:
        config_path = tmp_path / "invalid.toml"
        config_path.write_text("[collecting\npickup_interval = 1", encoding="utf-8")

        with pytest.raises(ConfigLoadError, match="TOML 解析失败"):
            load_config_from_path(config_path)
