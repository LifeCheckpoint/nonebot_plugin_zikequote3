from ...imports import *
from ..comand_definition import *
from ...msgtexts import general as mt


@matcher_rank.handle()
async def f_rank(event: GroupME, arg: Message = CommandArg()):
    """
    展示群内语录排行图片
    """
    from ...services.statistics_management.group_ranking_service import s_get_ranking_html
    from datetime import datetime

    # 解析参数，获取展示数量
    key = arg.extract_plain_text().strip()
    if key != "" and key.isnumeric() and int(key) > 0:
        max_showcase_number = min(int(key), max(1, cfg[event.group_id].showcase.max_rank_user_num))
    else:
        max_showcase_number = cfg[event.group_id].showcase.max_rank_user_num

    async with exception_finish_failure(matcher_quote_list, "获取语录排行"):
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_ranking_html(str(event.group_id), time, max_showcase_number)
        
        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=800, height=200)
        await matcher_rank.finish(MsgSeg.image(img))

@matcher_quote_list.handle()
async def f_quote_list(event: GroupME, arg: Message = CommandArg()):
    """
    语录列表
    """
    from ...services.user_management.user_service import s_user_exists
    from ...services.user_management.user_parser_service import s_parse_at_and_str_user
    from ...services.statistics_management.personal_listing_service import s_get_listing_html
    from datetime import datetime

    async with exception_finish_failure(matcher_quote_list, "获取语录列表"):
        # 解析参数，获取目标用户 QQ 号
        key = arg.extract_plain_text().strip()
        users = s_parse_at_and_str_user(key, event, exact=True)

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
        html = s_get_listing_html(str(event.group_id), valid_first_user, time)

        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=800, height=200)
        await matcher_quote_list.finish(MsgSeg.image(img))
    