"""语录 Pydantic DTO 定义。"""

from .imports import *


class QuoteBase(BaseModel):
    """语录基础模型。"""
    quote_id: str = Field(..., description="语录 ID，主键")
    author_id: str = Field(..., description="作者 QQ 号")
    group_id: str = Field(..., description="群号")
    content: Optional[str] = Field(..., description="语录内容")
    image_content_uuid: Optional[str] = Field(None, description="关联的图片 UUID")
    total_show_time: int = Field(0, description="总展示次数")

class QuoteCreate(QuoteBase):
    """创建语录模型。"""
    pass

class QuoteUpdate(BaseModel):
    """更新语录模型。"""
    content: Optional[str] = Field(None, description="语录内容")
    image_content_uuid: Optional[str] = Field(None, description="关联的图片 UUID")
    total_show_time: Optional[int] = Field(None, description="总展示次数")

class Quote(QuoteBase):
    """完整语录模型。"""
    time_stamp: datetime = Field(..., description="创建时间")
    