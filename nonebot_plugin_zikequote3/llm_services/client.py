from ..imports import cfg, default_cfg, _plugin_root

from openai import AsyncOpenAI
from pathlib import Path
from pydantic_ai.direct import model_request
from pydantic_ai.messages import ModelRequest
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage
from typing import Tuple

def create_model(group_id: int) -> Model:
    """
    创建 LLM 模型实例，可调整该函数以支持不同模型客户端
    """
    api_key_path = Path(default_cfg.llm.api_key_path)
    api_key: str = (
        api_key_path if api_key_path.is_absolute() else (_plugin_root / api_key_path)
    ).read_text(encoding="utf-8").strip()

    client = AsyncOpenAI(
        max_retries=cfg[group_id].llm.max_retries,
        base_url=cfg[group_id].llm.base_url,
        api_key=api_key,
    )

    return OpenAIChatModel(cfg[group_id].llm.model, provider=OpenAIProvider(openai_client=client))

async def send_llm_request(group_id: int, model: Model, content: str) -> Tuple[str, RequestUsage]:
    """
    发送单次请求到 LLM 模型并获取响应

    如有更多参数可自行配置

    Returns:
        :return: 模型响应文本, 使用量信息
    """
    model_response = await model_request(
        model=model,
        messages=[ModelRequest.user_text_prompt(content)],
        model_settings=ModelSettings(temperature=cfg[group_id].llm.temperature)
    )

    if model_response.parts[0] is None:
        raise RuntimeError("模型返回为空")
    
    if not isinstance(model_response.parts[0].content, str): # type: ignore
        raise RuntimeError("模型返回格式错误")

    return model_response.parts[0].content, model_response.usage # type: ignore