"""
单元测试 conftest —— Repository 测试用的内存数据库 fixtures。

提供基于 SQLAlchemy async + aiosqlite 的内存数据库基础设施。
ORM 模型尚未定义，init_db fixture 为占位版本，等子任务 4/5 完成后激活。

注意：
- 覆盖了 nonebug 的 _nonebot_init fixture，单元测试不需要 nonebot 环境。
- 在导入插件子模块前，预注册父包 stub 以绕过 nonebot 初始化链。
"""

import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# 预注册父包 stub，避免导入 database.sa 时触发
# nonebot_plugin_zikequote3/__init__.py → imports.py → nonebot 初始化链
# ---------------------------------------------------------------------------
_plugin_root = Path(__file__).resolve().parent.parent.parent / "nonebot_plugin_zikequote3"

if "nonebot_plugin_zikequote3" not in sys.modules:
    _stub_pkg = types.ModuleType("nonebot_plugin_zikequote3")
    _stub_pkg.__path__ = [str(_plugin_root)]
    sys.modules["nonebot_plugin_zikequote3"] = _stub_pkg

_database_root = _plugin_root / "database"
if "nonebot_plugin_zikequote3.database" not in sys.modules:
    _stub_db = types.ModuleType("nonebot_plugin_zikequote3.database")
    _stub_db.__path__ = [str(_database_root)]
    sys.modules["nonebot_plugin_zikequote3.database"] = _stub_db

# ---------------------------------------------------------------------------
# 现在可以安全导入 SA 基础设施模块
# ---------------------------------------------------------------------------
import pytest

from nonebot_plugin_zikequote3.database.sa import (
    create_async_engine_factory,
    create_async_session_factory,
)


@pytest.fixture(scope="session", autouse=True)
def _nonebot_init():
    """覆盖 nonebug 的 _nonebot_init，单元测试不需要 nonebot 环境。"""
    return


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init():
    """覆盖 nonebug 的 after_nonebot_init，单元测试不需要 nonebot 环境。"""
    return


@pytest.fixture(scope="session", autouse=True)
async def nonebug_init():
    """覆盖 nonebug 的 nonebug_init（lifespan），单元测试不需要 nonebot 环境。"""
    yield


@pytest.fixture(scope="session")
async def async_engine():
    """创建 session 级别的异步内存数据库引擎（使用 SA 工厂，含 PRAGMA 监听器）。"""
    engine = create_async_engine_factory(":memory:")
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def async_session_factory(async_engine):
    """创建 session 级别的异步 session 工厂（使用 SA 工厂）。"""
    return create_async_session_factory(async_engine)


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
