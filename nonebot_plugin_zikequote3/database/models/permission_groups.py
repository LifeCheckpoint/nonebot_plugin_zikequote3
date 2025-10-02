from .imports import *

class PermissionGroupBase(BaseModel):
    """权限组基础模型"""
    group_name: str = Field(..., description="权限组名称，主键")

class PermissionGroupCreate(PermissionGroupBase):
    """创建权限组模型"""
    be_collected: bool = Field(True, description="是否可被收集")
    get_quote: bool = Field(True, description="是否可获取语录")
    add_quote: bool = Field(True, description="是否可添加语录")
    search_quote: bool = Field(True, description="是否可搜索语录")
    review_quote: bool = Field(True, description="是否可评论语录")
    update_quote_self: bool = Field(True, description="是否可更新自己的语录")
    update_quote_group: bool = Field(False, description="是否可更新群内语录")
    delete_review_self: bool = Field(True, description="是否可删除自己的评论")
    delete_review_group: bool = Field(False, description="是否可删除群内评论")
    delete_quote_self: bool = Field(True, description="是否可删除自己的语录")
    delete_quote_group: bool = Field(False, description="是否可删除群内语录")
    modify_settings: bool = Field(False, description="是否可修改设置")
    common_operations: bool = Field(True, description="是否可进行普通操作")
    ban_others: bool = Field(False, description="是否可封禁他人")
    op_others: bool = Field(False, description="是否可设置他人权限")
    banop_others: bool = Field(False, description="是否可封禁他人")
    others: bool = Field(False, description="其他权限")

class PermissionGroupUpdate(BaseModel):
    """更新权限组模型"""
    be_collected: Optional[bool] = Field(None, description="是否可被收集")
    get_quote: Optional[bool] = Field(None, description="是否可获取语录")
    add_quote: Optional[bool] = Field(None, description="是否可添加语录")
    search_quote: Optional[bool] = Field(None, description="是否可搜索语录")
    review_quote: Optional[bool] = Field(None, description="是否可评论语录")
    update_quote_self: Optional[bool] = Field(None, description="是否可搜索语录")
    update_quote_group: Optional[bool] = Field(None, description="是否可更新群内语录")
    delete_review_self: Optional[bool] = Field(None, description="是否可删除自己的评论")
    delete_review_group: Optional[bool] = Field(None, description="是否可删除群内评论")
    delete_quote_self: Optional[bool] = Field(None, description="是否可删除自己的语录")
    delete_quote_group: Optional[bool] = Field(None, description="是否可删除群内语录")
    modify_settings: Optional[bool] = Field(None, description="是否可修改设置")
    common_operations: Optional[bool] = Field(None, description="是否可进行普通操作")
    ban_others: bool = Field(False, description="是否可封禁他人")
    op_others: Optional[bool] = Field(None, description="是否可设置他人权限")
    banop_others: Optional[bool] = Field(None, description="是否可封禁他人")
    others: Optional[bool] = Field(None, description="其他权限")

class PermissionGroup(PermissionGroupBase):
    """完整权限组模型"""
    class Config:
        from_attributes = True
