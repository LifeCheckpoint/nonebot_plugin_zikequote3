"""
Alembic migration tests.

Verify that:
1. The initial migration script can upgrade from empty to head
2. All 12 tables are created after upgrade
3. Downgrade back to base removes all tables
4. Programmatic migration via shared connection works
"""

from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect, text

from alembic import command
from alembic.config import Config

from nonebot_plugin_zikequote3.database.sa import create_async_engine_factory
from nonebot_plugin_zikequote3.database.sa.base import Base
from nonebot_plugin_zikequote3.database.sa.models import *  # noqa: F401, F403

# All 12 expected table names
EXPECTED_TABLES = sorted([
    "groups",
    "users",
    "images",
    "group_configs",
    "group_members",
    "group_nicknames",
    "user_nicknames",
    "msgs_queue",
    "queue_group_message_counts",
    "quotes",
    "msgid_quoteid_map",
    "reviews",
])

# Path to alembic.ini inside the plugin package
_ALEMBIC_INI = (
    Path(__file__).resolve().parent.parent.parent
    / "nonebot_plugin_zikequote3"
    / "alembic.ini"
)


def _make_alembic_cfg(url: str) -> Config:
    """Create an Alembic Config pointing at the plugin's alembic.ini."""
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


# ============================================================================
# Test: upgrade to head creates all 12 tables
# ============================================================================
class TestAlembicUpgrade:
    """Verify alembic upgrade head creates the expected schema."""

    async def test_upgrade_creates_all_tables(self):
        """Run upgrade head via programmatic API and check tables."""
        engine = create_async_engine_factory(":memory:")

        async with engine.connect() as async_conn:
            # Run alembic upgrade via run_sync + shared connection
            def _run_upgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

            await async_conn.run_sync(_run_upgrade)
            await async_conn.commit()

            # Inspect tables
            def _get_tables(connection):
                inspector = sa_inspect(connection)
                return sorted(inspector.get_table_names())

            tables = await async_conn.run_sync(_get_tables)

        await engine.dispose()

        # Filter out alembic's own version table
        user_tables = sorted(t for t in tables if t != "alembic_version")
        assert user_tables == EXPECTED_TABLES, (
            f"Expected {EXPECTED_TABLES}, got {user_tables}"
        )

    async def test_upgrade_stamps_version(self):
        """After upgrade, alembic_version table should contain head revision."""
        engine = create_async_engine_factory(":memory:")

        async with engine.connect() as async_conn:
            def _run_upgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

            await async_conn.run_sync(_run_upgrade)
            await async_conn.commit()

            # Check alembic_version has exactly one row
            result = await async_conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            rows = result.fetchall()

        await engine.dispose()

        assert len(rows) == 1, f"Expected 1 version row, got {len(rows)}"
        assert rows[0][0], "version_num should not be empty"


# ============================================================================
# Test: downgrade back to base removes all tables
# ============================================================================
class TestAlembicDowngrade:
    """Verify alembic downgrade base removes all user tables."""

    async def test_downgrade_removes_all_tables(self):
        """Upgrade then downgrade should leave only alembic_version."""
        engine = create_async_engine_factory(":memory:")

        async with engine.connect() as async_conn:
            def _run_upgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

            await async_conn.run_sync(_run_upgrade)
            await async_conn.commit()

            def _run_downgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.downgrade(cfg, "base")

            await async_conn.run_sync(_run_downgrade)
            await async_conn.commit()

            def _get_tables(connection):
                inspector = sa_inspect(connection)
                return sorted(inspector.get_table_names())

            tables = await async_conn.run_sync(_get_tables)

        await engine.dispose()

        user_tables = [t for t in tables if t != "alembic_version"]
        assert user_tables == [], (
            f"Expected no user tables after downgrade, got {user_tables}"
        )


# ============================================================================
# Test: migration matches ORM metadata
# ============================================================================
class TestMigrationMatchesMetadata:
    """Verify migration-created schema matches Base.metadata.create_all."""

    async def test_table_names_match_metadata(self):
        """Tables from migration should match Base.metadata table names."""
        expected_from_metadata = sorted(Base.metadata.tables.keys())

        engine = create_async_engine_factory(":memory:")

        async with engine.connect() as async_conn:
            def _run_upgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

            await async_conn.run_sync(_run_upgrade)
            await async_conn.commit()

            def _get_tables(connection):
                inspector = sa_inspect(connection)
                return sorted(inspector.get_table_names())

            tables = await async_conn.run_sync(_get_tables)

        await engine.dispose()

        user_tables = sorted(t for t in tables if t != "alembic_version")
        assert user_tables == expected_from_metadata, (
            f"Migration tables {user_tables} != metadata tables {expected_from_metadata}"
        )

    async def test_column_counts_match(self):
        """Each table should have the same number of columns as the ORM model."""
        engine = create_async_engine_factory(":memory:")

        async with engine.connect() as async_conn:
            def _run_upgrade(connection):
                cfg = Config(str(_ALEMBIC_INI))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

            await async_conn.run_sync(_run_upgrade)
            await async_conn.commit()

            def _get_column_counts(connection):
                inspector = sa_inspect(connection)
                counts = {}
                for table_name in inspector.get_table_names():
                    if table_name == "alembic_version":
                        continue
                    cols = inspector.get_columns(table_name)
                    counts[table_name] = len(cols)
                return counts

            migration_counts = await async_conn.run_sync(_get_column_counts)

        await engine.dispose()

        for table_name, table_obj in Base.metadata.tables.items():
            expected_col_count = len(table_obj.columns)
            actual_col_count = migration_counts.get(table_name)
            assert actual_col_count == expected_col_count, (
                f"Table '{table_name}': expected {expected_col_count} columns, "
                f"got {actual_col_count}"
            )
