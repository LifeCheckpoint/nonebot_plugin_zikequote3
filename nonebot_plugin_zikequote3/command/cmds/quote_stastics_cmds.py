from ...imports import *
from ..comand_definition import *


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
    