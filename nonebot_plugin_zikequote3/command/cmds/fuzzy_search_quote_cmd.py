"""模糊语义搜索命令处理器（/模糊查语录）。

通过 ``@inject`` 装饰器自动从 dishka 容器获取服务依赖。
支持简写位置参数和显式 ``-s`` / ``-n`` 选项。
"""

from __future__ import annotations

from nonebot import logger
from typing import Optional

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_alconna import Match, Query
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_alconna.uniseg.segment import At

from ..command_definition import matcher_fuzzy_search_quote
from ..parse_helper.query_resolver import extract_at_qq
from ...di import Inject, inject
from ...services import ConfigService, QuoteReadService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ...vector_search.search_service import VectorSearchService
from ._error_handlers import command_error_handler
from .search_quote_cmd import _ArgsValidater, _do_fuzzy_search

def _parse_fuzzy_shorthand(
    tokens: list[str],
) -> tuple[Optional[int], Optional[float], str]:
    """解析模糊搜索命令的简写位置参数。

    首个 token 若为整数则解析为 top_n，若为小数则解析为 similarity，
    其余 token 拼接为 keyword。

    :param tokens: 命令参数 token 列表。
    :type tokens: list[str]
    :returns: ``(top_n, similarity, keyword)`` 三元组。
    :rtype: tuple[Optional[int], Optional[float], str]
    """
    if not tokens:
        return None, None, ""

    first = tokens[0]
    top_n: Optional[int] = None
    similarity: Optional[float] = None
    rest_start = 0

    try:
        val = float(first)
        if "." in first:
            similarity = val
        else:
            top_n = int(val)
        rest_start = 1
    except ValueError:
        pass

    keyword = " ".join(tokens[rest_start:])
    return top_n, similarity, keyword

@matcher_fuzzy_search_quote.handle()
@inject
async def handle_fuzzy_search_quote(
    event: GroupMessageEvent,
    at_user: Match[At],
    qq: Match[int],
    keyword: Match[UniMessage],
    similarity: Match[float],
    top_n: Match[int],
    no_image: Query[bool] = Query("no_image.value", False),
    vector_search_svc: VectorSearchService = Inject(VectorSearchService),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    user_svc: UserService = Inject(UserService),
    image_store: ImageStore = Inject(ImageStore),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
    config_svc: ConfigService = Inject(ConfigService),
) -> None:
    """处理专用模糊搜索命令（/模糊查语录）。

    支持简写位置参数：首个 token 若为整数 → top_n，若为小数 → similarity。

    :param event: 群消息事件。
    :type event: GroupMessageEvent
    :param at_user: @提及 的用户。
    :type at_user: Match[At]
    :param qq: QQ 号参数。
    :type qq: Match[int]
    :param keyword: 搜索关键词。
    :type keyword: Match[UniMessage]
    :param similarity: 相似度阈值选项。
    :type similarity: Match[float]
    :param top_n: 返回结果数量选项。
    :type top_n: Match[int]
    :param no_image: 是否排除图片语录。
    :type no_image: Query[bool]
    :param vector_search_svc: 向量搜索服务（DI 注入）。
    :type vector_search_svc: VectorSearchService
    :param quote_read_svc: 语录读取服务（DI 注入）。
    :type quote_read_svc: QuoteReadService
    :param user_svc: 用户服务（DI 注入）。
    :type user_svc: UserService
    :param image_store: 图片存储（DI 注入）。
    :type image_store: ImageStore
    :param html_render_svc: HTML 渲染服务（DI 注入）。
    :type html_render_svc: HtmlRenderServiceBase
    :param config_svc: 配置服务（DI 注入）。
    :type config_svc: ConfigService

    .. note::
        示例：``/模糊查语录 15 xxxx`` → top_n=15, keyword="xxxx"；
        ``/模糊查语录 0.7 xxxx`` → similarity=0.7, keyword="xxxx"。
    """
    group_id = str(event.group_id)

    async with command_error_handler(matcher_fuzzy_search_quote, "解析参数"):
        at_qq = extract_at_qq(at_user)
        resolved_qq: int | None = None
        if at_qq is not None:
            resolved_qq = int(at_qq)
        elif qq.available and qq.result is not None:
            resolved_qq = qq.result

        raw_text = (
            keyword.result.extract_plain_text()
            if keyword.available else ""
        )
        tokens = raw_text.split() if raw_text else []

        parsed_top_n, parsed_similarity, parsed_keyword = _parse_fuzzy_shorthand(tokens)

        # 显式 -s / -n 选项优先于简写
        final_similarity = (
            similarity.result
            if similarity.available and similarity.result is not None
            else parsed_similarity
        )
        final_top_n = (
            top_n.result
            if top_n.available and top_n.result is not None
            else parsed_top_n
        )

        params = _ArgsValidater(
            qq=resolved_qq,
            search_with_image=(
                (not no_image.result) if no_image.available else True
            ),
            use_fuzzy=True,
            similarity=final_similarity,
            top_n=final_top_n,
            pattern=parsed_keyword,
        )
        logger.debug("模糊搜索解析结果: {}", params)

        # --- M3: 边界校验 top_n 和 similarity ---
        if params.top_n is not None and params.top_n < 1:
            await matcher_fuzzy_search_quote.finish("返回结果数量（-n）至少为 1 哦~")
        if params.similarity is not None and not (0.0 <= params.similarity <= 1.0):
            await matcher_fuzzy_search_quote.finish("相似度阈值（-s）必须在 0.0 到 1.0 之间哦~")

    # 两层检查：先检查群组配置，再检查基础设施
    cfg = await config_svc.get_parsed_config(group_id)
    if not cfg.embedding.enabled:
        await matcher_fuzzy_search_quote.finish(
            "当前群组未启用向量搜索，请先执行 /修改语录配置 embedding.enabled True"
        )

    if vector_search_svc is None:
        await matcher_fuzzy_search_quote.finish(
            "向量搜索基础设施未就绪，请检查 Embedding 配置（model、base_url、api_key_path）"
        )

    await _do_fuzzy_search(
        matcher_fuzzy_search_quote, group_id, params,
        vector_search_svc=vector_search_svc,
        quote_read_svc=quote_read_svc,
        user_svc=user_svc,
        image_store=image_store,
        html_render_svc=html_render_svc,
        config_svc=config_svc,
    )
