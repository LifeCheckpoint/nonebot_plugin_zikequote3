"""
Alembic env.py -- async migration environment configuration.

Supports two modes:
1. CLI: ``alembic upgrade head`` -- reads URL from alembic.ini, creates async engine
2. Programmatic: pass an existing sync connection via ``config.attributes["connection"]``
"""

from __future__ import annotations

import asyncio
import sys
import types
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---- Alembic Config object ----
config = context.config

# Configure Python logging (only when launched via .ini file)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Pre-register parent package stubs to avoid triggering
# nonebot_plugin_zikequote3/__init__.py -> nonebot initialization chain
# (same approach as tests/unit/conftest.py)
# ---------------------------------------------------------------------------
_plugin_root = Path(__file__).resolve().parent.parent.parent

if "nonebot_plugin_zikequote3" not in sys.modules:
    _stub_pkg = types.ModuleType("nonebot_plugin_zikequote3")
    _stub_pkg.__path__ = [str(_plugin_root)]
    sys.modules["nonebot_plugin_zikequote3"] = _stub_pkg

_database_root = _plugin_root / "database"
if "nonebot_plugin_zikequote3.database" not in sys.modules:
    _stub_db = types.ModuleType("nonebot_plugin_zikequote3.database")
    _stub_db.__path__ = [str(_database_root)]
    sys.modules["nonebot_plugin_zikequote3.database"] = _stub_db

# ---- Import all ORM models to ensure Base.metadata has all table defs ----
from nonebot_plugin_zikequote3.database.sa.base import Base  # noqa: E402
from nonebot_plugin_zikequote3.database.sa.models import *  # noqa: E402, F401, F403

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script only)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations on the given sync connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Supports two approaches:
    - Programmatic: pass connection via config.attributes["connection"]
    - CLI: create async engine from config
    """
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        # Programmatic call with existing sync connection
        do_run_migrations(connectable)
    else:
        # CLI call - create async engine
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
