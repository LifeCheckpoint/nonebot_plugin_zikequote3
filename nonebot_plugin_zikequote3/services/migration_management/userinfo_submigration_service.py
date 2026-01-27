from ...imports import db, logger

async def s_migrate_user_infos(
    source_group: str,
    target_group: str,
    clear_member_info: bool
) -> bool:
    """
    执行用户信息迁移
    
    Args:
        source_group: 源群号
        target_group: 目标群号
        clear_member_info: 是否清除源群用户信息
    """
    member_dao = db.dao.get_group_member_dao()
    nickname_dao = db.dao.get_group_nickname_dao()
    
    # 迁移群成员关系
    source_members = member_dao.get_members_by_group(source_group)
    if source_members:
        source_qq_ids = [m.qq_id for m in source_members]
        logger.info(f"正在将 {len(source_qq_ids)} 名成员从源群 {source_group} 迁移至目标群 {target_group}...")
        # 批量添加到目标群
        member_dao.batch_add_members(target_group, source_qq_ids)
        
    # 迁移群名片
    source_nicknames = nickname_dao.get_nicknames_by_group(source_group)
    if source_nicknames:
        logger.info(f"正在迁移 {len(source_nicknames)} 条群名片记录...")
        for nickname in source_nicknames:
            # 强制作为历史记录导入 (current_using=False)
            try:
                nickname_dao.add_group_nickname(
                    qq_id=nickname.qq_id,
                    group_id=target_group,
                    current_using=False,
                    name=nickname.name
                )
            except Exception:
                # 忽略重复或其他插入错误
                pass
            
    # 清理源群信息
    if clear_member_info:
        logger.info(f"正在清理源群 {source_group} 的用户信息...")
        member_dao.delete_all_members_by_group(source_group)
        nickname_dao.clear_group_all_nicknames(source_group)
        
    return True
