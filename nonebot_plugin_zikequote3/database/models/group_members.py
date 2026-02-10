"""群成员关系 Pydantic DTO 定义。"""

from .imports import *


class GroupMemberBase(BaseModel):
    """群成员关系基础模型。"""
    group_id: str = Field(..., description="群号")
    qq_id: str = Field(..., description="QQ 号")

class GroupMemberCreate(GroupMemberBase):
    """创建群成员关系模型。"""
    pass

class GroupMember(GroupMemberBase):
    """完整群成员关系模型。"""
    model_config = ConfigDict(from_attributes=True)
