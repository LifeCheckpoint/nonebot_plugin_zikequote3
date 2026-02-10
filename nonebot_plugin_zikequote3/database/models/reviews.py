"""评论 Pydantic DTO 定义。"""

from .imports import *


class ReviewBase(BaseModel):
    """评论基础模型。"""
    review_id: str = Field(..., description="评论 ID，主键")
    author_id: str = Field(..., description="评论者 QQ 号")
    quote_id: str = Field(..., description="语录 ID")
    content: str = Field(..., description="评论内容")

class ReviewCreate(ReviewBase):
    """创建评论时的模型。"""
    pass

class Review(ReviewBase):
    """完整的评论模型。"""
    time_stamp: datetime = Field(..., description="评论时间")

class ReviewUpdate(BaseModel):
    """更新评论时的模型。"""
    content: Optional[str] = Field(None, description="评论内容")
