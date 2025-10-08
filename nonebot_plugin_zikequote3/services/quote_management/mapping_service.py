from ...imports import *


def s_create_mapping_from_msgid_to_quoteid(message_id: str, quote_id: str):
    """
    创建消息 ID 与语录 ID 的映射
    """
    with service_exception("创建消息 ID 与语录 ID 的映射"):
        suc = db.dao.get_mapping_dao().create_mapping(message_id, quote_id)
        if not suc:
            raise RuntimeError(f"创建消息 ID {message_id} 与语录 ID {quote_id} 的映射失败")


def s_get_mapping_by_msgid(message_id: str) -> Optional[str]:
    """
    根据消息 ID 获取映射关系

    Returns:
        result (Optional[str]): 映射的语录 ID，未找到则返回 None
    """
    with service_exception("获取消息 ID 与语录 ID 的映射"):
        msgid = db.dao.get_mapping_dao().get_mapping_by_msg_id(message_id)
        return msgid.quote_id if msgid is not None else None
