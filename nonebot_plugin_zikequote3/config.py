from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal
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

