from ...imports import *

def s_queue_put(group_id: str, msg_id: str, qq_id: str, content: str) -> bool:
    """
    将消息放入收录队列

    Returns:
        bool: 是否达到收录阈值
    """
    from ...database.models.msgs_queue import MsgQueueCreate
    with error_report("消息入队"):
        db.dao.get_msg_queue_dao().create_msg(MsgQueueCreate(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=qq_id,
            content=content.strip(),
        ))

    with error_report("更新收录计数"):
        db.dao.get_queue_count_dao().increment_count(group_id)
    
    with error_report("检查收录阈值"):
        return db.dao.get_queue_count_dao().get_group_count(group_id) >= cfg[int(group_id)].collecting.pickup_interval

 
def s_queue_clear(group_id: str):
    """
    清空收录队列
    """
    with error_report("清空收录队列"):
        db.dao.get_msg_queue_dao().clear_group_queue(group_id)
    