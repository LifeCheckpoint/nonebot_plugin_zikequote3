from .imports import *

class GroupNicknameBase(BaseModel):
    """群名片基础模型"""
    qq_id: str = Field(..., description="QQ 号")
    group_id: str = Field(..., description="群号")
    current_using: bool = Field(False, description="是否正在使用")
    name: str = Field(..., description="群名片名称")

class GroupNicknameCreate(GroupNicknameBase):
    """创建群名片模型"""
    pass

class GroupNickname(GroupNicknameBase):
    """完整群名片模型"""
    class Config:
        from_attributes = True
