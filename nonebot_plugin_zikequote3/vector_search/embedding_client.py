"""Embedding API 客户端，基于 AsyncOpenAI。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..config import EmbeddingConfig, LLMConfig
from ..paths import PluginPath

logger = logging.getLogger(__name__)

_RETRY_BASE_DELAY = 1.0  # 秒


class EmbeddingClient:
    """封装 OpenAI 兼容的 Embedding API 调用。"""

    def __init__(
        self,
        embedding_config: EmbeddingConfig,
        llm_config: LLMConfig,
        *,
        plugin_root: Path | None = None,
    ):
        self._config = embedding_config
        self._max_retries = embedding_config.max_retries
        resolved_root = plugin_root or PluginPath.plugin_root

        # base_url / api_key 为 None 时回退使用 LLM 配置
        base_url = embedding_config.base_url if embedding_config.base_url is not None else llm_config.base_url
        api_key_path_str = embedding_config.api_key_path if embedding_config.api_key_path is not None else llm_config.api_key_path
        api_key_path = Path(api_key_path_str)
        if not api_key_path.is_absolute():
            api_key_path = resolved_root / api_key_path
        # L2: 同步读取文件是有意为之——此构造函数仅在 dishka APP scope 启动时
        # 调用一次，且 dishka 的 provide 方法支持同步操作，无需异步化。
        api_key = api_key_path.read_text(encoding="utf-8").strip()

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=self._max_retries,
        )

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def dimensions(self) -> int:
        return self._config.dimensions

    @property
    def batch_size(self) -> int:
        return self._config.batch_size

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding 向量。含重试机制（指数退避，重试次数由配置决定）。"""
        if not texts:
            return []

        # L3: 仅在 dimensions 配置为有效正整数时才传递该参数，
        # 避免不支持 dimensions 参数的 API 报错。
        kwargs: Dict[str, Any] = {
            "model": self._config.model,
            "input": texts,
        }
        if self._config.dimensions:
            kwargs["dimensions"] = self._config.dimensions

        # L5: 简单重试机制，指数退避
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.embeddings.create(**kwargs)
                return [item.embedding for item in response.data]
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Embedding API 调用失败 (第 %d 次)，%.1f 秒后重试: %s",
                        attempt + 1, delay, exc,
                    )
                    await asyncio.sleep(delay)
        # 所有重试均失败，抛出最后一次异常
        raise last_exc  # type: ignore[misc]

    async def embed_query(self, text: str) -> List[float]:
        """单条文本生成 embedding 向量。"""
        vectors = await self.embed_texts([text])
        return vectors[0]
