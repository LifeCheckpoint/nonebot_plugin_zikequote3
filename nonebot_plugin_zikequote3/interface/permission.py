from __future__ import annotations

from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupME
from ..imports import db
import logging

class PMS:
    BE_COLLECTED = "be_collected"
    GET_QUOTE = "get_quote"
    ADD_QUOTE = "add_quote"
    SEARCH_QUOTE = "search_quote"
    REVIEW_QUOTE = "review_quote"
    UPDATE_QUOTE_SELF = "update_quote_self"
    UPDATE_QUOTE_GROUP = "update_quote_group"
    DELETE_REVIEW_SELF = "delete_review_self"
    DELETE_REVIEW_GROUP = "delete_review_group"
    DELETE_QUOTE_SELF = "delete_quote_self"
    DELETE_QUOTE_GROUP = "delete_quote_group"
    BAN_OTHERS = "ban_others"
    BANOP_OTHERS = "banop_others"
    OTHERS = "others"

async def permission_type(operator_type: str) -> QuotePermissionChecker:
    return QuotePermissionChecker(operator_type)

class QuotePermissionChecker:
    operator_type: str

    async def __init__(self, operator_type: str):
        self.operator_type = operator_type

    async def __call__(self, event: GroupME) -> bool:
        group_id = str(event.group_id)
        qq_id = str(event.user_id)

        try:
            pms_group = db.dao.get_group_member_dao().get_member_permission_group(group_id, qq_id)
        except Exception as e:
            logging.error(f"获取用户权限组失败，事件处理将被忽略: {e}")
            return False
        
        if pms_group is None:
            logging.info(f"用户 {qq_id} 在群 {group_id} 中无权限组，事件处理将被忽略")
            return False
    
        try:
            pms = db.dao.get_permission_dao().check_permission(pms_group, self.operator_type)
        except Exception as e:
            logging.error(f"检查权限组信息失败，事件处理将被忽略: {e}")
            return False
        
        return pms
