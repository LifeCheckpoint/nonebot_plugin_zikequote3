from ...imports import *

async def s_ensure_user_group_mapping(group_id: str, qq_id: str, bot: Bot):
    from ...services.user_management.group_info_service import s_update_group_info_api
    if not db.dao.get_group_dao().get_group_by_id(group_id):
        await s_update_group_info_api(group_id, bot)

    if not db.dao.get_group_member_dao().get_group_member(group_id, qq_id):
        db.dao.get_group_member_dao().create_group_member(
            group_id=group_id,
            qq_id=qq_id
        )
        logger.info(f"创建用户-群映射：用户 {qq_id} - 群 {group_id}")
