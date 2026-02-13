"""
语录搜索命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
使用 :class:`QueryResolver` 统一解析 @提及 和 ``-qq`` 选项的用户筛选参数。
支持普通搜索、正则搜索和模糊语义搜索三种模式。
"""

from __future__ import annotations

from nonebot import logger
from datetime import datetime
from typing import Any, Optional

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match, Query
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_alconna.uniseg.segment import At
from pydantic import BaseModel

from ..command_definition import matcher_search_quote
from ..parse_helper.query_resolver import extract_at_qq
from ...di import Inject, inject
from ...services import ConfigService, StatisticsService, QuoteReadService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ...vector_search.search_service import VectorSearchService
from ._error_handlers import command_error_handler
from ...templates.registry import LISTING
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes

class _ArgsValidater(BaseModel):
    """
    搜索命令参数校验模型。

    :param qq: 用于筛选的 QQ 号，默认为 ``None``
    :type qq: Optional[int]
    :param search_with_image: 是否包含含图片的语录，默认为 ``True``
    :type search_with_image: bool
    :param max_result: 最大返回结果数量，默认为 ``None``（不限制）
    :type max_result: Optional[int]
    :param use_regex: 是否使用正则表达式搜索，默认为 ``False``
    :type use_regex: bool
    :param use_fuzzy: 是否启用模糊语义搜索，默认为 ``False``
    :type use_fuzzy: bool
    :param similarity: 模糊搜索相似度阈值(0-1)，默认为 ``None``
    :type similarity: Optional[float]
    :param top_n: 模糊搜索返回前N个结果，默认为 ``None``
    :type top_n: Optional[int]
    :param pattern: 搜索关键词或正则模式，默认为空字符串
    :type pattern: str
    """

    qq: Optional[int] = None
    search_with_image: bool = True
    max_result: Optional[int] = None
    use_regex: bool = False
    use_fuzzy: bool = False
    similarity: Optional[float] = None
    top_n: Optional[int] = None
    pattern: str = ""

@matcher_search_quote.handle()
@inject
async def handle_search_quote(
    event: GroupMessageEvent,
    at_user: Match[At],
    qq: Match[int],
    max_result: Match[int],
    keyword: Match[UniMessage],
    similarity: Match[float],
    top_n: Match[int],
    no_image: Query[bool] = Query("no_image.value", False),
    use_regex: Query[bool] = Query("use_regex.value", False),
    use_fuzzy: Query[bool] = Query("use_fuzzy.value", False),
    stats_svc: StatisticsService = Inject(StatisticsService),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    user_svc: UserService = Inject(UserService),
    image_store: ImageStore = Inject(ImageStore),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
    config_svc: ConfigService = Inject(ConfigService),
    vector_search_svc: VectorSearchService = Inject(VectorSearchService),
) -> None:
    """
    处理语录搜索命令。

    支持关键词搜索、正则搜索、模糊语义搜索，按 @提及 或 QQ 号筛选作者、排除图片等，
    使用 :func:`extract_at_qq` 从 @提及 中提取 QQ 号，与 ``-qq`` 选项统一处理，
    渲染为列表图片发送。当 ``-f/--fuzzy`` 启用时走向量语义搜索分支。
    """
    group_id = str(event.group_id)

    async with command_error_handler(matcher_search_quote, "解析参数"):
        if max_result.available:
            if max_result.result is not None and max_result.result < 1:
                await matcher_search_quote.finish(
                    "最大返回结果数量至少为 1 哦~"
                )

        # 统一 @提及 和 -qq 选项：@提及 优先于 -qq
        at_qq = extract_at_qq(at_user)
        resolved_qq: int | None = None
        if at_qq is not None:
            resolved_qq = int(at_qq)
        elif qq.available and qq.result is not None:
            resolved_qq = qq.result

        params = _ArgsValidater(
            qq=resolved_qq,
            search_with_image=(
                (not no_image.result) if no_image.available else True
            ),
            max_result=(
                max_result.result if max_result.available else None
            ),
            use_regex=(
                use_regex.result if use_regex.available else False
            ),
            use_fuzzy=(
                use_fuzzy.result if use_fuzzy.available else False
            ),
            similarity=(
                similarity.result if similarity.available else None
            ),
            top_n=(
                top_n.result if top_n.available else None
            ),
            pattern=(
                keyword.result.extract_plain_text()
                if keyword.available else ""
            ),
        )
        logger.debug("解析结果参数: {}", params)

    # 模糊语义搜索分支
    if params.use_fuzzy:
        await _do_fuzzy_search(
            matcher_search_quote, group_id, params,
            vector_search_svc=vector_search_svc,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            html_render_svc=html_render_svc,
            config_svc=config_svc,
        )
        return

    # 普通/正则搜索分支
    await _do_normal_search(
        matcher_search_quote, group_id, params,
        stats_svc=stats_svc,
        quote_read_svc=quote_read_svc,
        user_svc=user_svc,
        image_store=image_store,
        html_render_svc=html_render_svc,
        config_svc=config_svc,
    )

async def _do_normal_search(
    matcher: Any,
    group_id: str,
    params: _ArgsValidater,
    *,
    stats_svc: StatisticsService,
    quote_read_svc: QuoteReadService,
    user_svc: UserService,
    image_store: ImageStore,
    html_render_svc: HtmlRenderServiceBase,
    config_svc: ConfigService,
) -> None:
    """普通/正则搜索逻辑（从 handle_search_quote 提取）。"""
    async with command_error_handler(matcher, "获取语录列表"):
        quotes, total_found = await stats_svc.search_quotes(
            keyword=params.pattern,
            group_id=group_id,
            author_id=(str(params.qq) if params.qq else None),
            include_image_only=params.search_with_image,
            max_results=params.max_result,
            use_regex=params.use_regex,
        )

        cfg = await config_svc.get_parsed_config(group_id)
        max_content_length = cfg.showcase.quote_content_max_length

        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            show_author=True,
            max_content_length=max_content_length,
        )

        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_text = f"有关{params.pattern}的语录搜索结果"
        search_mode = "正则" if params.use_regex else "普通"
        desc_text = " | ".join([
            f"{time_str}",
            f"{search_mode}搜索模式",
            (f"筛选 QQ: {params.qq}" if params.qq else "不筛选 QQ"),
            f"{'' if params.search_with_image else '不'} 包含图片",
            f"共 {total_found} 条 (显示 {len(quote_boxes)} 条)",
        ])

        hitokoto_text = _try_get_hitokoto()

        html = render_list(TemplateQuoteListData(
            title=title_text,
            desc=desc_text,
            addition=hitokoto_text,
            quotes=quote_boxes,
        ))
        img = await html_render_svc.render(html, width=LISTING.width, height=LISTING.height)
        await matcher.finish(MsgSeg.image(img))

def _try_get_hitokoto() -> Optional[str]:
    """尝试获取一言，失败时返回 None。"""
    try:
        from ...utils.hitokoto import get_hitokoto
        content, author = get_hitokoto()
        if content and author:
            return f"「{content}」 ——{author}"
        if content:
            return f"「{content}」"
    except Exception:
        logger.debug("获取一言失败", exc_info=True)
    return None

async def _do_fuzzy_search(
    matcher: Any,
    group_id: str,
    params: _ArgsValidater,
    *,
    vector_search_svc: Optional[VectorSearchService],
    quote_read_svc: QuoteReadService,
    user_svc: UserService,
    image_store: ImageStore,
    html_render_svc: HtmlRenderServiceBase,
    config_svc: ConfigService,
) -> None:
    """模糊语义搜索逻辑，从 :func:`handle_search_quote` 提取的公共实现。

    执行向量语义搜索并渲染结果为列表图片发送。支持按 QQ 号和图片过滤结果。

    :param matcher: 命令匹配器实例。
    :type matcher: Any
    :param group_id: 群组 ID。
    :type group_id: str
    :param params: 搜索参数校验模型。
    :type params: _ArgsValidater
    :param vector_search_svc: 向量搜索服务，未启用时为 ``None``。
    :type vector_search_svc: Optional[VectorSearchService]
    :param quote_read_svc: 语录读取服务。
    :type quote_read_svc: QuoteReadService
    :param user_svc: 用户服务。
    :type user_svc: UserService
    :param image_store: 图片存储。
    :type image_store: ImageStore
    :param html_render_svc: HTML 渲染服务。
    :type html_render_svc: HtmlRenderServiceBase
    :param config_svc: 配置服务。
    :type config_svc: ConfigService
    """
    async with command_error_handler(matcher, "模糊语义搜索"):
        if not params.pattern:
            await matcher.finish("模糊搜索需要提供关键词哦~")

        # 两层检查：先检查群组配置，再检查基础设施
        cfg = await config_svc.get_parsed_config(group_id)
        if not cfg.embedding.enabled:
            await matcher.finish(
                "当前群组未启用向量搜索，请先执行 /修改语录配置 embedding.enabled True"
            )
            return

        if vector_search_svc is None:
            await matcher.finish(
                "向量搜索基础设施未就绪，请检查 Embedding 配置（model、base_url、api_key_path）"
            )
            return

        # M4: 分别检查基础设施可用性和索引是否为空
        available = await vector_search_svc.is_available()
        if not available:
            await matcher.finish(
                "模糊搜索服务当前不可用，请确认已启用 embedding 配置。"
            )

        index_count = await vector_search_svc.get_index_count()
        if index_count == 0:
            await matcher.finish(
                "向量索引为空，请先使用 /重建语录索引 构建索引。"
            )

        # --- M3: 边界校验 top_n 和 similarity ---
        if params.top_n is not None and params.top_n < 1:
            await matcher.finish("返回结果数量（-n）至少为 1 哦~")
        if params.similarity is not None and not (0.0 <= params.similarity <= 1.0):
            await matcher.finish("相似度阈值（-s）必须在 0.0 到 1.0 之间哦~")

        threshold = params.similarity if params.similarity is not None else 0.0
        limit = params.top_n if params.top_n is not None else 10

        results = await vector_search_svc.semantic_search(
            params.pattern, group_id,
            limit=limit, threshold=threshold,
        )

        # --- M2: 按 QQ 号和图片过滤结果 ---
        if params.qq:
            author_id = str(params.qq)
            results = [(q, s) for q, s in results if q.author_id == author_id]
        if not params.search_with_image:
            results = [(q, s) for q, s in results if q.image_content_uuid is None]

        quotes = [q for q, _ in results]
        scores = [s for _, s in results]

        cfg = await config_svc.get_parsed_config(group_id)
        max_content_length = cfg.showcase.quote_content_max_length

        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            show_author=True,
            show_image=params.search_with_image,
            max_content_length=max_content_length,
        )

        # 在每条语录的文本前附加相似度分数
        for box, score in zip(quote_boxes, scores):
            if box.quote_text:
                box.quote_text = f"[{score:.2f}] {box.quote_text}"

        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_text = f"有关「{params.pattern}」的模糊搜索结果"
        desc_parts = [
            f"{time_str}",
            "模糊语义搜索",
            (f"筛选 QQ: {params.qq}" if params.qq else "不筛选 QQ"),
            f"{'' if params.search_with_image else '不'} 包含图片",
        ]
        if params.similarity is not None:
            desc_parts.append(f"阈值: {params.similarity}")
        desc_parts.append(f"共 {len(quote_boxes)} 条")
        desc_text = " | ".join(desc_parts)

        hitokoto_text = _try_get_hitokoto()

        html = render_list(TemplateQuoteListData(
            title=title_text,
            desc=desc_text,
            addition=hitokoto_text,
            quotes=quote_boxes,
        ))
        img = await html_render_svc.render(html, width=LISTING.width, height=LISTING.height)
        await matcher.finish(MsgSeg.image(img))

