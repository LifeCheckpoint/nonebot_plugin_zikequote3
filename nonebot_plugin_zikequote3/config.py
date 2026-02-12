"""
插件配置模型定义。

基于 Pydantic 定义插件的全部配置项，支持从 TOML 文件解析。

如有修改，注意同步 `config.toml` 中的配置模型
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


class EmbeddingConfig(BaseModel):
    """Embedding 服务配置。

    控制模糊语义搜索功能的模型、API 连接和搜索行为参数。

    :param enabled: 是否启用模糊语义搜索功能，默认为 ``False``。
    :type enabled: bool
    :param model: Embedding 模型名称。
    :type model: str
    :param dimensions: 模型输出向量维度。
    :type dimensions: int
    :param base_url: Embedding API 地址，为 ``None`` 时复用 ``llm.base_url``。
    :type base_url: str | None
    :param api_key_path: Embedding API Key 文件路径，为 ``None`` 时复用 ``llm.api_key_path``。
    :type api_key_path: str | None
    :param batch_size: 批量向量化时每批的文本数量。
    :type batch_size: int
    :param max_retries: 请求失败重试次数。
    :type max_retries: int
    :param default_top_n: 默认返回的搜索结果数量。
    :type default_top_n: int
    :param default_threshold: 默认相似度阈值，``0`` 表示不过滤。
    :type default_threshold: float
    """

    enabled: bool = False
    """是否启用模糊语义搜索功能。"""
    model: str = "qwen/qwen3-embedding-8b"
    """Embedding 模型名称。"""
    dimensions: int = 4096
    """模型输出向量维度。"""
    base_url: str | None = None
    """Embedding API 地址，为 None 时复用 llm.base_url。"""
    api_key_path: str | None = None
    """Embedding API Key 文件路径，为 None 时复用 llm.api_key_path。"""
    batch_size: int = 64
    """批量向量化时每批的文本数量。"""
    max_retries: int = 2
    """请求失败重试次数。"""
    default_top_n: int = 10
    """默认返回的搜索结果数量。"""
    default_threshold: float = 0.0
    """默认相似度阈值，0 表示不过滤。"""


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
    cfg_version: int = 6
    """配置版本号，配置变更需要递增以触发自动更新"""

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
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
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

