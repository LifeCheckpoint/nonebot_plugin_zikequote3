from ...imports import *
from ..command_definition import *
from ..parse_helper import *


@matcher_group_migration.handle()
async def f_group_migration(
    event: GroupME,
    source: Match[str],
    target: Match[str],
    overwrite: Query[bool] = Query("overwrite.value", False),
    duplicate: Query[bool] = Query("duplicate.value", False),
    exclude_member: Query[bool] = Query("exclude_member.value", False),
    clear_member_info: Query[bool] = Query("clear_member_info.value", False),
    keep_source: Query[bool] = Query("keep_source.value", False),
):
    """
    群语录迁移功能，批量迁移一个群的语录并进行合并
    """
    from ...services.user_management.group_basic_service import s_check_group_exists
    from ...services.migration_management.group_migration_service import s_get_group_quote_migration_checkcard_html
    
    async with event_exception_failmsg_a(matcher_group_migration, "群聊存在性确认"):
        if not source.available or not target.available:
            await matcher_group_migration.finish("请提供源群号和目标群号哦~")
            
        if not s_check_group_exists(str(source.result)):
            await matcher_group_migration.finish("呀呀，找不到来源群呢 >.<")
        if not s_check_group_exists(str(target.result)):
            await matcher_group_migration.finish("咦？我还没有目标群的信息哦，请在目标群启用语录功能哦")

    # TODO: 测试
    migration_checker_html = s_get_group_quote_migration_checkcard_html(
        source=str(source.result),
        target=str(target.result),
        migration_mode="覆写" if overwrite.result else "合并",
        before_quotes_num=114514,
        after_quotes_num=1919810
    )
    migration_checker_card = await html_img_render(migration_checker_html, width=500, height=120)
    
    # 生成 Token，发出提示并等待用户确认
    check_wait_time = 60
    token = token_manager.generate(ttl = check_wait_time)
    logger.warning("迁移语录请求")
    logger.warning(f"来源群：{source.result} -> 目标群：{target.result}")
    logger.warning("------------------------------")
    logger.warning(f"TOKEN: {token}")
    logger.warning("------------------------------")
    logger.warning("输入“确认 token”执行")

    resp = await waiter.prompt(MsgSeg.image(migration_checker_card), timeout=check_wait_time)
    
    if resp == None:
        await matcher_group_migration.finish("已取消迁移操作~")
    msgs = resp.extract_plain_text().split(" ")
    
    if len(msgs) != 2 or msgs[0] != "确认":
        await matcher_group_migration.finish("已取消迁移操作~")

    token_suc, reason = token_manager.verify_and_use(msgs[1].strip())
    if not token_suc:
        await matcher_group_migration.finish(f"Token 验证失败喵~ 原因：{reason}")

    # TODO: 验证成功，执行迁移
    await matcher_group_migration.finish(f"模拟一下迁移（还没写好）")
