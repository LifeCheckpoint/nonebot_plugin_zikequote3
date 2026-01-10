from ...imports import *

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
    from ...templates import migration
    from ...templates.schema.migration import DiffItem
    
    return migration.render_migration_diff(
        status_title="语录管理操作",
        title="群语录迁移确认",
        description=f"本次迁移将{'完全覆盖 (不保留) ' if overwrite else '合并'}目标群语录，并将{'不' if duplicate else ''}对语录去重，不在目标群的用户语录{'不会' if exclude_member else '依然将'}被导入新群，源群的用户信息{'不会' if clear_member_info else '同时将'}被导入到目标群，且源群的消息记录{'不会' if keep_source else '将'}被抹除。请在一分钟内查看控制台输出的 token 并确认。",
        diff_items=[
            DiffItem(label="语录迁移方向", oldval=source, newval=target),
            DiffItem(label="来源群语录数", oldval=str(source_quotes_num), newval="0" if not keep_source else str(source_quotes_num)),
            DiffItem(label="目标群语录数", oldval=str(before_quotes_num), newval=str(after_quotes_num)),
            DiffItem(label="收录成员数量", oldval=str(before_members_num), newval=str(after_members_num)),
        ],
        left_button="发送任意内容取消",
        right_button="发送“确认 token”执行",
    )