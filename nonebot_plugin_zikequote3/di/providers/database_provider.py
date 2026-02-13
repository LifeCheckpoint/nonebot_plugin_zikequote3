"""
数据库相关的 dishka Provider。

提供 AsyncEngine（APP 作用域单例）和 AsyncSession（REQUEST 作用域，含事务 commit/rollback 管理）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Union

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from nonebot_plugin_zikequote3.database.sa.engine import create_async_engine_factory
from nonebot_plugin_zikequote3.database.sa.session import create_async_session_factory


class DatabaseProvider(Provider):
    """
    数据库依赖提供者。

    :param db_path: 数据库文件路径，或 ``":memory:"`` 表示内存数据库
    :type db_path: Union[str, Path]
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        super().__init__()
        self._db_path = db_path

    @provide(scope=Scope.APP)
    def provide_engine(self) -> AsyncEngine:
        """
        创建 APP 级别的 AsyncEngine 单例。

        :returns: 异步数据库引擎
        :rtype: AsyncEngine
        """
        return create_async_engine_factory(self._db_path)

    @provide(scope=Scope.APP)
    def provide_session_factory(
        self, engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        """
        创建 APP 级别的 async_sessionmaker 单例。

        :param engine: 异步数据库引擎
        :type engine: AsyncEngine
        :returns: 异步会话工厂
        :rtype: async_sessionmaker[AsyncSession]
        """
        return create_async_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def provide_session(
        self, session_factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        """
        每次 REQUEST 作用域提供一个 AsyncSession，并管理事务生命周期。

        事务管理策略（Unit of Work 模式）：

        - Repository 层仅使用 ``flush()`` 将变更写入数据库缓冲区，不负责提交事务。
        - 当 REQUEST 作用域正常退出时，本方法自动调用 ``commit()`` 提交事务。
        - 当 REQUEST 作用域因异常退出时，本方法自动调用 ``rollback()`` 回滚事务。
        - 无论成功或失败，最终都会调用 ``close()`` 释放连接资源。

        :param session_factory: 异步会话工厂
        :type session_factory: async_sessionmaker[AsyncSession]
        :returns: 异步会话迭代器
        :rtype: AsyncIterator[AsyncSession]
        """
        session = session_factory()
        try:
            yield session
            # dishka 在关闭 scope 时可能通过 asend() 而非 athrow() 恢复 generator，
            # 导致上游异常不会被 except 捕获。此时 session 可能处于 flush 失败状态，
            # 直接 commit 会触发 PendingRollbackError。因此在 commit 前检查 session 状态。
            if session.is_active and not session.in_nested_transaction():
                await session.commit()
            else:
                await session.rollback()
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()
