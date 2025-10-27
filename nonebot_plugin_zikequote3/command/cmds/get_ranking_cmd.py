from ...imports import *
from ..command_definition import *


@matcher_get_ranking.handle()
async def f_get_ranking(event: GroupME, arg: Message = CommandArg()):
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

    async with event_exception_failmsg_a(matcher_get_ranking, "获取语录排行"):
        # 获取详细信息 HTML
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = s_get_ranking_html(str(event.group_id), time, max_showcase_number)

        # HACK
        # 渲染图片
        img = await html_img_render_plugin(html, module_render_image_root, width=1920, height=1080, timeout=10000)
        await matcher_get_ranking.finish(MsgSeg.image(img))