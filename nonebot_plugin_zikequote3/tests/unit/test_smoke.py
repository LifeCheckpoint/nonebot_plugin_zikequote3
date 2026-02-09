"""
冒烟测试 —— 验证新依赖安装成功且基础设施可用。

测试内容：
1. SQLAlchemy async engine 能否正常创建和连接到 :memory: 数据库
2. dishka 能否正常 import
3. aiosqlite 能否正常 import
"""

import pytest


class TestDependencyImports:
    """验证新依赖可以正常导入。"""

    def test_sqlalchemy_import(self):
        """SQLAlchemy 核心模块可导入。"""
        from sqlalchemy import __version__ as sa_version
        from sqlalchemy.ext.asyncio import create_async_engine

        assert sa_version is not None
        assert callable(create_async_engine)

    def test_aiosqlite_import(self):
        """aiosqlite 可导入。"""
        import aiosqlite

        assert aiosqlite is not None

    def test_dishka_import(self):
        """dishka 核心模块可导入。"""
        from dishka import Provider, Scope, make_async_container

        assert Provider is not None
        assert Scope is not None
        assert callable(make_async_container)


class TestAsyncEngineSmoke:
    """验证 SQLAlchemy async engine 基本功能。"""

    async def test_engine_creation(self, async_engine):
        """async_engine fixture 能正常创建。"""
        assert async_engine is not None
        assert str(async_engine.url) == "sqlite+aiosqlite:///:memory:"

    async def test_engine_connect(self, async_engine):
        """能正常连接到内存数据库并执行简单查询。"""
        async with async_engine.connect() as conn:
            result = await conn.exec_driver_sql("SELECT 1")
            row = result.scalar()
            assert row == 1

    async def test_session_factory(self, async_session_factory):
        """async_session_factory fixture 能正常创建 session。"""
        async with async_session_factory() as session:
            result = await session.exec_driver_sql("SELECT 42")
            row = result.scalar()
            assert row == 42
