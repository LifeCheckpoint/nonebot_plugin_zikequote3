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
    enable_zikequote3: bool = True
    check_intergrity: bool = True
    enable_groups: List[int] = Field(default_factory=list)

class CollectingConfig(BaseModel):
    enable_auto_collect: bool = True
    pickup_interval: int = 80
    msg_max_length: int = 35
    enable_duplicate: bool = False

class FetchingConfig(BaseModel):
    enable_cross_group_fetching: bool = False
    algorithm: Literal["freq", "diversity"] = "freq"

class ShowcaseConfig(BaseModel):
    max_rank_user_num: int = 40
    quote_num_per_page: int = 20
    page_num_limit: int = 5
    comment_show_method: Literal["no", "noai", "all"] = "noai"
    hitokoto_url: str = "https://v1.hitokoto.cn"

class PermissionConfig(BaseModel):
    static_root: List[str] = Field(default_factory=list)

class LLMConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key_path: str = "utils/api_key"
    model: str = "deepseek/deepseek-v3.2-exp"
    temperature: float = 0.2
    max_retries: int = 3

class ConfigureConfig(BaseModel):
    reloadable_items: List[str] = Field(default_factory=list)

class ConfigSchema(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    collecting: CollectingConfig = Field(default_factory=CollectingConfig)
    fetching: FetchingConfig = Field(default_factory=FetchingConfig)
    showcase: ShowcaseConfig = Field(default_factory=ShowcaseConfig)
    permission: PermissionConfig = Field(default_factory=PermissionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    configure: ConfigureConfig = Field(default_factory=ConfigureConfig)

# 模型转换
def parse_config_from_toml(toml_doc: tomlkit.TOMLDocument) -> ConfigSchema:
    return ConfigSchema.model_validate(toml_doc)

def reload_config():
    """
    加载 / 重载所有自定义群组配置
    """
    cfg_file = get_plugin_config(ConfigPath).config_toml

    if not Path(cfg_file).is_file():
        logger.error(f"默认配置文件 {cfg_file} 不存在")
        raise FileNotFoundError(f"默认配置文件 {cfg_file} 不存在")
        
    _default_cfg_toml = tomlkit.parse(Path(cfg_file).read_text(encoding="utf-8"))
    _defaul_cfg = parse_config_from_toml(_default_cfg_toml)

    # 从数据库读取所有自定义群组配置
    from .imports import db
    try:
        group_configs = db.dao.get_group_configs_dao().get_all_group_configs()
        # 转换为字典
        _cfg_toml: Dict[str, tomlkit.TOMLDocument] = {}
        _cfg: Dict[str, ConfigSchema] = {}
        for gc in group_configs:
            try:
                _cfg_toml[gc.group_id] = tomlkit.parse(gc.toml_config)            
                _cfg[gc.group_id] = parse_config_from_toml(_cfg_toml[gc.group_id])
            except Exception as e:
                logger.error(f"解析群 {gc.group_id} 的自定义配置失败，其将使用默认配置: {e}")

    except Exception as e:
        logger.error(f"加载群组自定义配置失败，将使用默认配置: {e}")
        group_configs = {}

    return _default_cfg_toml, _defaul_cfg, _cfg_toml, _cfg

def modify_group_config(group_id: str, schema_str: str, new_value: Any, reload: bool = True) -> None:
    """
    修改指定群组的配置，如果群组自定义配置不存在，则创建一个新的配置。

    :param _cfg_toml: 当前所有群组的配置字典
    :param _default_cfg_toml: 默认配置的 toml 文本
    :param group_id: 群号
    :param schema_str: 配置的模式文本。
    
        例如，`showcase.page_num_limit` 表示修改 `showcase` 模式下的 `page_num_limit` 配置项
    :param new_value: 新的配置值
    :param reload: 是否在修改后重新加载配置

    :raises ValueError: 如果指定的配置项不存在或类型不匹配
    :raises Exception: 其他异常
    """
    from .imports import db, _cfg_toml, _default_cfg_toml, cfg, default_cfg, notify_reload_config

    # 通过修改 toml 并写入 db 实现
    group_toml = _cfg_toml.get(group_id, _default_cfg_toml)
    
    # 解析设置项模式
    try:
        reloadable_cfgs_schema = default_cfg.configure.reloadable_items
        # 检查 schema_str 是否在 reloadable_cfgs_keys 中
        if schema_str not in reloadable_cfgs_schema:
            raise ValueError(f"配置项模式 '{schema_str}' 不存在或不可修改")
        schema_parts = schema_str.split('.')

        if len(schema_parts) != 2:
            raise ValueError(f"配置项模式层数不为 2")
        
        section, key = schema_parts
        group_toml[section][key] = new_value # type: ignore
    except Exception as e:
        raise ValueError(f"解析配置项模式失败: {e}")
    
    # 写入数据库
    try:
        db.dao.get_group_configs_dao().update_or_create_group_config(
            group_id, tomlkit.dumps(group_toml)
        )
    except Exception as e:
        raise Exception(f"配置项写入数据库失败: {e}")
    
    if reload:
        notify_reload_config()
