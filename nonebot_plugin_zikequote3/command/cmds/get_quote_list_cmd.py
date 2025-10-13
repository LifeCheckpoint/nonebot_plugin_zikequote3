from ...imports import *
from ..command_definition import *
from ..parse_helper import *

class CmdParamsGetQuoteList(BaseModel):
    page_from: Optional[int] = Field(None, description="起始页码")
    page_to: Optional[int] = Field(None, description="结束页码")
    name: Optional[str] = Field(..., description="名称，可含空格")


parser = typer.Typer()
@cmd_name_alias(parser, cmdname_get_quote_list)
def quote_list_command(
    args: List[str] = typer.Argument(..., help="格式: [页码/范围] <名称>")
):
    """
    - /语录列表
    - /语录列表 <名称>
    - /语录列表 <页码> <名称>
    - /语录列表 <起始页码-结束页码> <名称>
    """

    # 去除命令头
    args = args[1:]

    # /语录列表
    if not args:
        return CmdParamsGetQuoteList(page_from=None, page_to=None, name=None)
    
    page_range_str = args[0]
    name_parts = args[1:]
    
    page_range_obj = None
    
    # 尝试将第一个参数解析为页码范围
    try:
        page_range_obj = PARAMTYPE_RANGE.convert(page_range_str, None, None)
    except click.BadParameter:
        # 如果解析失败，说明第一个参数是名称的一部分
        name_parts.insert(0, page_range_str)
        page_range_obj = None
    
    full_name = " ".join(name_parts)
    full_name = full_name if full_name != "" else None
    page_from = None
    page_to = None

    if isinstance(page_range_obj, tuple):
        page_from, page_to = page_range_obj
    elif isinstance(page_range_obj, int):
        page_from = page_range_obj
    
    return CmdParamsGetQuoteList(page_from=page_from, page_to=page_to, name=full_name)


@matcher_get_quote_list.handle()
async def f_get_quote_list(event: GroupME):
    """
    语录列表
    """
    from ...services.statistics_management.personal_listing_service import s_get_listing_html
    from ...services.user_management.user_parser_service import s_parse_at_and_str_user, s_at_one_user
    from ...services.user_management.user_service import s_user_exists
    from ...utils.click_cmd_parser import parse_command
    from datetime import datetime

    async with event_exception_failmsg_a(matcher_get_quote_list, "解析参数"):
        plain_command = event.get_plaintext().strip()
        params: CmdParamsGetQuoteList = parse_command(parser, plain_command)
        users: List[str] = []
        
        # HACK: 实现不太好，需要重新考虑
        logger.debug(f"命令原始文本: {plain_command}")
        logger.debug(f"命令解析参数结果: {params}")

        # 优先解析 At 段
        at_one_list = s_at_one_user(event)
        if at_one_list:
            users = s_parse_at_and_str_user(at_one_list, None, group_id=str(event.group_id), exact=True)
        else:
            # 如果不能被解析出名称，没有 At 段，则视为自己
            if not params.name:
                params.name = str(event.user_id)
                users = [str(event.user_id)]
            # 如果能被解析出名称但不存在 At 段
            if params.name and not s_at_one_user(event):
                users = s_parse_at_and_str_user(params.name, None, group_id=str(event.group_id), exact=True)
        
        logger.debug(f"解析结果用户列表: {users}")

    async with event_exception_failmsg_a(matcher_get_quote_list, "获取语录列表"):
        # 解析参数，获取目标用户 QQ 号
        if len(users) > 1:
            await matcher_get_quote_list.send("找到多个用户，仅使用第一个有效用户进行查询哦~")

        # 尝试使用第一个有效 QQ
        valid_first_user = None
        for u in users:
            if s_user_exists(u):
                valid_first_user = u
                break
        
        if not valid_first_user:
            raise ValueError("没有找到有效的用户哦.·´¯`(>▂<)´¯`·. ")
    
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_listing_html(str(event.group_id), valid_first_user, time, from_page=params.page_from, to_page=params.page_to)

        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=1520, height=200)
        await matcher_get_quote_list.finish(MsgSeg.image(img))
    