"""
nonebot-plugin-zikequote3 新插件入口（dishka DI 版本）。

替代旧的 __init__.py，消除 ``from .imports import *`` 全局单例模式，
改用 dishka AsyncContainer 管理所有依赖的生命周期。

生命周期：
- driver.on_startup: 创建数据库表 → 组装 DI 容器 → 绑定到 NoneBot Driver
- driver.on_shutdown: 由 setup_dishka 自动关闭容器，释放连接池
- 模块导入时: matcher 定义（on_command 等）自动注册到 NoneBot
"""

from dishka import AsyncContainer
from nonebot import get_driver, require, logger
from nonebot.plugin import PluginMetadata

from .config import ConfigPath

# ---------------------------------------------------------------------------
# require 声明 —— 保留原 imports.py 中的全部 require
# ---------------------------------------------------------------------------
require("nonebot_plugin_localstore")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_alconna")
require("nonebot_plugin_waiter")
require("nonebot_plugin_access_control_api")

# ---------------------------------------------------------------------------
# 插件元数据
# ---------------------------------------------------------------------------
__plugin_meta__ = PluginMetadata(
    name="ZikeQuote3",
    description=(
        "LLM 介入，功能丰富的群聊语录自动收集与管理插件，"
        "支持自动收集、后台管理、生成排行榜、展示等功能"
    ),
    usage=(
        "ZikeQuote3 基于 NoneBot 开发，便于群聊语录自动收集与管理，"
        "支持通过 LLM 自动收集群聊消息作为语录、手动管理语录、"
        "以及多种方式查看等功能。"
    ),
    type="application",
    homepage="https://github.com/LifeCheckpoint/nonebot_plugin_zikequote3",
    config=ConfigPath,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "LifeCheckpoint",
        "version": "0.5.0alpha2",
    },
)

# ---------------------------------------------------------------------------
# 生命周期钩子
# ---------------------------------------------------------------------------
driver = get_driver()

@driver.on_startup
async def _startup() -> None:
    """
    启动时初始化：
    1. 导入所有 ORM 模型（确保 Base.metadata 注册全部表）
    2. 创建 AsyncEngine 并执行 create_all 建表
    3. 组装 dishka 容器并绑定到 NoneBot Driver
    """
    from pathlib import Path

    import tomlkit

    from .config import ConfigPath, parse_config_from_toml
    from .paths import PluginPath
    from .di import create_container
    from .di.nonebot_integration import setup_dishka
    from .database.sa.base import Base
    from .database.sa.engine import create_async_engine_factory

    # 导入全部 ORM 模型，触发 Base.metadata 注册
    from .database.sa import models as _models  # noqa: F401

    # 0) 读取默认配置以获取 render_device_factor
    from nonebot import get_plugin_config

    cfg_file = get_plugin_config(ConfigPath).config_toml
    default_cfg = parse_config_from_toml(
        tomlkit.parse(Path(cfg_file).read_text(encoding="utf-8"))
    )

    # 初始化 Sentry 错误追踪
    from .utils.sentry_init import init_sentry
    init_sentry(default_cfg.sentry.dsn_path)

    # 创建引擎并初始化数据库表
    engine = create_async_engine_factory(PluginPath.data_db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()  # 临时引擎，建表后释放

    # 创建 DI 容器
    vector_db_path = PluginPath.data_cache_path / "vector_db"
    container = create_container(
        db_path=PluginPath.data_db_path,
        image_store_path=PluginPath.data_image_root,
        render_device_factor=default_cfg.showcase.render_device_factor,
        embedding_config=default_cfg.embedding,
        llm_config=default_cfg.llm,
        vector_db_path=vector_db_path,
    )

    # 配置完整性修复
    from .services.config_service import ConfigService

    async with container() as request_ctx:
        config_svc = await request_ctx.get(ConfigService)
        await config_svc.fix_config_integrity()

    # 绑定到 NoneBot Driver
    setup_dishka(container, driver)

    # 启动时检查向量索引模型一致性
    if default_cfg.embedding.enabled:
        await _check_vector_index_consistency(container)

async def _check_vector_index_consistency(container: AsyncContainer) -> None:
    """启动时检查向量索引的模型一致性。"""
    from .vector_search.search_service import VectorSearchService

    try:
        async with container() as request_scope:
            svc = await request_scope.get(VectorSearchService)
            if svc is None:
                return
            consistent = await svc.check_model_consistency()
            if not consistent:
                logger.warning(
                    "⚠️ 向量索引模型不一致！当前配置的 embedding 模型或维度与已存储的索引不匹配。"
                    "模糊搜索功能暂不可用，请执行 /重建语录索引 --all 重建索引。"
                )
            else:
                count = await svc.get_index_count()
                if count > 0:
                    logger.info("向量索引就绪，共 %d 条记录", count)
                else:
                    logger.info("向量索引为空，请执行 /重建语录索引 建立索引")
    except Exception as e:
        logger.warning("向量索引一致性检查失败: %s", e)

# ---------------------------------------------------------------------------
# 导入命令模块 —— 触发 matcher 注册（NoneBot2 标准模式）
# ---------------------------------------------------------------------------
from .command import cmds as _cmds  # noqa: E402, F401
