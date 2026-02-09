"""
AsyncSession 工厂函数。

创建 async_sessionmaker 实例，用于生产 AsyncSession。
expire_on_commit=False 避免 commit 后访问属性时触发隐式查询。
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


def create_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """
    创建配置好的 async_sessionmaker 实例。

    参数:
        engine: 已配置的 AsyncEngine。

    返回:
        async_sessionmaker 实例，调用即可获得 AsyncSession。
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
