from ...imports import *
from ..comand_definition import *
from ...interface.message_handle import pick_received_msg


@matcher_listener.handle()
async def f_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理可能的语录收集
    """
    if not default_cfg.general.enable_zikequote3:
        return
    
    success = await pick_received_msg(event, bot)
    if success == False:
        print("自动语录收集失败，可能需要检查相关配置")