"""
LLM 客户端模块。

提供 LLM 模型实例创建与请求发送的工具函数。
"""
import httpx

from ..config import LLMConfig
from ..paths import PluginPath

from openai import AsyncOpenAI

# Fix Pydantic - OpenAI 库兼容性问题修复: object of type 'Omit' has no len()
try:
    from openai import Omit
    if not hasattr(Omit, '__len__'):
        Omit.__len__ = lambda self: 0 # type: ignore
except ImportError:
    pass

from pathlib import Path
from pydantic import BaseModel
from pydantic_ai.direct import model_request
from pydantic_ai.messages import ModelRequest
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage
from typing import Tuple, TypeVar, Type

def create_model(
    llm_config: LLMConfig,
    *,
    api_key_path: str | None = None,
    plugin_root: Path | None = None,
) -> Model:
    """
    创建 LLM 模型实例，可调整该函数以支持不同模型客户端。

    :param llm_config: 群组级别的 LLM 配置（包含 base_url / max_retries / model 等）
    :type llm_config: LLMConfig
    :param api_key_path: API key 文件路径（相对或绝对），
        为 ``None`` 时使用 ``llm_config.api_key_path``
    :type api_key_path: str | None
    :param plugin_root: 插件根目录，用于解析相对路径，
        为 ``None`` 时使用 ``PluginPath.plugin_root``
    :type plugin_root: Path | None
    :returns: LLM 模型实例
    :rtype: Model
    """
    resolved_api_key_path = Path(api_key_path or llm_config.api_key_path)
    resolved_plugin_root = plugin_root or PluginPath.plugin_root

    api_key: str = (
        resolved_api_key_path
        if resolved_api_key_path.is_absolute()
        else (resolved_plugin_root / resolved_api_key_path)
    ).read_text(encoding="utf-8").strip()

    if not api_key:
        raise ValueError(
            f"API key file is empty or contains only whitespace: {resolved_api_key_path}"
        )

    client = AsyncOpenAI(
        max_retries=llm_config.max_retries,
        base_url=llm_config.base_url,
        api_key=api_key,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )

    return OpenAIChatModel(
        llm_config.model, provider=OpenAIProvider(openai_client=client),
    )

async def send_llm_request(
    model: Model,
    content: str,
    *,
    temperature: float = 0.2,
) -> Tuple[str, RequestUsage]:
    """
    发送单次请求到 LLM 模型并获取响应。

    :param model: 已创建的 LLM 模型实例
    :type model: Model
    :param content: 用户提示词文本
    :type content: str
    :param temperature: 采样温度，默认 ``0.2``
    :type temperature: float
    :returns: ``(模型响应文本, 使用量信息)``
    :rtype: Tuple[str, RequestUsage]
    :raises RuntimeError: 当模型返回为空或格式错误时抛出
    """
    model_response = await model_request(
        model=model,
        messages=[ModelRequest.user_text_prompt(content)],
        model_settings=ModelSettings(temperature=temperature),
    )

    if not model_response.parts:
        raise RuntimeError("模型返回为空")

    for part in model_response.parts:
        if getattr(part, "part_kind", None) == "text":
            content = getattr(part, "content", None)
            if not isinstance(content, str):
                raise RuntimeError("模型返回文本格式错误")
            return content, model_response.usage

    raise RuntimeError("模型未返回文本内容")


T = TypeVar('T', bound=BaseModel)


async def send_llm_request_json2model(
    model: Model,
    content: str,
    response_model: Type[T],
    *,
    temperature: float = 0.2,
) -> Tuple[T, RequestUsage]:
    """
    发送单次请求到 LLM 模型并获取响应，将返回 JSON 转换为 Pydantic 模型实例。

    :param model: 已创建的 LLM 模型实例
    :type model: Model
    :param content: 用户提示词文本
    :type content: str
    :param response_model: 期望的 Pydantic 响应模型类型
    :type response_model: Type[T]
    :param temperature: 采样温度，默认 ``0.2``
    :type temperature: float
    :returns: ``(Pydantic 模型实例, 使用量信息)``
    :rtype: Tuple[T, RequestUsage]
    """
    from ..utils.json_parser import llm_json_parse_model
    model_response, usage = await send_llm_request(
        model, content, temperature=temperature,
    )
    return llm_json_parse_model(response_model, model_response), usage