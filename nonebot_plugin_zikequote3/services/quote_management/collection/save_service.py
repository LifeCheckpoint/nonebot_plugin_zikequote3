from ....imports import *
from .llm_selection_service import LLMSelectionResponse

def s_save_selection_result(group_id: str, response: LLMSelectionResponse):
    for i, quote in enumerate(response.quotes):
        with service_exception(f"LLM 消息反查: {quote.msg_id}", True):
            message_data = db.dao.get_msg_queue_dao().get_msg_by_id(quote.msg_id)
            if message_data is None:
                raise ValueError(f"消息数据未找到: {quote.msg_id}")
        
        if not cfg[int(group_id)].collecting.enable_duplicate:
            with service_exception(f"LLM 消息去重: {quote.msg_id}", True):
                exists = db.dao.get_quote_dao().check_quote_exists_by_author_content(message_data.qq_id, quote.quote)

                if exists:
                    continue

        with service_exception(f"LLM 消息入库: {quote.msg_id}", True):
            quote_id = str(random.randint(10 ** 10, 10 ** 11 - 1))
            success = db.dao.get_quote_dao().create_quote(
                quote_id=quote_id,
                author_id=message_data.qq_id,
                group_id=group_id,
                content=quote.quote,
                image_content_uuid=None,
                total_show_time=0
            )
            response.quotes[i].quote_id = quote_id

            if not success:
                raise ValueError(f"语录入库失败: {quote.msg_id}，请检查 DAO 层")
            
    return response