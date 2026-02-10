from .imports import *

class GroupBase(BaseModel):
    """群组基础模型"""
    group_id: str = Field(..., description="群号，主键")
    name: str = Field(..., description="群名称")

class GroupCreate(GroupBase):
    """创建群组模型"""
    pass

class GroupUpdate(BaseModel):
    """更新群组模型"""
    name: Optional[str] = Field(None, description="群名称")

class Group(GroupBase):
    """完整群组模型"""
    model_config = ConfigDict(from_attributes=True)