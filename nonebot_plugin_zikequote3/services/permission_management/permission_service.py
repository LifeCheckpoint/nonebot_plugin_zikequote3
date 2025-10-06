from __future__ import annotations

from ...imports import GroupME, db, default_cfg
from nonebot.permission import Permission as NBPermission
import logging
import sentry_sdk

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
    MODIFY_SETTINGS = "modify_settings"
    COMMON_OPERATIONS = "common_operations"
    BAN_OTHERS = "ban_others"
    BANOP_OTHERS = "banop_others"
    OTHERS = "others"

def permission_check(operator_type: str) -> QuotePermissionChecker:
    return QuotePermissionChecker(operator_type)


class QuotePermissionChecker(NBPermission):
    operator_type: str

    def __init__(self, operator_type: str):
        self.operator_type = operator_type

    async def __call__(self, event: GroupME) -> bool:
        group_id = str(event.group_id)
        qq_id = str(event.user_id)

        # 检查插件是否启用
        if not default_cfg.general.enable_zikequote3:
            return False
        
        # 检查群组是否在插件启用范围内
        if event.group_id not in default_cfg.general.enable_groups or str(event.group_id) not in default_cfg.general.enable_groups:
            return False

        # 检查该用户是否在群组关系中，若无则创建
        try:
            is_in_group = db.dao.get_group_member_dao().is_group_member_exists(group_id, qq_id)
            if not is_in_group:
                # 若不在群组关系中，则添加该成员，默认权限组为 "normal"
                db.dao.get_group_member_dao().update_or_create_member(group_id, qq_id, "normal")
        except Exception as e:
            logging.error(f"检查/创建用户群组关系失败，事件处理将被忽略: {e}")
            sentry_sdk.capture_exception(e)
            return False

        try:
            pms_group = db.dao.get_group_member_dao().get_member_permission_group(group_id, qq_id)
            is_static_root = event.user_id in default_cfg.permission.static_root
        except Exception as e:
            logging.error(f"获取用户权限组失败，事件处理将被忽略: {e}")
            sentry_sdk.capture_exception(e)
            return False
        
        if pms_group is None or pms_group == "":
            # 无权限组成员将被默认赋予 "normal" 权限组
            pms_group = "normal"
            # 向数据库写回该成员权限
            try:
                db.dao.get_group_member_dao().update_or_create_member(group_id, qq_id, pms_group)
            except Exception as e:
                logging.error(f"写回用户权限组失败，事件处理将被忽略: {e}")
                sentry_sdk.capture_exception(e)
                return False
    
        try:
            pms = db.dao.get_permission_dao().check_permission(pms_group, self.operator_type)
        except Exception as e:
            logging.error(f"检查权限组信息失败，事件处理将被忽略: {e}")
            sentry_sdk.capture_exception(e)
            return False
        
        return pms or is_static_root
