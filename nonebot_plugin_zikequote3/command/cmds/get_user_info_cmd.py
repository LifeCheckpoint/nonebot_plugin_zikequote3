from ...imports import *
from ..command_definition import *

@matcher_get_user_info.handle()
async def f_get_user_info(
    event: GroupME,
    at_user: Match[At],
    qq: Match[str],
    nickname: Match[str]
):
    """
    获取用户信息卡片
    """
    from ...services.user_management.user_info_card_service import s_get_user_info_html
    from ...services.user_management.user_service import s_search_users_by_name
    from ...services.user_management.user_service import s_user_exists

    logger.debug("获取用户信息")

    async with event_exception_failmsg_a(matcher_get_user_info, "解析参数"):
        user_qq: str | None = None
        
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
                    await matcher_get_user_info.finish("找到多个用户，请考虑使用 @ 或 QQ 号进行查询哦~")
                elif len(probabily_users) < 1:
                    await matcher_get_user_info.finish("没有找到符合条件的用户哦~")
                else:
                    user_qq = probabily_users[0]
        
        # 最后使用发送者
        if not user_qq:
            user_qq = str(event.user_id)

    async with event_exception_failmsg_a(matcher_get_user_info, "获取用户信息"):
        # 尝试使用第一个有效 QQ
        if not user_qq or not s_user_exists(user_qq):
            raise ValueError("没有找到有效的用户哦.·´¯`(>▂<)´¯`·. ")
    
        html = await s_get_user_info_html(str(event.group_id), user_qq)
        img = await html_img_render(html, width=450, height=100) 
        await matcher_get_user_info.finish(MsgSeg.image(img))
