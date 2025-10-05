from ...imports import *
from ..comand_definition import *

@matcher_collecting_listener.handle()
async def f_collecting_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理自动语录收集
    """
    from ...services.collecting.collecting_queue import s_queue_put, s_queue_clear
    from ...services.collecting.llm_selection import s_llm_selection
    from ...services.collecting.save_selection_result import s_save_selection_result
    from ...services.status.personal_info_update import s_update_personal_info_api

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
        return # TODO

    # 以一定概率更新个人信息
    if random.random() < cfg[event.group_id].collecting.update_personal_info_probability:
        try:
            await s_update_personal_info_api(str(event.group_id), str(event.user_id), bot)
        except Exception as e:
            return

    # 未达到阈值，结束流程，否则尝试触发收录
    if not is_thresold:
        return
    
    # LLM 筛选
    try:
        response, usage = await s_llm_selection(str(event.group_id))
        logger.info(f"筛选到 {response.num_quotes} 条语录，输入 {usage.input_tokens} tokens，输出 {usage.output_tokens} tokens，总计 {usage.total_tokens} tokens")
    except Exception as e:
        return
    
    # 最终语录入库，清空队列
    try:
        s_save_selection_result(str(event.group_id), response)
        s_queue_clear(str(event.group_id))
    except Exception as e:
        return
    