"""
数据库相关的 dishka Provider。

提供 AsyncEngine（APP 作用域单例）和 AsyncSession（REQUEST 作用域，yield 模式自动关闭）。
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

    构造参数:
        db_path: 数据库文件路径，或 ":memory:" 表示内存数据库。
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        super().__init__()
        self._db_path = db_path

    @provide(scope=Scope.APP)
    def provide_engine(self) -> AsyncEngine:
        """创建 APP 级别的 AsyncEngine 单例。"""
        return create_async_engine_factory(self._db_path)

    @provide(scope=Scope.APP)
    def provide_session_factory(
        self, engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        """创建 APP 级别的 async_sessionmaker 单例。"""
        return create_async_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def provide_session(
        self, session_factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        """
        每次 REQUEST 作用域提供一个 AsyncSession。

        使用 yield 模式确保作用域结束时 session 被正确关闭。
        """
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
