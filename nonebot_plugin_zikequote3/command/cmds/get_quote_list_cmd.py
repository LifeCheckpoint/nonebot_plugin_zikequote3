from ...imports import *
from ..command_definition import *


@matcher_quote_list.handle()
async def f_quote_list(event: GroupME):
    """
    语录列表
    """
    from ...services.statistics_management.personal_listing_service import s_get_listing_html
    from ...services.user_management.user_parser_service import s_parse_at_and_str_user, s_at_one_user
    from ...services.user_management.user_service import s_user_exists
    from ...utils.click_cmd_parser import parse_command
    from ..parser.quote_statistics_parser import quote_statistics_parser as qsp, QuoteListCommandParams
    from datetime import datetime

    async with event_exception_failmsg_a(matcher_quote_list, "解析参数"):
        plain_command = event.get_plaintext().strip()
        params: QuoteListCommandParams = parse_command(qsp, plain_command)
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

    async with event_exception_failmsg_a(matcher_quote_list, "获取语录列表"):
        # 解析参数，获取目标用户 QQ 号
        if len(users) > 1:
            await matcher_quote_list.send("找到多个用户，仅使用第一个有效用户进行查询哦~")

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
        await matcher_quote_list.finish(MsgSeg.image(img))
    