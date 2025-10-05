from ...imports import *
from ..comand_definition import *
from ...msgtexts import general as mt


@matcher_rank.handle()
async def f_rank(event: GroupME, arg: Message = CommandArg()):
    """
    展示群内语录排行图片
    """
    from ...services.stastics.ranking import s_get_ranking_html
    from datetime import datetime

    # 解析参数，获取展示数量
    key = arg.extract_plain_text().strip()
    if key != "" and key.isnumeric() and int(key) > 0:
        max_showcase_number = min(int(key), max(1, cfg[event.group_id].showcase.max_rank_user_num))
    else:
        max_showcase_number = cfg[event.group_id].showcase.max_rank_user_num

    try:
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_ranking_html(str(event.group_id), time, max_showcase_number)
        
        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=800, height=200)
        await matcher_rank.finish(MsgSeg.image(img))
    except Exception as e:
        await matcher_rank.finish(mt.failure("获取语录排行", detial=str(e)))

@matcher_quote_list.handle()
async def f_quote_list(event: GroupME, arg: Message = CommandArg()):
    """
    语录列表
    """
    from ...services.users.get_user import s_user_exists, s_search_users_by_name
    from ...services.stastics.listing import s_get_listing_html
    from datetime import datetime

    # 解析参数，获取目标用户 QQ 号
    key = arg.extract_plain_text().strip()
    at_segs: List[MsgSeg] = event.get_message()["at"]
    at_one: str | int | None = at_segs[0].data.get("qq") if at_segs else None

    if not at_one or at_one == "all":
        # 非@用户，使用参数
        if key == "" or key.isnumeric():
            # 输入 QQ 号或空
            qq_id = str(event.user_id) if key == "" else key
        else:
            # 输入昵称，尝试搜索
            users = s_search_users_by_name(key, str(event.group_id), exact=True)
            if not users:
                await matcher_quote_list.finish(mt.failure("获取语录列表", entity_name=key, detial="找不到匹配的用户~昵称有没有输入完整呢？"))
                return
            if len(users) > 1:
                pass # TODO
                return
            qq_id = users[0]
    else:
        # @用户，使用第一个@
        qq_id = str(at_one)
    
    if not s_user_exists(qq_id):
        await matcher_quote_list.finish(mt.failure("获取语录列表", qq_id, detial="用户不存在呢"))
        return
    
    try:
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_listing_html(str(event.group_id), qq_id, time)

        # 渲染图片
        img = await html_img_render(html, module_render_image_root, width=800, height=200)
        await matcher_quote_list.finish(MsgSeg.image(img))
    except Exception as e:
        await matcher_quote_list.finish(mt.failure("获取语录列表", entity_name=qq_id, detial=str(e)))
    