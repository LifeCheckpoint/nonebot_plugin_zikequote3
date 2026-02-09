"""
单元测试 conftest —— Repository 测试用的内存数据库 fixtures。

提供基于 SQLAlchemy async + aiosqlite 的内存数据库基础设施。
ORM 模型尚未定义，init_db fixture 为占位版本，等子任务 4/5 完成后激活。
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
async def async_engine():
    """创建 session 级别的异步内存数据库引擎。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def async_session_factory(async_engine):
    """创建 session 级别的异步 session 工厂。"""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(scope="session")
async def init_db(async_engine):
    """
    初始化数据库表结构（占位版本）。

    当前 ORM 模型尚未定义，此 fixture 暂时为空操作。
    等子任务 4/5 完成 ORM 模型定义后，替换为：

        from nonebot_plugin_zikequote3.database.orm import Base
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    届时 import 路径需根据实际 ORM 模块位置调整。
    """
    # TODO: 子任务 4/5 完成后激活 metadata.create_all
    yield


@pytest.fixture
async def async_session(async_session_factory, init_db):
    """
    每个测试函数获得独立的 async session。

    测试结束后自动 rollback，确保测试间互不影响。
    """
    async with async_session_factory() as session:
        yield session
        await session.rollback()
