from ...imports import *

async def s_queue_put(group_id: str, msg_id: str, qq_id: str, content: str, bot: Bot) -> bool:
    """
    将消息放入收录队列

    Returns:
        bool: 是否达到收录阈值
    """
    from ..status.group_info_update import s_update_group_info_api
    
    with exception_report("检查群组存在性"):
        exists = db.dao.get_group_dao().group_exists(group_id)
    
    if not exists:
        with exception_report(f"创建群组 {group_id}"):
            await s_update_group_info_api(group_id, bot)

    with exception_report("消息入队"):
        db.dao.get_msg_queue_dao().create_msg(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=qq_id,
            content=content.strip(),
        )

    with exception_report("更新收录计数"):
        db.dao.get_queue_count_dao().increment_count(group_id)
    
    with exception_report("检查收录阈值"):
        return db.dao.get_queue_count_dao().get_group_count(group_id) >= cfg[int(group_id)].collecting.pickup_interval

 
def s_queue_clear(group_id: str):
    """
    清空收录队列
    """
    with exception_report("清空收录队列"):
        db.dao.get_msg_queue_dao().clear_group_queue(group_id)


def s_get_queue_length(group_id: str) -> int:
    """
    获取当前收录队列长度
    """
    with exception_report("获取收录队列长度"):
        return db.dao.get_queue_count_dao().get_group_count(group_id)