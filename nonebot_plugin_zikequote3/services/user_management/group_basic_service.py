from ...imports import *


def s_check_group_exists(group_id: str) -> bool:
    """
    检查指定的群聊是否存在
    """
    with service_exception(f"检查群组 {group_id} 存在性"):
        return db.dao.group_dao.group_exists(group_id)
