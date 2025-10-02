from ..imports import *
from .comand_definition import *
from ..utils.formating import format_pydantic_config_markdown
from ..interface.message_handle import (
    pick_received_msg,
    get_typed_message_list,
)
from ..interface.quote_handle import get_quote_rank


@matcher_listener.handle()
async def f_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理可能的语录收集
    """
    if not cfg.general.enable_zikequote3:
        return
    
    success = await pick_received_msg(event, bot)
    if success == False:
        print("自动语录收集失败，可能需要检查相关配置")


@matcher_rank.handle()
async def f_rank(event: GroupME, arg: Message = CommandArg()):
    """
    语录排行
    """
    key = arg.extract_plain_text().strip()
    num_topn = cfg.showcase.max_rank_user_num
    if key.isdigit() and 0 < int(key) <= cfg.showcase.max_rank_user_num:
        num_topn = int(key)
    
    msg_pending_num = len(get_typed_message_list(event.group_id))
    rank_info = get_quote_rank(event.group_id, top_n=num_topn)
    rank_info["stats"]["pending_quotes"] = msg_pending_num

    try:
        image_data = await full_render_html(cfg.path.templates / "rank.html", cfg.path.templates, data=rank_info, width=800, height=600)
    except Exception as e:
        print("生成语录排行失败：", e)
        await mfinish(matcher_rank, msg_rank_failed, error=str(e))

    await matcher_rank.finish(MsgSeg.image(image_data))


@matcher_setting_showing.handle()
async def f_setting_showing(event: GroupME):
    """
    显示语录设置，递归检查设置项并生成 Markdown 图片查看
    """
    # 检查权限
    if not is_quote_manager(event.sender.user_id):
        await mfinish(matcher_setting_showing, msg_no_permission, event="语录设置")
        return
    
    # 获取设置项
    config_md = format_pydantic_config_markdown(cfg)

    # 生成 Markdown 图片
    try:
        image_data = await full_render_markdown(config_md)
    except Exception as e:
        print("生成语录配置失败：", e)
        await mfinish(matcher_setting_showing, msg_quote_setting_showing_failed, error=str(e))

    await matcher_setting_showing.finish(MsgSeg.image(image_data))
    