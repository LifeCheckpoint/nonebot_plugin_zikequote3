from ...imports import *
from ..command_definition import *


@matcher_update_quote.handle()
async def f_update_quote(event: GroupME, state: T_State):
    """
    强制更新语录

    与自动收集命令流程类似
    """    
    from ...services.quote_management.collection.queue_service import s_queue_clear
    from ...services.quote_management.collection.llm_selection_service import s_llm_selection
    from ...services.quote_management.collection.save_service import s_save_selection_result
    from ...services.review_management.review_service import s_add_review, AUTHOR_AI
    from ...services.quote_management.collection.lock_service import llm_collecting_locker as locker

    # 异步锁，防止多次触发
    if locker.is_locked(str(event.group_id)):
        await matcher_update_quote.finish("当前已有更新任务在进行中，请稍后再试~")
    
    async with locker.for_key(credential=str(event.group_id)):
        async with event_exception_failmsg_a(matcher_update_quote, "语录强制更新"):
            # LLM 筛选
            response, usage = await s_llm_selection(str(event.group_id))
            logger.info(f"筛选到 {response.num_quotes} 条语录，输入 {usage.input_tokens} tokens，输出 {usage.output_tokens} tokens，总计 {usage.total_tokens} tokens")
        
            # 最终语录入库
            s_save_selection_result(str(event.group_id), response)
        
            # 清空队列
            s_queue_clear(str(event.group_id))
        
            # 为每条语录添加系统评论
            for quote in response.quotes:
                with event_exception(operation="ignore"):
                    s_add_review(AUTHOR_AI, quote.msg_id, quote.comment)

            await matcher_update_quote.finish(f"本次语录更新完成，共新增 {response.num_quotes} 条语录~")
