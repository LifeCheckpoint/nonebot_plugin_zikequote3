"""Embedding API 客户端，基于 AsyncOpenAI。"""

from __future__ import annotations

from pathlib import Path
from typing import List

from openai import AsyncOpenAI

from ..config import EmbeddingConfig, LLMConfig
from ..paths import PluginPath


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
        resolved_root = plugin_root or PluginPath.plugin_root

        # base_url / api_key 为空时复用 LLM 配置
        base_url = embedding_config.base_url or llm_config.base_url
        api_key_path_str = embedding_config.api_key_path or llm_config.api_key_path
        api_key_path = Path(api_key_path_str)
        if not api_key_path.is_absolute():
            api_key_path = resolved_root / api_key_path
        api_key = api_key_path.read_text(encoding="utf-8").strip()

        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

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
        """批量生成 embedding 向量。"""
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._config.model,
            input=texts,
            dimensions=self._config.dimensions,
        )
        return [item.embedding for item in response.data]

    async def embed_query(self, text: str) -> List[float]:
        """单条文本生成 embedding 向量。"""
        vectors = await self.embed_texts([text])
        return vectors[0]
