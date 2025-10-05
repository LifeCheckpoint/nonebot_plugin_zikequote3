from ...imports import *
from pydantic import BaseModel, Field

class QuotePickupItem(BaseModel):
    id: str = Field(..., description="消息 ID")
    quote: str = Field(..., description="语录内容")
    comment: str = Field(..., description="简要评述")

class LLMSelectionResponse(BaseModel):
    num_quotes: int = Field(..., description="筛选出的语录数量")
    quotes: List[QuotePickupItem] = Field(..., description="筛选出的语录列表")


async def s_llm_selection(group_id: str):
    """
    使用 LLM 对收集队列中的消息进行筛选
    """
    from ...llm_services.client import create_model, send_llm_request_json2model
    from ...llm_services.prompts import quote_pickup

    with exception_report("获取缓存队列消息"):
        # 获取消息，并转换为元组列表
        messages = db.dao.get_msg_queue_dao().get_msgs_by_group(
            group_id,
            limit=cfg[int(group_id)].collecting.pickup_interval
        )

        if len(messages) == 0:
            raise ValueError("消息队列为空，请检查配置逻辑正确性")

        messages_tuple = [(
            msg.msg_id,
            db.dao.get_group_nickname_dao().get_current_group_nickname(str(msg.qq_id), group_id) or str(msg.qq_id),
            msg.content
        ) for msg in messages]
    
    with exception_report("创建 LLM 模型"):
        model = create_model(int(group_id))
    
    with exception_report("构建 LLM prompt"):
        prompt = quote_pickup.quote_pickup(int(group_id), messages_tuple)
    
    with exception_report("LLM 语录筛选请求"):
        response, usage = await send_llm_request_json2model(
            int(group_id),
            model,
            prompt,
            LLMSelectionResponse
        )
        return response, usage
    