"""LLM client 单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart
from pydantic_ai.usage import RequestUsage

from nonebot_plugin_zikequote3.llm_services import client


class TestSendLlmRequest:
    """测试 LLM 请求响应文本提取逻辑。"""

    @pytest.mark.asyncio
    async def test_ignores_thinking_part_and_returns_text_part(self, monkeypatch) -> None:
        """模型返回独立 thinking part 时，应返回 JSON 文本 part 而不是思考内容。"""
        expected_json = '{"num_quotes": 0, "quotes": []}'
        mock_model_request = AsyncMock(
            return_value=ModelResponse(
                parts=[
                    ThinkingPart(content="我们分析这段聊天记录，寻找符合金句特征的内容。"),
                    TextPart(content=expected_json),
                ],
                usage=RequestUsage(input_tokens=10, output_tokens=20),
            )
        )
        monkeypatch.setattr(client, "model_request", mock_model_request)

        response_text, usage = await client.send_llm_request(
            model=object(),
            content="请筛选金句",
            temperature=0.2,
        )

        assert response_text == expected_json
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20

    @pytest.mark.asyncio
    async def test_raises_when_no_text_part(self, monkeypatch) -> None:
        """仅返回 thinking part 时，应明确报错而不是把思考内容当作业务响应。"""
        mock_model_request = AsyncMock(
            return_value=ModelResponse(
                parts=[ThinkingPart(content="只有思考内容，没有最终 JSON。")],
                usage=RequestUsage(input_tokens=10, output_tokens=20),
            )
        )
        monkeypatch.setattr(client, "model_request", mock_model_request)

        with pytest.raises(RuntimeError, match="文本"):
            await client.send_llm_request(
                model=object(),
                content="请筛选金句",
                temperature=0.2,
            )
