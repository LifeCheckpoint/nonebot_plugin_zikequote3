"""Embedding API 客户端，基于 AsyncOpenAI。

提供对 OpenAI 兼容 Embedding API 的异步调用封装，
支持批量文本向量化和指数退避重试机制。
"""

from __future__ import annotations

import asyncio
from nonebot import logger
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..config import EmbeddingConfig, LLMConfig
from ..paths import PluginPath

_RETRY_BASE_DELAY = 1.0  # 秒

class EmbeddingClient:
    """封装 OpenAI 兼容的 Embedding API 调用。

    负责管理 API 连接配置、模型参数，并提供带重试机制的
    文本向量化接口。

    :param embedding_config: Embedding 服务配置。
    :type embedding_config: EmbeddingConfig
    :param llm_config: LLM 服务配置，用于回退 base_url 和 api_key。
    :type llm_config: LLMConfig
    :param plugin_root: 插件根目录路径，默认使用 :attr:`PluginPath.plugin_root`。
    :type plugin_root: Path | None
    """

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

        # base_url / api_key 为空字符串时回退使用 LLM 配置
        base_url = embedding_config.base_url or llm_config.base_url
        api_key_path_str = embedding_config.api_key_path or llm_config.api_key_path
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
        """获取当前配置的 Embedding 模型名称。

        :returns: 模型名称字符串。
        :rtype: str
        """
        return self._config.model

    @property
    def dimensions(self) -> int:
        """获取模型输出向量的维度。

        :returns: 向量维度。
        :rtype: int
        """
        return self._config.dimensions

    @property
    def batch_size(self) -> int:
        """获取批量向量化时每批的文本数量。

        :returns: 批大小。
        :rtype: int
        """
        return self._config.batch_size

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding 向量。

        使用指数退避重试机制，重试次数由配置决定。

        :param texts: 待向量化的文本列表。
        :type texts: List[str]
        :returns: 与输入文本一一对应的向量列表。
        :rtype: List[List[float]]
        :raises Exception: 所有重试均失败时抛出最后一次异常。
        """
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
                        "Embedding API 调用失败 (第 {} 次)，{:.1f} 秒后重试: {}",
                        attempt + 1, delay, exc,
                    )
                    await asyncio.sleep(delay)
        # 所有重试均失败，抛出最后一次异常
        raise last_exc  # type: ignore[misc]

    async def embed_query(self, text: str) -> List[float]:
        """单条文本生成 embedding 向量。

        :param text: 待向量化的文本。
        :type text: str
        :returns: 文本对应的向量。
        :rtype: List[float]
        """
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def close(self) -> None:
        await self._client.close()
