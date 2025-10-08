from ....imports import *
from pydantic import BaseModel, Field

class QuotePickupItem(BaseModel):
    msg_id: str = Field(..., description="消息 ID")
    quote: str = Field(..., description="语录内容")
    comment: str = Field(..., description="简要评述")
    quote_id: Optional[str] = Field(None, description="语录 ID，仅在已存在语录时有值")

class LLMSelectionResponse(BaseModel):
    num_quotes: int = Field(..., description="筛选出的语录数量")
    quotes: List[QuotePickupItem] = Field(..., description="筛选出的语录列表")


async def s_llm_selection(group_id: str):
    """
    使用 LLM 对收集队列中的消息进行筛选
    """
    from ....llm_services.client import create_model, send_llm_request_json2model
    from ....llm_services.prompts import quote_pickup
    from ....services.user_management.user_service import s_get_user_current_display_name

    async with service_exception_a("获取缓存队列消息"):
        # 获取消息，并转换为元组列表
        messages = db.dao.get_msg_queue_dao().get_msgs_by_group(
            group_id,
            limit=cfg[int(group_id)].collecting.pickup_interval
        )

        if len(messages) == 0:
            raise ValueError("消息队列为空，请检查配置逻辑正确性")

        messages_tuple = [(
            msg.msg_id,
            s_get_user_current_display_name(str(msg.qq_id), group_id),
            msg.content
        ) for msg in messages]
    
    async with service_exception_a("创建 LLM 模型"):
        model = create_model(int(group_id))
    
    async with service_exception_a("构建 LLM prompt"):
        prompt = quote_pickup.quote_pickup(int(group_id), messages_tuple)
    
    async with service_exception_a("LLM 语录筛选请求"):
        logger.debug(f"LLM Selection Prompt: {prompt}")
        response, usage = await send_llm_request_json2model(
            group_id=int(group_id),
            model=model,
            content=prompt,
            response_model=LLMSelectionResponse
        )
        logger.debug(f"LLM Selection Raw Response: {response}")
        return response, usage
    