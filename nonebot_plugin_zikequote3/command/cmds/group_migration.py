from ...imports import *
from ..command_definition import *
from ..parse_helper import *


@matcher_group_migration.handle()
async def f_group_migration(
    event: GroupME,
    bot: Bot,
    source: Match[int],
    target: Match[int],
    overwrite: Query[bool] = Query("overwrite.value", False),
    duplicate: Query[bool] = Query("duplicate.value", False),
    exclude_member: Query[bool] = Query("exclude_member.value", False),
    clear_member_info: Query[bool] = Query("clear_member_info.value", False),
    keep_source: Query[bool] = Query("keep_source.value", False),
):
    """
    群语录迁移功能，批量迁移一个群的语录并进行合并
    """
    