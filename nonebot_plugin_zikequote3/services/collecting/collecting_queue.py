from ...imports import *

def s_queue_put(group_id: str, msg_id: str, qq_id: str, content: str) -> bool:
    """
    将消息放入收录队列

    Returns:
        bool: 是否达到收录阈值
    """
    from ...database.models.msgs_queue import MsgQueueCreate
    try:
        db.dao.get_msg_queue_dao().create_msg(MsgQueueCreate(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=qq_id,
            content=content,
        ))
    except Exception as e:
        logger.error(f"消息入队失败: {e}")
        sentry_sdk.capture_exception(e)
        raise e

    # 更新收录计数
    try:
        db.dao.get_queue_count_dao().increment_count(group_id)
    except Exception as e:
        logger.error(f"更新收录计数失败: {e}")
        sentry_sdk.capture_exception(e)
        raise e
    
    # 检查是否达到收录阈值
    try:
        return db.dao.get_queue_count_dao().get_group_count(group_id) >= cfg[int(group_id)].collecting.pickup_interval
    except Exception as e:
        logger.error(f"检查收录阈值失败: {e}")
        sentry_sdk.capture_exception(e)
        raise e

 
def s_queue_clear(group_id: str):
    """
    清空收录队列
    """
    try:
        db.dao.get_msg_queue_dao().clear_group_queue(group_id)
    except Exception as e:
        logger.error(f"清空收录队列失败: {e}")
        sentry_sdk.capture_exception(e)
        raise e
    