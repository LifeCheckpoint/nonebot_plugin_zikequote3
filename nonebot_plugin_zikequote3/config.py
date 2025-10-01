from typing import List, Literal
from pathlib import Path
from pydantic import BaseModel, Field
import tomlkit
from tomlkit.items import Table

class ConfigPath(BaseModel):
    config_toml: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "config.toml"),
        description="配置文件路径"
    )

# 具体配置模型

class GeneralConfig(BaseModel):
    enable_zikequote3: bool = True
    check_intergrity: bool = True

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
    enable_groups: List[int] = Field(default_factory=list)

class LLMConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key_path: str = "utils/api_key"
    model: str = "deepseek/deepseek-v3.2-exp"
    temperature: float = 0.2
    max_retries: int = 3

class ConfigSchema(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    collecting: CollectingConfig = Field(default_factory=CollectingConfig)
    fetching: FetchingConfig = Field(default_factory=FetchingConfig)
    showcase: ShowcaseConfig = Field(default_factory=ShowcaseConfig)
    permission: PermissionConfig = Field(default_factory=PermissionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

# 模型转换辅助函数

def load_config_from_toml(toml_doc: tomlkit.TOMLDocument) -> ConfigSchema:
    return ConfigSchema.model_validate(toml_doc)