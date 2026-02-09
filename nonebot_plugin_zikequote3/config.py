from nonebot import get_plugin_config, logger
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Any, Dict
import tomlkit

class ConfigPath(BaseModel):
    config_toml: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "config.toml"),
        description="配置文件路径"
    )

# 具体配置模型

class GeneralConfig(BaseModel):
    pass

class CollectingConfig(BaseModel):
    enable_auto_collect: bool = True
    pickup_interval: int = 80
    msg_max_length: int = 35
    at_least_selections: int = 0
    at_most_selections: int = 3
    enable_duplicate: bool = False
    enable_image_collection: bool = True
    img_max_sidelength: int = 3840
    img_max_size_mb: float = 5
    update_personal_info_probability: float = 0.05

class FetchingConfig(BaseModel):
    # enable_cross_group_fetching: bool = False
    algorithm: str = "IFW --lambda 1.0"

class ShowcaseConfig(BaseModel):
    max_rank_user_num: int = 40
    quote_num_per_page: int = 20
    max_quotes_in_list: int = 50
    comment_show_method: Literal["no", "noai", "all"] = "noai"
    hitokoto_url: str = "https://v1.hitokoto.cn"
    render_device_factor: float = 2.0

class CommentConfig(BaseModel):
    enable_comment_without_prefix: bool = True

class LLMConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key_path: str = "utils/api_key"
    model: str = "deepseek/deepseek-v3.2-exp"
    temperature: float = 0.2
    max_retries: int = 3

class SentryConfig(BaseModel):
    dsn_path: str = "utils/sentry_dsn"

class ConfigureConfig(BaseModel):
    nonreloadable_items: List[str] = Field(
        default_factory=lambda: [
            "llm.api_key_path",
            "sentry.dsn_path",
            "configure.nonreloadable_items",
        ]
    )
    cfg_version: int = 4

class ConfigSchema(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    collecting: CollectingConfig = Field(default_factory=CollectingConfig)
    fetching: FetchingConfig = Field(default_factory=FetchingConfig)
    showcase: ShowcaseConfig = Field(default_factory=ShowcaseConfig)
    comment: CommentConfig = Field(default_factory=CommentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sentry: SentryConfig = Field(default_factory=SentryConfig)
    configure: ConfigureConfig = Field(default_factory=ConfigureConfig)

# 模型转换
def parse_config_from_toml(toml_doc: tomlkit.TOMLDocument) -> ConfigSchema:
    return ConfigSchema.model_validate(toml_doc)

def fix_config_integrity(default_toml: tomlkit.TOMLDocument, group_toml: tomlkit.TOMLDocument) -> bool:
    """
    修复群组配置的完整性，确保数据库中的配置包含所有本地默认配置项
    
    Args:
        default_toml: 本地默认配置的TOML文档
        group_toml: 群组配置的TOML文档
    
    Returns:
        bool: 配置是否被修改
    """
    changed = False
    
    default_cfg_version = default_toml.get("configure", {}).get("cfg_version", -1)
    group_cfg_version = group_toml.get("configure", {}).get("cfg_version", -1)

    if default_cfg_version != group_cfg_version:
        logger.info(f"配置版本不一致，准备从 v{group_cfg_version} 迁移到 v{default_cfg_version}")
        new_toml = default_toml.copy()
        for section_name in default_toml.keys():
            if section_name in group_toml:
                for key_name in default_toml[section_name].keys(): # type: ignore
                    if key_name in group_toml[section_name]:
                        new_toml[section_name][key_name] = group_toml[section_name][key_name] # type: ignore
        
        # 保留新版本的配置版本号
        new_toml["configure"]["cfg_version"] = default_toml["configure"]["cfg_version"] # type: ignore

        # 清除旧的 group_toml 并将 new_toml 的内容复制过去
        for key in list(group_toml.keys()):
            del group_toml[key]
        for key, value in new_toml.items():
            group_toml[key] = value

        changed = True
        logger.info(f"配置已迁移到 v{default_cfg_version}")

    return changed

def reload_config():
    """
    加载 / 重载所有自定义群组配置
    """
    from .utils.defaulting_dict import DefaultingDict

    cfg_file = get_plugin_config(ConfigPath).config_toml

    if not Path(cfg_file).is_file():
        logger.error(f"默认配置文件 {cfg_file} 不存在")
        raise FileNotFoundError(f"默认配置文件 {cfg_file} 不存在")
        
    _default_cfg_toml = tomlkit.parse(Path(cfg_file).read_text(encoding="utf-8"))
    _defaul_cfg = parse_config_from_toml(_default_cfg_toml)

    # 从数据库读取所有自定义群组配置
    from .imports import db

    # 预先初始化，避免 except 分支导致变量未绑定
    _cfg_toml: DefaultingDict[int, tomlkit.TOMLDocument] = DefaultingDict(_default_cfg_toml, {})
    _cfg: DefaultingDict[int, ConfigSchema] = DefaultingDict(_defaul_cfg, {})

    try:
        group_configs = db.dao.get_group_configs_dao().get_all_group_configs()

        for gc in group_configs:
            try:
                group_toml = tomlkit.parse(gc.toml_config)
                
                # 检查并修复配置完整性
                if fix_config_integrity(_default_cfg_toml, group_toml):
                    # 配置有变化，更新数据库
                    try:
                        db.dao.get_group_configs_dao().update_or_create_group_config(
                            str(gc.group_id), tomlkit.dumps(group_toml)
                        )
                        logger.info(f"已修复群 {gc.group_id} 的配置完整性")
                    except Exception as e:
                        logger.error(f"更新群 {gc.group_id} 的配置失败: {e}")
                
                _cfg_toml[int(gc.group_id)] = group_toml
                _cfg[int(gc.group_id)] = parse_config_from_toml(group_toml)
            except Exception as e:
                logger.error(f"解析群 {gc.group_id} 的自定义配置失败，其将使用默认配置: {e}")

    except Exception as e:
        logger.error(f"加载群组自定义配置失败，将使用默认配置: {e}")
        group_configs = {}

    return _default_cfg_toml, _defaul_cfg, _cfg_toml, _cfg

def modify_group_config(group_id: int, schema_str: str, new_value: Any, reload: bool = True) -> None:
    """
    修改指定群组的配置，如果群组自定义配置不存在，则创建一个新的配置。

    :param _cfg_toml: 当前所有群组的配置字典
    :param _default_cfg_toml: 默认配置的 toml 文本
    :param group_id: 群号
    :param schema_str: 配置的模式文本。
    
        例如，`showcase.max_quotes_in_list` 表示修改 `showcase` 模式下的 `max_quotes_in_list` 配置项
    :param new_value: 新的配置值
    :param reload: 是否在修改后重新加载配置

    :raises ValueError: 如果指定的配置项不存在或类型不匹配
    :raises Exception: 其他异常
    """
    from .imports import db, _cfg_toml, _default_cfg_toml, cfg, default_cfg, notify_reload_config

    # 通过修改 toml 并写入 db 实现
    group_toml = _cfg_toml.get(group_id, _default_cfg_toml)
    
    # 解析设置项模式
    nonreloadable_cfgs_schema = default_cfg.configure.nonreloadable_items
    if schema_str in nonreloadable_cfgs_schema:
        raise ValueError(f"配置项模式 '{schema_str}' 不可修改")
    schema_parts = schema_str.split('.')

    if len(schema_parts) != 2:
        raise ValueError(f"配置项模式层数不为 2")
    
    section, key = schema_parts
    if section not in group_toml:
        raise ValueError(f"配置项模式 '{section}' 不存在")
    
    if key not in group_toml[section]: # type: ignore
        raise ValueError(f"配置项 '{key}' 在模式 '{section}' 中不存在")

    try:
        group_toml[section][key] = new_value # type: ignore
    except Exception as e:
        raise ValueError(f"解析配置项模式失败: {e}")
    
    # 写入数据库
    try:
        db.dao.get_group_configs_dao().update_or_create_group_config(
            str(group_id), tomlkit.dumps(group_toml)
        )
    except Exception as e:
        raise Exception(f"配置项写入数据库失败: {e}")
    
    if reload:
        notify_reload_config()

    logger.info(f"群 {group_id} 的配置项 '{schema_str}' 已更新为 '{new_value}'")

def batch_modify_group_config(group_ids: List[int], schema_str: str, new_value: Any, reload: bool = True) -> int:
    """
    批量修改指定群组的配置

    :param group_ids: 群号列表
    :param schema_str: 配置的模式文本
    :param new_value: 新的配置值
    :param reload: 是否在修改后重新加载配置

    :return: 成功修改的群组数量
    """
    success_count = 0
    for gid in group_ids:
        try:
            modify_group_config(gid, schema_str, new_value, reload)
            success_count += 1
        except Exception as e:
            logger.error(f"修改群 {gid} 的配置项失败: {e}")
    logger.info(f"已调整 {success_count} 个群的配置项 '{schema_str}' 至 '{new_value}'")
    return success_count