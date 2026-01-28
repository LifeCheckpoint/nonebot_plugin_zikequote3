from ...imports import *
from ...database.models.quotes import Quote


def s_get_group_quote_migration_checkcard_html(
    source: str,
    target: str,
    overwrite: bool,
    before_quotes_num: int,
    after_quotes_num: int,
    duplicate: bool,
    exclude_member: bool,
    clear_member_info: bool,
    keep_source: bool,
    before_members_num: int,
    after_members_num: int,
    source_quotes_num: int,
) -> str:
    """
    获取语录迁移提示

    Args:
        source (str): 源群
        target (str): 目标群
        overwrite (bool): 迁移是否完全覆盖目标群语录
        before_quotes_num (int): 迁移前语录条数
        after_quotes_num (int): 迁移后语录条数
        duplicate (bool): 是否去重
        exclude_member (bool): 是否排除非目标群成员语录
        clear_member_info (bool): 是否清除来源群用户群昵称信息
        keep_source (bool): 是否保留来源群语录记录
        before_members_num (int): 迁移前目标群收录成员数量
        after_members_num (int): 迁移后目标群收录成员数量
        source_quotes_num (int): 来源群语录条数
    """
    from ...templates.schema.migration import render_migration_diff, TemplateDiffItemData, TemplateMigrationData
    
    return render_migration_diff(
        TemplateMigrationData(
            status_title="语录管理操作",
            title="群语录迁移确认",
            description=f"本次迁移将{'完全覆盖 (不保留) ' if overwrite else '合并'}目标群语录，" \
                         "并将{'不' if duplicate else ''}对语录去重，" \
                         "不在目标群的用户语录{'不会' if exclude_member else '依然将'}被导入新群，" \
                         "源群的用户信息{'不会' if clear_member_info else '同时将'}被导入到目标群，" \
                         "且源群的消息记录{'不会' if keep_source else '将'}被抹除。" \
                         "请在一分钟内查看控制台输出的 token 并确认。",
            diff_items=[
                TemplateDiffItemData(label="语录迁移方向", oldval=source, newval=target),
                TemplateDiffItemData(label="来源群语录数", oldval=str(source_quotes_num), newval="0" if not keep_source else str(source_quotes_num)),
                TemplateDiffItemData(label="目标群语录数", oldval=str(before_quotes_num), newval=str(after_quotes_num)),
                TemplateDiffItemData(label="收录成员数量", oldval=str(before_members_num), newval=str(after_members_num)),
            ],
            left_button="发送任意内容取消",
            right_button="发送“确认 token”执行",
            )
        )


async def s_prepare_comparison_process(
    source: str,
    target: str,
    overwrite: bool,
    duplicate: bool,
    exclude_member: bool,
    keep_source: bool,
):
    """
    统计迁移过程所需的所有信息

    Args:
        source (str): 源群
        target (str): 目标群
        overwrite (bool): 迁移是否完全覆盖目标群语录
        duplicate (bool): 是否去重
        exclude_member (bool): 是否排除非目标群成员语录
        keep_source (bool): 是否保留来源群语录记录
    
    Returns:
        Tuple[str, int], Tuple[str, int], Tuple[str, int], Tuple[int, int]:
        分别为来源群语录及数量，目标群语录及数量，最终合并结果语录及数量，(迁移前成员数, 迁移后成员数)
    """
    import itertools
    from ...services.quote_management.showcase.basic_quote_service import s_get_quote_by_group
    from ...services.user_management.group_relationship_service import s_get_all_users_by_group

    def duplicate_id_process(quotes: List[Quote], force_new_ids_for_source: bool = False, source_ids: set | None = None):
        """
        重复 ID 处理
        """
        # 获取全局最大 ID
        max_id = db.dao.get_quote_dao().get_max_quote_id()
        # 也要考虑当前列表中的 ID (因为可能比 DB 中的大)
        current_max = max(int(q.quote_id) for q in quotes) if quotes else 0
        start_id = max(max_id, current_max) + 1
        
        new_id_gen = (str(i) for i in itertools.count(start_id))
        seen = set()
        
        for q in quotes:
            # 如果需要强制为源群语录生成新 ID
            if force_new_ids_for_source and source_ids and q.quote_id in source_ids:
                q.quote_id = next(new_id_gen)
                continue

            if q.quote_id in seen:
                q.quote_id = next(new_id_gen)
            seen.add(q.quote_id)
        return quotes


    def duplicate_quote_content_process(quotes: List[Quote]):
        """
        基于作者、内容及图片去重，并累加重复项的展示次数
        """
        merged: dict[tuple, Quote] = {}
        for q in quotes:
            fingerprint = (q.author_id, q.content, q.image_content_uuid)
            if fingerprint in merged:
                # 当前语录的次数累加
                merged[fingerprint].total_show_time += q.total_show_time
            else:
                merged[fingerprint] = q
        return list(merged.values())


    async with service_exception_a("获取群聊语录与用户统计信息"):
        source_group_quotes = s_get_quote_by_group(str(source))
        target_group_quotes = s_get_quote_by_group(str(target))
        source_group_users = [s.qq_id for s in await s_get_all_users_by_group(str(source))]
        target_group_users = [s.qq_id for s in await s_get_all_users_by_group(str(target))]

    with service_exception("统计迁移语录信息"):
        # 记录源群 ID 集合，用于后续判断
        source_ids = {q.quote_id for q in source_group_quotes}

        # 覆写模式
        if not overwrite:
            final_group_quotes = source_group_quotes + target_group_quotes
        else:
            final_group_quotes = source_group_quotes
        
        # 更改语录集归属
        for q in final_group_quotes:
            q.group_id = target
        
        # 包含非交集用户处理
        if exclude_member:
            final_group_quotes = [q for q in final_group_quotes if q.author_id in target_group_users]

        # 去重处理
        if duplicate:
            final_group_quotes = duplicate_quote_content_process(final_group_quotes)

        # 处理可能的重复 ID
        # 如果保留源群，则源群过来的语录必须生成新 ID
        final_group_quotes = duplicate_id_process(
            final_group_quotes,
            force_new_ids_for_source=keep_source,
            source_ids=source_ids
        )

        source_quotes_num = len(source_group_quotes)
        target_quotes_num = len(target_group_quotes)
        final_quotes_num = len(final_group_quotes)

    with service_exception("统计迁移用户信息"):
        before_members_num = len(target_group_users)
        # 迁移后成员数量 = 目标群原有成员 + 源群成员 (去重)
        all_members = set(target_group_users) | set(source_group_users)
        after_members_num = len(all_members)
        
        return (
            (source_group_quotes, source_quotes_num), 
            (target_group_quotes, target_quotes_num), 
            (final_group_quotes, final_quotes_num),
            (before_members_num, after_members_num)
        )


async def s_execute_group_migration(
    final_quotes: List[Quote],
    source_group: str,
    target_group: str,
    overwrite: bool,
    duplicate: bool,
    exclude_member: bool,
    clear_member_info: bool,
    keep_source: bool
) -> bool:
    """
    执行群迁移
    """
    from .quote_submigration_service import s_migrate_quotes
    from .userinfo_submigration_service import s_migrate_user_infos
    
    # 在执行迁移前备份数据库
    logger.info("正在创建数据库备份...")
    db.backup_database()

    async with service_exception_a("执行语录迁移"):
        await s_migrate_quotes(
            final_quotes=final_quotes,
            source_group=source_group,
            target_group=target_group,
            overwrite=overwrite,
            keep_source=keep_source
        )
        
    async with service_exception_a("执行用户信息迁移"):
        await s_migrate_user_infos(
            source_group=source_group,
            target_group=target_group,
            clear_member_info=clear_member_info
        )
        
    return True
