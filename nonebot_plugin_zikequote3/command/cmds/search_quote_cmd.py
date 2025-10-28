from ...imports import *
from ..command_definition import *
from ..parse_helper import *


class ArgsValidater(BaseModel):
    qq: Optional[int] = None
    search_with_image: bool = True
    max_result: Optional[int] = None
    use_regex: bool = False
    pattern: str = ""


@matcher_search_quote.handle()
async def f_search_quote(
    event: GroupME,
    qq: Match[int],
    max_result: Match[int],
    keyword: Match[UniMessage],
    no_image: Query[bool] = Query("no_image.value", False),
    use_regex: Query[bool] = Query("use_regex.value", False),
):
    """
    语录搜索
    """
    from ...services.statistics_management.quote_searching_service import s_get_searching_quote_html

    async with event_exception_failmsg_a(matcher_search_quote, "解析参数"):
        plain_command = event.get_plaintext().strip()
        logger.debug(f"命令原始文本: {plain_command}")

        if max_result.available:
            if max_result.result is not None and max_result.result < 1:
                await matcher_search_quote.finish("最大返回结果数量至少为 1 哦~")
        
        params = ArgsValidater(
            qq=qq.result if qq.available else None,
            search_with_image=(not no_image.result) if no_image.available else True,
            max_result=max_result.result if max_result.available else None,
            use_regex=use_regex.result if use_regex.available else False,
            pattern=keyword.result.extract_plain_text() if keyword.available else "",
        )
        logger.debug(f"解析结果参数: {params}")

    async with event_exception_failmsg_a(matcher_search_quote, "获取语录列表"):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_searching_quote_html(
            group_id=str(event.group_id),
            pattern=params.pattern,
            qq_id=str(params.qq) if params.qq else None,
            search_with_image=params.search_with_image,
            max_result=params.max_result,
            use_regex=params.use_regex,
            time=time
        )

        # 渲染图片
        img = await html_img_render(html, width=1520, height=200)
        await matcher_search_quote.finish(MsgSeg.image(img))
