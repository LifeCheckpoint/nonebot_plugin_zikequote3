"""
AsyncEngine 工厂函数。

负责创建 SQLAlchemy 2.0 AsyncEngine 并注册 SQLite PRAGMA 事件监听器。
PRAGMA 配置沿用旧同步架构的最佳实践：
- journal_mode=WAL
- foreign_keys=ON
- busy_timeout=30000
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool


def _register_pragma_listeners(engine: AsyncEngine) -> None:
    """
    为 engine 的底层同步引擎注册 SQLite PRAGMA 事件监听器。

    :param engine: 异步引擎实例
    :type engine: AsyncEngine
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


def _build_sqlite_engine_kwargs(path_str: str) -> dict[str, Any]:
    """构造 SQLite 引擎参数。"""
    if path_str == ":memory:":
        # 内存库仍使用 StaticPool，保证同一引擎内的测试连接共享同一内存数据库。
        return {"poolclass": StaticPool}

    # 文件型 SQLite 使用默认队列池，让不同 session / request 可以获取独立物理连接。
    # 显式启用 rollback reset，避免连接回到池中后残留事务状态。
    return {"pool_reset_on_return": "rollback"}



def create_async_engine_factory(
    db_path: Union[str, Path],
) -> AsyncEngine:
    """
    创建配置好的 AsyncEngine 实例。

    :param db_path: 数据库文件路径，或 ``":memory:"`` 表示内存数据库
    :type db_path: Union[str, Path]
    :returns: 已注册 PRAGMA 监听器的 AsyncEngine
    :rtype: AsyncEngine
    """
    path_str = str(db_path)
    if path_str == ":memory:":
        url = "sqlite+aiosqlite:///:memory:"
    else:
        url = f"sqlite+aiosqlite:///{path_str}"

    engine_kwargs: dict[str, Any] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        engine_kwargs.update(_build_sqlite_engine_kwargs(path_str))

    engine = create_async_engine(url, **engine_kwargs)

    _register_pragma_listeners(engine)
    return engine
