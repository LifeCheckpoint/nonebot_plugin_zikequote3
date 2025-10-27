from ...imports import *
from ..command_definition import *

@matcher_collecting_listener.handle()
async def f_collecting_listener(event: GroupME, bot: Bot):
    """
    监听群组消息，处理自动语录收集

    此事件不会向用户界面提供任何反馈
    """
    from ...services.quote_management.collection.llm_selection_service import s_llm_selection
    from ...services.quote_management.collection.lock_service import llm_collecting_locker as locker
    from ...services.quote_management.collection.queue_service import s_queue_put, s_queue_clear
    from ...services.quote_management.collection.save_service import s_save_selection_result
    from ...services.review_management.review_service import s_add_review, AUTHOR_AI
    from ...services.user_management.group_relationship_service import s_ensure_user_group_mapping
    from ...services.user_management.personal_info_service import s_update_personal_info_api

    # 验证收录条件
    msg = event.get_plaintext().strip()
    if not msg or msg == "" or len(msg) > cfg[event.group_id].collecting.msg_max_length:
        return
    
    is_thresold = None
    async with event_exception_a("收录与阈值检查", operation="finish"):
        is_thresold = await s_queue_put(
            group_id=str(event.group_id),
            msg_id=str(event.message_id),
            qq_id=str(event.user_id),
            content=msg,
            bot=bot,
        )

    # 概率更新
    if random.random() < cfg[event.group_id].collecting.update_personal_info_probability:
        async with event_exception_a("更新个人信息", operation="finish"):
            await s_update_personal_info_api(str(event.group_id), str(event.user_id), bot)
    
    # 检查用户-群映射存在性
    with event_exception(operation="ignore"):
        await s_ensure_user_group_mapping(str(event.group_id), str(event.user_id), bot)
    
    # 未达到阈值，结束流程，否则尝试触发收录
    if not is_thresold:
        return
    
    # 异步锁，防止多次触发
    if locker.is_locked(str(event.group_id)):
        logger.info(f"群 {event.group_id} 的 LLM 收录任务已在进行中，跳过本次触发")
        return

    async with locker.for_key(credential=str(event.group_id)):
        async with event_exception_a("LLM 筛选", operation="finish"):
            response, usage = await s_llm_selection(str(event.group_id))
            logger.info(f"筛选到 {response.num_quotes} 条语录，输入 {usage.input_tokens} tokens，输出 {usage.output_tokens} tokens，总计 {usage.total_tokens} tokens")
        
        with event_exception("入库", operation="finish"):
            response_with_qid = s_save_selection_result(str(event.group_id), response)
        
        for quote in response_with_qid.quotes:
            if quote.quote_id is not None:
                with event_exception("添加评论", operation="finish"):
                    s_add_review(AUTHOR_AI, quote.quote_id, quote.comment)
        
        with event_exception("清空队列", operation="finish"):
            s_queue_clear(str(event.group_id))
    
