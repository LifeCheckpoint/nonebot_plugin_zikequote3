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

    Args:
        llm_config: 群组级别的 LLM 配置（包含 base_url / max_retries / model 等）。
        api_key_path: API key 文件路径（相对或绝对）。
            为 ``None`` 时使用 ``llm_config.api_key_path``。
        plugin_root: 插件根目录，用于解析相对路径。
            为 ``None`` 时使用 ``PluginPath.plugin_root``。
    """
    resolved_api_key_path = Path(api_key_path or llm_config.api_key_path)
    resolved_plugin_root = plugin_root or PluginPath.plugin_root

    api_key: str = (
        resolved_api_key_path
        if resolved_api_key_path.is_absolute()
        else (resolved_plugin_root / resolved_api_key_path)
    ).read_text(encoding="utf-8").strip()

    client = AsyncOpenAI(
        max_retries=llm_config.max_retries,
        base_url=llm_config.base_url,
        api_key=api_key,
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

    Args:
        model: 已创建的 LLM 模型实例。
        content: 用户提示词文本。
        temperature: 采样温度，默认 ``0.2``。

    Returns:
        ``(模型响应文本, 使用量信息)``。
    """
    model_response = await model_request(
        model=model,
        messages=[ModelRequest.user_text_prompt(content)],
        model_settings=ModelSettings(temperature=temperature),
    )

    if not model_response.parts or model_response.parts[0] is None:
        raise RuntimeError("模型返回为空")

    if not isinstance(model_response.parts[0].content, str):  # type: ignore
        raise RuntimeError("模型返回格式错误")

    return model_response.parts[0].content, model_response.usage  # type: ignore


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

    Args:
        model: 已创建的 LLM 模型实例。
        content: 用户提示词文本。
        response_model: 期望的 Pydantic 响应模型类型。
        temperature: 采样温度，默认 ``0.2``。

    Returns:
        ``(Pydantic 模型实例, 使用量信息)``。
    """
    from ..utils.json_parser import llm_json_parse_model
    model_response, usage = await send_llm_request(
        model, content, temperature=temperature,
    )
    return llm_json_parse_model(response_model, model_response), usage