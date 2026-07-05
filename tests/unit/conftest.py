"""
单元测试 conftest —— Repository 测试用的内存数据库 fixtures。

提供基于 SQLAlchemy async + aiosqlite 的内存数据库基础设施。
init_db fixture 会通过 Base.metadata.create_all 创建所有 ORM 模型对应的表。

注意：
- 覆盖了 nonebug 的 _nonebot_init fixture，单元测试不需要 nonebot 环境。
- 在导入插件子模块前，预注册父包 stub 以绕过 nonebot 初始化链。
"""

import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# 预注册父包 stub，避免导入 database.sa 时触发
# nonebot_plugin_zikequote3/__init__.py → nonebot 初始化链
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

_services_root = _plugin_root / "services"
if "nonebot_plugin_zikequote3.services" not in sys.modules:
    _stub_svc = types.ModuleType("nonebot_plugin_zikequote3.services")
    _stub_svc.__path__ = [str(_services_root)]
    sys.modules["nonebot_plugin_zikequote3.services"] = _stub_svc

_vector_search_root = _plugin_root / "vector_search"
if "nonebot_plugin_zikequote3.vector_search" not in sys.modules:
    _stub_vs = types.ModuleType("nonebot_plugin_zikequote3.vector_search")
    _stub_vs.__path__ = [str(_vector_search_root)]
    sys.modules["nonebot_plugin_zikequote3.vector_search"] = _stub_vs

# stub nonebot_plugin_localstore 以避免 paths.py 触发 nonebot 初始化
if "nonebot_plugin_localstore" not in sys.modules:
    _stub_store = types.ModuleType("nonebot_plugin_localstore")
    setattr(_stub_store, "get_plugin_data_dir", lambda: Path("/tmp/zikequote3/data"))
    setattr(_stub_store, "get_plugin_cache_dir", lambda: Path("/tmp/zikequote3/cache"))
    sys.modules["nonebot_plugin_localstore"] = _stub_store

# ---------------------------------------------------------------------------
# 现在可以安全导入 SA 基础设施模块
# ---------------------------------------------------------------------------
import pytest

from nonebot_plugin_zikequote3.database.sa import (
    create_async_engine_factory,
    create_async_session_factory,
)
from nonebot_plugin_zikequote3.database.sa.base import Base

# 导入所有 ORM 模型，确保 Base.metadata 注册了全部表
from nonebot_plugin_zikequote3.database.sa.models import (  # noqa: F401
    # 基础实体
    GroupMemberModel,
    GroupModel,
    GroupNicknameModel,
    UserModel,
    UserNicknameModel,
    # 业务实体
    GroupConfigModel,
    ImageModel,
    MsgIdQuoteIdMapModel,
    MsgQueueModel,
    QueueGroupMessageCountModel,
    QuoteModel,
    ReviewModel,
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


@pytest.fixture
async def async_engine():
    """为每个测试创建独立的异步内存数据库引擎（使用 SA 工厂，含 PRAGMA 监听器）。"""
    engine = create_async_engine_factory(":memory:")
    yield engine
    await engine.dispose()


@pytest.fixture
def async_session_factory(async_engine):
    """为每个测试创建独立的异步 session 工厂（使用 SA 工厂）。"""
    return create_async_session_factory(async_engine)


@pytest.fixture
async def init_db(async_engine):
    """
    为每个测试初始化独立数据库表结构。

    通过 ``Base.metadata.create_all`` 根据已注册的 ORM 模型创建所有表，
    避免已提交状态在不同测试用例之间泄漏。
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
