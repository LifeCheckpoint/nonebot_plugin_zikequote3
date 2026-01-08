from ...imports import *

def s_get_group_quote_migration_checkcard_html(
    source: str,
    target: str,
    migration_mode: str,
    before_quotes_num: int,
    after_quotes_num: int,
) -> str:
    """
    获取语录迁移提示

    Args:
        source (str): 源群
        target (str): 目标群
        migration_mode (str): 迁移模式名称
        before_quotes_num (int): 迁移前语录条数
        after_quotes_num (int): 迁移后语录条数
    """
    from ...templates import migration
    from ...templates.schema.migration import DiffItem
    
    # TODO: 迁移提示信息
    return migration.render_migration_diff(
        status_title="语录管理操作",
        title="群语录迁移确认",
        describtion="现在这还只是一个测试，并不能实际迁移，需要填充各类参数。请在一分钟内查看控制台输出的 token 并确认。",
        diff_items=[
            DiffItem(label="迁移方向", oldval=source, newval=target),
            DiffItem(label=f"语录条数 ({migration_mode}模式)", oldval=str(before_quotes_num), newval=str(after_quotes_num)),
        ],
        left_button="发送任意内容取消",
        right_button="发送“确认 token”执行",
    )