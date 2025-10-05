from ...imports import *
from ..comand_definition import *

@matcher_collecting_listener.handle()
async def f_collecting_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理自动语录收集

    此事件不会向用户界面提供任何反馈
    """
    from ...services.collecting.collecting_queue import s_queue_put, s_queue_clear
    from ...services.collecting.llm_selection import s_llm_selection
    from ...services.collecting.save_selection_result import s_save_selection_result
    from ...services.reviewing.add_review import s_add_review, AUTHOR_AI
    from ...services.status.personal_info_update import s_update_personal_info_api

    # 验证收录条件
    msg = event.get_plaintext().strip()
    if not msg or msg == "" or len(msg) > cfg[event.group_id].collecting.msg_max_length:
        return
    
    # 加入队列并获取是否达到阈值
    with exception_report(ignore_all=True):
        is_thresold = await s_queue_put(
            group_id=str(event.group_id),
            msg_id=str(event.message_id),
            qq_id=str(event.user_id),
            content=msg,
            bot=bot,
        )

    # 以一定概率更新个人信息
    if random.random() < cfg[event.group_id].collecting.update_personal_info_probability:
        with exception_report(ignore_all=True):
            await s_update_personal_info_api(str(event.group_id), str(event.user_id), bot)

    # 未达到阈值，结束流程，否则尝试触发收录
    if not is_thresold:
        return
    
    # LLM 筛选
    with exception_report(ignore_all=True):
        response, usage = await s_llm_selection(str(event.group_id))
        logger.info(f"筛选到 {response.num_quotes} 条语录，输入 {usage.input_tokens} tokens，输出 {usage.output_tokens} tokens，总计 {usage.total_tokens} tokens")
    
    # 最终语录入库
    with exception_report(ignore_all=True):
        s_save_selection_result(str(event.group_id), response)
    
    # 清空队列
    with exception_report(ignore_all=True):
        s_queue_clear(str(event.group_id))
    
    # 为每条语录添加系统评论
    for quote in response.quotes:
        with exception_report(ignore_all=True):
            s_add_review(AUTHOR_AI, quote.id, quote.comment)
