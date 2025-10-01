from .imports import *

class UserNicknameBase(BaseModel):
    """用户昵称基础模型"""
    qq_id: str = Field(..., description="QQ 号")
    current_using: bool = Field(False, description="是否正在使用")
    name: str = Field(..., description="昵称")

class UserNicknameCreate(UserNicknameBase):
    """创建用户昵称模型"""
    pass

class UserNickname(UserNicknameBase):
    """完整用户昵称模型"""
    class Config:
        from_attributes = True