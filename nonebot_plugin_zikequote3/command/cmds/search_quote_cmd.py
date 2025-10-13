from ...imports import *
from ..command_definition import *
from ..parse_helper import *


class CmdParamsSearchQuote(BaseModel):
    qq: Optional[int] = Field(None, description="用于筛选的QQ号")
    search_with_image: bool = Field(True, description="是否搜索包含图片的语录")
    max_result: Optional[int] = Field(None, ge=1, description="最大返回结果数量，至少为1")
    use_regex: bool = Field(False, description="是否启用正则表达式匹配")
    keyword: str = Field(..., description="搜索的关键词或模式")


parser = typer.Typer()
@cmd_name_alias(parser, cmdname_search_quote)
@click.option('-qq', type=int, default=None, help='筛选特定QQ号的语录')
@click.option('--no-image', '-ni', is_flag=True, flag_value=False, default=True, help='禁用图片语录搜索 (缩写: -ni)')
@click.option('--max-result', '-m', type=click.IntRange(min=1), default=None, show_default=True, help='最大结果数量 (缩写: -m)')
@click.option('-r', '--regex', is_flag=True, default=False, help='启用正则表达式')
@click.argument('keyword_parts', nargs=-1, required=True)
def quote_search_command(qq, search_with_image, max_result, use_regex, keyword_parts):
    """
    - /查语录 xxx
    - /查语录 -qq 123456 xxx
    - /查语录 --no-image xxx
    - /查语录 -m 5 xxx
    - /查语录 -r xxx
    - /查语录 -qq 123456 --no-image -m 5 -r xxx
    """
    if not keyword_parts:
        raise ValueError("缺少关键词或搜索模式~")
    
    keyword = " ".join(keyword_parts)
    
    with service_exception("解析语录搜索命令验证"):
        return CmdParamsSearchQuote(
            qq=qq,
            search_with_image=search_with_image,
            max_result=max_result,
            use_regex=use_regex,
            keyword=keyword
        )


@matcher_search_quote.handle()
async def f_search_quote(event: GroupME):
    """
    语录搜索
    """
    from ...services.statistics_management.quote_searching_service import s_get_searching_quote_html

    async with event_exception_failmsg_a(matcher_search_quote, "解析参数"):
        plain_command = event.get_plaintext().strip()
        params: CmdParamsSearchQuote = parse_command(parser, plain_command)

        logger.debug(f"命令原始文本: {plain_command}")
        logger.debug(f"命令解析参数结果: {params}")

    async with event_exception_failmsg_a(matcher_search_quote, "获取语录列表"):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_searching_quote_html(
            group_id=str(event.group_id),
            pattern=params.keyword,
            qq_id=str(params.qq),
            search_with_image=params.search_with_image,
            max_result=params.max_result,
            use_regex=params.use_regex,
            time=time,
        )

        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=1520, height=200)
        await matcher_search_quote.finish(MsgSeg.image(img))
