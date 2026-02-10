"""群消息计数 Pydantic DTO 定义。"""

from .imports import *


class QueueGroupMessageCountBase(BaseModel):
    """群消息计数基础模型。"""
    group_id: str = Field(..., description="群号")
    message_count: int = Field(0, description="消息计数")

class QueueGroupMessageCountCreate(QueueGroupMessageCountBase):
    """创建群消息计数模型。"""
    pass

class QueueGroupMessageCount(QueueGroupMessageCountBase):
    """完整群消息计数模型。"""
    model_config = ConfigDict(from_attributes=True)