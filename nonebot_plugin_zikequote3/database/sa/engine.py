"""
AsyncEngine 工厂函数。

负责创建 SQLAlchemy 2.0 AsyncEngine 并注册 SQLite PRAGMA 事件监听器。
PRAGMA 配置参考现有 connection_manager.py，确保兼容：
- journal_mode=WAL
- foreign_keys=ON
- busy_timeout=5000
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _register_pragma_listeners(engine: AsyncEngine) -> None:
    """为 engine 的底层同步引擎注册 SQLite PRAGMA 事件监听器。"""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def create_async_engine_factory(
    db_path: Union[str, Path],
) -> AsyncEngine:
    """
    创建配置好的 AsyncEngine 实例。

    参数:
        db_path: 数据库文件路径，或 ":memory:" 表示内存数据库。

    返回:
        已注册 PRAGMA 监听器的 AsyncEngine。
    """
    # 处理 :memory: 特殊值
    path_str = str(db_path)
    if path_str == ":memory:":
        url = "sqlite+aiosqlite:///:memory:"
    else:
        url = f"sqlite+aiosqlite:///{path_str}"

    engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
    )

    _register_pragma_listeners(engine)
    return engine
