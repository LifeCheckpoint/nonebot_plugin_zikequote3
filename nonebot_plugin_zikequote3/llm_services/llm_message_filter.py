"""
LLM 消息筛选器 —— MessageFilter 协议的具体实现。

使用 LLM 从消息队列中筛选出值得保存为语录的"金句"。
重构前由 ``llm_selection_service.py`` 承担，现作为独立类注入到
:class:`QuoteCollectionService` 中。
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field

from ..config import ConfigSchema, LLMConfig
from ..services.config_service import ConfigService
from ..services.quote_collection_service import SelectedQuote
from .client import create_model, send_llm_request
from .prompts.quote_pickup import quote_pickup

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  LLM 响应的 Pydantic 模型
# ------------------------------------------------------------------ #


class _QuoteItem(BaseModel):
    msg_id: str
    quote: str
    comment: str = ""


class _LlmPickupResponse(BaseModel):
    num_quotes: int = 0
    quotes: List[_QuoteItem] = Field(default_factory=list)


# ------------------------------------------------------------------ #
#  LlmMessageFilter
# ------------------------------------------------------------------ #


class LLMMessageFilter:
    """
    基于 LLM 的消息筛选器，实现 ``MessageFilter`` 协议。

    :param config_service: 配置服务，用于获取群组级别的 LLM / 收集配置
    :type config_service: ConfigService
    """

    def __init__(self, config_service: ConfigService) -> None:
        self._config_service = config_service

    async def filter_messages(
        self,
        messages: Sequence[tuple[str, str, str]],
        group_id: str,
    ) -> list[SelectedQuote]:
        """
        调用 LLM 从消息列表中筛选金句。

        :param messages: ``[(msg_id, display_name, content), ...]``
        :param group_id: 群号
        :returns: 筛选出的语录列表
        """
        if not messages:
            return []

        cfg = await self._config_service.get_parsed_config(group_id)
        llm_cfg: LLMConfig = cfg.llm
        at_least: int = cfg.collecting.at_least_selections
        at_most: int = cfg.collecting.at_most_selections

        # 构建提示词
        prompt = quote_pickup(
            list(messages),
            at_least_selections=at_least,
            at_most_selections=at_most,
        )

        # 调用 LLM
        try:
            model = create_model(llm_cfg)
            response_text, usage = await send_llm_request(
                model, prompt, temperature=llm_cfg.temperature,
            )
            logger.debug(
                "LLM 筛选响应 (group=%s): tokens=%s, text=%s",
                group_id, usage, response_text[:200],
            )
        except Exception:
            logger.warning(
                "LLM 筛选请求失败 (group=%s)，本轮不产出语录",
                group_id, exc_info=True,
            )
            return []

        # 解析响应
        try:
            from ..utils.json_parser import llm_json_parse_model
            parsed = llm_json_parse_model(_LlmPickupResponse, response_text)
        except Exception:
            logger.warning(
                "LLM 筛选响应解析失败 (group=%s): %s",
                group_id, response_text[:300], exc_info=True,
            )
            return []

        # 转换为 SelectedQuote
        result: list[SelectedQuote] = []
        msg_id_set = {m[0] for m in messages}
        for item in parsed.quotes:
            if item.msg_id not in msg_id_set:
                logger.debug(
                    "LLM 返回的 msg_id=%s 不在队列中，跳过", item.msg_id,
                )
                continue
            result.append(SelectedQuote(
                msg_id=item.msg_id,
                content=item.quote,
                comment=item.comment,
            ))

        logger.info(
            "LLM 筛选完成 (group=%s): %d/%d 条入选",
            group_id, len(result), len(messages),
        )
        return result
