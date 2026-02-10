"""消息队列 Pydantic DTO 定义。"""

from .imports import *


class MsgQueueBase(BaseModel):
    """消息队列基础模型。"""
    msg_id: str = Field(..., description="消息 ID，主键")
    group_id: str = Field(..., description="群号")
    qq_id: str = Field(..., description="发送者 QQ 号")
    content: str = Field(..., description="消息内容")

class MsgQueueCreate(MsgQueueBase):
    """创建消息队列记录模型。"""
    time_stamp: Optional[datetime] = Field(None, description="消息时间（为空时使用数据库默认值）")

class MsgQueue(MsgQueueBase):
    """完整消息队列模型。"""
    time_stamp: datetime = Field(..., description="消息时间")

class MsgQueueUpdate(BaseModel):
    """更新消息队列记录模型。"""
    content: Optional[str] = Field(None, description="消息内容")
