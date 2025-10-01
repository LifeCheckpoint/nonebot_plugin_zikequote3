from .imports import *

class MsgQuoteIDBase(BaseModel):
    """消息 ID 与语录 ID 映射基础模型"""
    msg_id: str = Field(..., description="消息 ID，主键")
    quote_id: str = Field(..., description="语录 ID")

class MsgQuoteIDCreate(MsgQuoteIDBase):
    """创建消息 ID 与语录 ID 映射模型"""
    pass

class MsgQuoteID(MsgQuoteIDBase):
    """完整消息 ID 与语录 ID 映射模型"""
    class Config:
        from_attributes = True