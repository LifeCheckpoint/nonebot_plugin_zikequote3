from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupME
from nonebot import get_plugin_config
from typing import Optional
from ..imports import cfg

def is_quote_manager(user_id: Optional[int]) -> bool:
    """
    检查用户是否为语录管理者
    """
    return user_id in cfg.permission.quote_managers

async def quote_permission(event: GroupME):
    """
    群权限管理，可用白名单或黑名单
    """
    if not cfg.enable:
        return False
    
    match cfg.permission.mode_group:
        case "white":
            group_permission = event.group_id in cfg.permission.white_group_list
        case "black":
            group_permission = event.group_id not in cfg.permission.black_group_list
        case _:
            print("权限模式错误，请检查配置")
            group_permission = False

    match cfg.permission.mode_user:
        case "white":
            user_permission = event.user_id in cfg.permission.white_user_list
        case "black":
            user_permission = event.user_id not in cfg.permission.black_user_list
        case _:
            print("权限模式错误，请检查配置")
            user_permission = False

    if group_permission == user_permission:
        permission = group_permission
    else:
        # 如果群组和用户权限不一致，使用默认权限
        match cfg.permission.default_permission:
            case "group":
                permission = group_permission
            case "user":
                permission = user_permission
            case True:
                permission = True
            case False:
                permission = False
            
    return permission