"""
Alembic migration tests.

Verify that:
1. upgrade 到 head 会建立当前 schema 并写入 head revision
2. downgrade 回 base 会移除所有业务表
3. head schema 中的 quotes 语义与图片语录业务规则一致
4. 启动期程序化迁移能把历史未版本化旧库升级到 head
5. 启动期程序化迁移会对未知未版本化 schema 给出可诊断错误
"""

from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from nonebot_plugin_zikequote3.database.alembic_runtime import (
    DatabaseMigrationError,
    migrate_database_to_head,
)
from nonebot_plugin_zikequote3.database.sa import create_async_engine_factory
from nonebot_plugin_zikequote3.database.sa.base import Base
from nonebot_plugin_zikequote3.database.sa.models import *  # noqa: F401, F403

_EXPECTED_TABLES = sorted(Base.metadata.tables.keys())
_INITIAL_REVISION = "9a62ce7e5cff"
_ALEMBIC_INI = (
    Path(__file__).resolve().parent.parent.parent
    / "nonebot_plugin_zikequote3"
    / "alembic.ini"
)


def _make_alembic_cfg() -> Config:
    return Config(str(_ALEMBIC_INI))


def _get_head_revision() -> str:
    return ScriptDirectory.from_config(_make_alembic_cfg()).get_current_head()


def _run_upgrade(revision: str):
    def _runner(connection) -> None:
        cfg = _make_alembic_cfg()
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, revision)

    return _runner


def _run_downgrade(revision: str):
    def _runner(connection) -> None:
        cfg = _make_alembic_cfg()
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, revision)

    return _runner


def _inspect_quote_schema(connection) -> tuple[dict[str, dict], set[str]]:
    inspector = sa_inspect(connection)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("quotes")
    }
    check_names = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("quotes")
        if constraint.get("name")
    }
    return columns, check_names



def _inspect_current_nickname_indexes(connection) -> tuple[set[str], set[str]]:
    inspector = sa_inspect(connection)
    user_indexes = {
        index.get("name")
        for index in inspector.get_indexes("user_nicknames")
        if index.get("name")
    }
    group_indexes = {
        index.get("name")
        for index in inspector.get_indexes("group_nicknames")
        if index.get("name")
    }
    return user_indexes, group_indexes


class TestAlembicUpgrade:
    """验证 Alembic 升级到 head 的行为。"""

    async def test_upgrade_to_head_sets_current_revision_and_expected_tables(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "upgrade_head.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade("head"))
                await async_conn.commit()

                tables = await async_conn.run_sync(
                    lambda connection: sorted(
                        table_name
                        for table_name in sa_inspect(connection).get_table_names()
                        if table_name != "alembic_version"
                    )
                )
                version = (
                    await async_conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
        finally:
            await engine.dispose()

        assert tables == _EXPECTED_TABLES
        assert version == _get_head_revision()

    async def test_head_quote_schema_matches_image_only_business_rule(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "quote_schema.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade("head"))
                await async_conn.commit()
                columns, check_names = await async_conn.run_sync(_inspect_quote_schema)
                user_indexes, group_indexes = await async_conn.run_sync(
                    _inspect_current_nickname_indexes
                )
        finally:
            await engine.dispose()

        assert columns["content"]["nullable"] is True
        assert "ck_quotes_content_or_image_present" in check_names
        assert "uq_user_nicknames_current_using" in user_indexes
        assert "uq_group_nicknames_current_using" in group_indexes

    async def test_head_schema_enforces_current_nickname_uniqueness(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "nickname_unique.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade("head"))
                await async_conn.commit()
                await async_conn.execute(
                    text("INSERT INTO users (qq_id, avatar) VALUES ('u1', NULL), ('u2', NULL)")
                )
                await async_conn.execute(
                    text("INSERT INTO groups (group_id, name) VALUES ('g1', 'group1')")
                )
                await async_conn.commit()

                await async_conn.execute(
                    text(
                        "INSERT INTO user_nicknames (qq_id, name, current_using) VALUES ('u1', 'A', 1)"
                    )
                )
                await async_conn.commit()

                with pytest.raises(IntegrityError):
                    await async_conn.execute(
                        text(
                            "INSERT INTO user_nicknames (qq_id, name, current_using) VALUES ('u1', 'B', 1)"
                        )
                    )
                await async_conn.rollback()

                await async_conn.execute(
                    text(
                        "INSERT INTO group_nicknames (qq_id, group_id, name, current_using) VALUES ('u2', 'g1', 'A', 1)"
                    )
                )
                await async_conn.commit()

                with pytest.raises(IntegrityError):
                    await async_conn.execute(
                        text(
                            "INSERT INTO group_nicknames (qq_id, group_id, name, current_using) VALUES ('u2', 'g1', 'B', 1)"
                        )
                    )
                await async_conn.rollback()
        finally:
            await engine.dispose()


class TestAlembicDowngrade:
    """验证 Alembic 降级行为。"""

    async def test_downgrade_base_removes_all_user_tables(self, tmp_path: Path, monkeypatch) -> None:
        db_path = tmp_path / "downgrade.db"
        engine = create_async_engine_factory(db_path)
        monkeypatch.setenv("ALEMBIC_FORCE_DOWNGRADE", "1")

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade("head"))
                await async_conn.commit()
                await async_conn.run_sync(_run_downgrade("base"))
                await async_conn.commit()
                tables = await async_conn.run_sync(
                    lambda connection: sorted(sa_inspect(connection).get_table_names())
                )
        finally:
            await engine.dispose()

        user_tables = [table_name for table_name in tables if table_name != "alembic_version"]
        assert user_tables == []


class TestStartupMigrationCompatibility:
    """验证启动期程序化迁移路径。"""

    async def test_migrate_database_to_head_upgrades_unversioned_legacy_schema(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "legacy_unversioned.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade(_INITIAL_REVISION))
                await async_conn.commit()
                await async_conn.execute(
                    text("INSERT INTO users (qq_id, avatar) VALUES ('dup_u', NULL)")
                )
                await async_conn.execute(
                    text("INSERT INTO groups (group_id, name) VALUES ('dup_g', 'dup-group')")
                )
                await async_conn.execute(
                    text(
                        "INSERT INTO user_nicknames (qq_id, name, current_using) VALUES ('dup_u', 'A', 1), ('dup_u', 'B', 1)"
                    )
                )
                await async_conn.execute(
                    text(
                        "INSERT INTO group_nicknames (qq_id, group_id, name, current_using) VALUES ('dup_u', 'dup_g', 'A', 1), ('dup_u', 'dup_g', 'B', 1)"
                    )
                )
                await async_conn.commit()
                await async_conn.execute(text("DROP TABLE alembic_version"))
                await async_conn.commit()
        finally:
            await engine.dispose()

        await migrate_database_to_head(db_path)

        engine = create_async_engine_factory(db_path)
        try:
            async with engine.connect() as async_conn:
                version = (
                    await async_conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
                columns, check_names = await async_conn.run_sync(_inspect_quote_schema)
                user_indexes, group_indexes = await async_conn.run_sync(
                    _inspect_current_nickname_indexes
                )
                current_user_count = (
                    await async_conn.execute(
                        text(
                            "SELECT COUNT(*) FROM user_nicknames WHERE qq_id = 'dup_u' AND current_using = 1"
                        )
                    )
                ).scalar_one()
                current_group_count = (
                    await async_conn.execute(
                        text(
                            "SELECT COUNT(*) FROM group_nicknames WHERE qq_id = 'dup_u' AND group_id = 'dup_g' AND current_using = 1"
                        )
                    )
                ).scalar_one()
        finally:
            await engine.dispose()

        assert version == _get_head_revision()
        assert columns["content"]["nullable"] is True
        assert "ck_quotes_content_or_image_present" in check_names
        assert current_user_count == 1
        assert current_group_count == 1
        assert "uq_user_nicknames_current_using" in user_indexes
        assert "uq_group_nicknames_current_using" in group_indexes

    async def test_migrate_database_to_head_upgrades_official_v1_to_v2_shape(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "official_v1_to_v2_unversioned.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.connect() as async_conn:
                await async_conn.run_sync(_run_upgrade(_INITIAL_REVISION))
                await async_conn.commit()
                await async_conn.execute(text("DROP TABLE queue_group_message_counts"))
                await async_conn.execute(text("DROP TABLE alembic_version"))
                await async_conn.commit()
        finally:
            await engine.dispose()

        await migrate_database_to_head(db_path)

        engine = create_async_engine_factory(db_path)
        try:
            async with engine.connect() as async_conn:
                version = (
                    await async_conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
                tables = await async_conn.run_sync(
                    lambda connection: set(sa_inspect(connection).get_table_names())
                )
        finally:
            await engine.dispose()

        assert version == _get_head_revision()
        assert "queue_group_message_counts" in tables

    async def test_migrate_database_to_head_rejects_unknown_unversioned_schema(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "unknown_unversioned.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.begin() as async_conn:
                await async_conn.execute(text("CREATE TABLE rogue (id INTEGER PRIMARY KEY)"))
        finally:
            await engine.dispose()

        with pytest.raises(DatabaseMigrationError, match="无法安全自动迁移"):
            await migrate_database_to_head(db_path)
