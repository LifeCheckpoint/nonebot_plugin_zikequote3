from ...imports import *
from ..command_definition import *


def parse_page_range(s: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    解析 page_from, page_to
    """
    if s is None:
        return (None, None)
    
    s = s.strip()
    if not s:
        return (None, None)
    if "-" in s:
        parts = s.split("-", 1)
        try:
            page_from = int(parts[0])
        except ValueError:
            page_from = None
        try:
            page_to = int(parts[1])
        except ValueError:
            page_to = None
        return (page_from, page_to)
    else:
        try:
            val = int(s)
        except ValueError:
            return (None, None)
        return (val, None)


@matcher_get_quote_list.handle()
async def f_get_quote_list(
    event: GroupME,
    range: Match[str],
    at_user: Match[At],
    qq: Match[str],
    nickname: Match[str]
):
    """
    语录列表
    """
    from ...services.statistics_management.personal_listing_service import s_get_listing_html
    from ...services.user_management.user_service import s_search_users_by_name
    from ...services.user_management.user_service import s_user_exists
    from datetime import datetime

    async with event_exception_failmsg_a(matcher_get_quote_list, "解析参数"):
        plain_command = event.get_plaintext().strip()
        logger.debug(f"命令原始文本: {plain_command}")
        user_qq: str | None = None
        
        with service_exception("解析命令参数"):
            # 优先解析 At 段
            if at_user.available:
                if at_user.result and at_user.result.origin:
                    user_qq = at_user.result.origin.data.get("qq")

            # 其次解析 QQ 号
            if not user_qq and qq.available:
                if qq.result and qq.result.isdigit():
                    user_qq = qq.result
            # 其次解析手动输入昵称
            if not user_qq and nickname.available:
                if nickname.result:
                    probabily_users = s_search_users_by_name(nickname.result, str(event.group_id), exact=False)
                    if len(probabily_users) > 1:
                        await matcher_get_quote_list.finish("找到多个用户，请考虑使用 @ 或 QQ 号进行查询哦~")
                    elif len(probabily_users) < 1:
                        await matcher_get_quote_list.finish("没有找到符合条件的用户哦~")
                    else:
                        user_qq = probabily_users[0]
            
            # 最后使用发送者
            if not user_qq:
                user_qq = str(event.user_id)

            logger.debug(f"解析结果用户: {user_qq}")

            # 解析范围参数
            page_from, page_to = parse_page_range(range.result if range.available else "")

    async with event_exception_failmsg_a(matcher_get_quote_list, "获取语录列表"):
        # 尝试使用第一个有效 QQ
        if not user_qq or not s_user_exists(user_qq):
            raise ValueError("没有找到有效的用户哦.·´¯`(>▂<)´¯`·. ")
    
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_listing_html(str(event.group_id), user_qq, time, from_page=page_from, to_page=page_to)

        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=1520, height=200)
        await matcher_get_quote_list.finish(MsgSeg.image(img))
    