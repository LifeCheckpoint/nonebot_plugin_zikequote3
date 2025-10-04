from ...imports import *
from ..comand_definition import *

@matcher_collecting_listener.handle()
async def f_collecting_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理自动语录收集
    """
    from ...services.collecting.collecting_listener import s_queue_put
    from ...services.status.personal_info_update import s_update_personal_info_api
    import random as ran

    # 验证收录条件
    msg = event.get_plaintext().strip()
    if not msg or msg == "" or len(msg) > cfg[event.group_id].collecting.msg_max_length:
        return
    
    # 加入队列并获取是否达到阈值
    try:
        is_thresold = s_queue_put(
            group_id=str(event.group_id),
            msg_id=str(event.message_id),
            qq_id=str(event.user_id),
            content=msg,
        )
    except Exception as e:
        pass

    # 以一定概率更新个人信息
    if ran.random() < 0.1:
        try:
            await s_update_personal_info_api(str(event.group_id), str(event.user_id), bot)
        except Exception as e:
            pass

    # 达到阈值，尝试触发收录
    # TODO