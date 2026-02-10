"""Alembic 异步迁移环境配置。

支持两种运行模式：

1. CLI 模式：``alembic upgrade head`` —— 从 ``alembic.ini`` 读取 URL 并创建异步引擎
2. 编程模式：通过 ``config.attributes["connection"]`` 传入已有的同步连接
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
    """以离线模式运行迁移（仅生成 SQL 脚本）。"""
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
    """在给定的同步连接上执行迁移。

    :param connection: SQLAlchemy 同步连接。
    :type connection: Connection
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """创建异步引擎并运行迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """以在线模式运行迁移。

    支持两种方式：

    - 编程式调用：通过 ``config.attributes["connection"]`` 传入已有连接。
    - CLI 调用：根据配置创建异步引擎。
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
