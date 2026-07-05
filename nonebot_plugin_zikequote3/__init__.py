"""
nonebot-plugin-zikequote3 插件入口（dishka DI 版本）。

生命周期：
- driver.on_startup: 读取并校验配置 → 初始化基础设施 → 执行 Alembic 升级 → 组装 DI 容器
- driver.on_shutdown: 由 setup_dishka 自动关闭容器，释放连接池
- 模块导入时: matcher 定义（on_command 等）自动注册到 NoneBot
"""

from dishka import AsyncContainer
from nonebot import get_driver, logger, require
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
        "version": "0.5.0",
    },
)

# ---------------------------------------------------------------------------
# 生命周期钩子
# ---------------------------------------------------------------------------
driver = get_driver()


@driver.on_startup
async def _startup() -> None:
    """启动时初始化插件依赖。"""
    from nonebot import get_plugin_config

    from .config import ConfigLoadError, load_config_from_path
    from .database.alembic_runtime import (
        DatabaseMigrationError,
        migrate_database_to_head,
    )
    from .di import create_container
    from .di.nonebot_integration import setup_dishka
    from .paths import PluginPath
    from .services.config_service import ConfigService

    config_path = get_plugin_config(ConfigPath).zikequote3_config_toml

    try:
        default_cfg = load_config_from_path(config_path)

        await migrate_database_to_head(PluginPath.data_db_path)

        container = create_container(
            db_path=PluginPath.data_db_path,
            image_store_path=PluginPath.data_image_root,
            render_device_factor=default_cfg.showcase.render_device_factor,
            default_config=default_cfg,
            embedding_config=default_cfg.embedding,
            llm_config=default_cfg.llm,
            vector_db_path=PluginPath.data_vector_db_path,
        )

        async with container() as request_ctx:
            config_svc = await request_ctx.get(ConfigService)
            await config_svc.fix_config_integrity()

        setup_dishka(container, driver)

        if default_cfg.embedding.enabled:
            await _check_vector_index_consistency(container)
    except (ConfigLoadError, DatabaseMigrationError) as exc:
        logger.opt(exception=exc).critical("ZikeQuote3 启动失败: {}", exc)
        raise
    except Exception as exc:  # pragma: no cover - 启动期诊断兜底
        logger.opt(exception=exc).critical("ZikeQuote3 启动阶段出现未预期异常: {}", exc)
        raise


async def _check_vector_index_consistency(container: AsyncContainer) -> None:
    """启动时检查向量索引的模型一致性。"""
    from .vector_search.capability import VectorSearchCapability

    try:
        async with container() as request_scope:
            svc = await request_scope.get(VectorSearchCapability)
            if not svc.get_status().available:
                logger.warning(
                    "向量搜索基础设施未就绪，跳过一致性检查: {}",
                    svc.get_unavailable_reason() or "未知原因",
                )
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
                    logger.info("向量索引就绪，共 {} 条记录", count)
                else:
                    logger.info("向量索引为空，请执行 /重建语录索引 建立索引")
    except Exception as e:
        logger.opt(exception=e).warning("向量索引一致性检查失败: {}", e)


# ---------------------------------------------------------------------------
# 导入命令模块 —— 触发 matcher 注册（NoneBot2 标准模式）
# ---------------------------------------------------------------------------
from .command import cmds as _cmds  # noqa: E402, F401
