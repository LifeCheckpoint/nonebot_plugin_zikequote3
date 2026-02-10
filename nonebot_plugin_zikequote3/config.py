"""
插件配置模型定义。

基于 Pydantic 定义插件的全部配置项，支持从 TOML 文件解析。
"""

from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal
import tomlkit


class ConfigPath(BaseModel):
    """
    NoneBot 环境变量级配置，指定 TOML 配置文件路径。

    :param config_toml: 配置文件路径，默认为插件目录下的 ``config.toml``
    :type config_toml: str
    """

    config_toml: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "config.toml"),
        description="配置文件路径"
    )

class GeneralConfig(BaseModel):
    """通用配置（预留扩展）。"""


class CollectingConfig(BaseModel):
    """语录自动收集相关配置。"""

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
    """语录抽取算法相关配置。"""

    algorithm: str = "IFW --lambda 1.0"


class ShowcaseConfig(BaseModel):
    """语录展示相关配置。"""

    max_rank_user_num: int = 40
    quote_num_per_page: int = 20
    max_quotes_in_list: int = 50
    comment_show_method: Literal["no", "noai", "all"] = "noai"
    hitokoto_url: str = "https://v1.hitokoto.cn"
    render_device_factor: float = 2.0
    quote_content_max_length: int = 500
    """语录列表中单条语录内容的最大显示字符数，超过则截断并显示 ``"..."``，``0`` 表示不限制。"""


class CommentConfig(BaseModel):
    """语录评论相关配置。"""

    enable_comment_without_prefix: bool = True

class LLMConfig(BaseModel):
    """LLM 服务相关配置。"""

    base_url: str = "https://openrouter.ai/api/v1"
    api_key_path: str = "utils/api_key"
    model: str = "deepseek/deepseek-v3.2-exp"
    temperature: float = 0.2
    max_retries: int = 3


class SentryConfig(BaseModel):
    """Sentry 错误追踪相关配置。"""

    dsn_path: str = "utils/sentry_dsn"


class ConfigureConfig(BaseModel):
    """配置管理自身的元配置。"""

    nonreloadable_items: List[str] = Field(
        default_factory=lambda: [
            "llm.api_key_path",
            "sentry.dsn_path",
            "configure.nonreloadable_items",
        ]
    )
    cfg_version: int = 5

class ConfigSchema(BaseModel):
    """
    插件完整配置模型。

    聚合所有子配置分组，每个字段对应 TOML 文件中的一个 section。
    """

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    collecting: CollectingConfig = Field(default_factory=CollectingConfig)
    fetching: FetchingConfig = Field(default_factory=FetchingConfig)
    showcase: ShowcaseConfig = Field(default_factory=ShowcaseConfig)
    comment: CommentConfig = Field(default_factory=CommentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sentry: SentryConfig = Field(default_factory=SentryConfig)
    configure: ConfigureConfig = Field(default_factory=ConfigureConfig)


def parse_config_from_toml(toml_doc: tomlkit.TOMLDocument) -> ConfigSchema:
    """
    将 TOML 文档解析为 :class:`ConfigSchema` 实例。

    :param toml_doc: 已解析的 TOML 文档对象
    :type toml_doc: tomlkit.TOMLDocument
    :returns: 插件配置实例
    :rtype: ConfigSchema
    """
    return ConfigSchema.model_validate(toml_doc)

