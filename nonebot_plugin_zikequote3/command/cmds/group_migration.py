"""
群语录迁移命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。

注意：
- 迁移确认卡片通过 HtmlRenderServiceBase 渲染 migration 模板为图片。
- TokenManager 通过 DI 容器获取（APP scope 单例）。
"""

from __future__ import annotations

from nonebot import logger
from typing import Any

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment as MsgSeg
from nonebot_plugin_alconna import Match, Query

from ..command_definition import matcher_group_migration
from ...di import Inject, inject
from ...services import MigrationService, GroupService
from ...services.html_render_service import HtmlRenderServiceBase
from ...templates.registry import MIGRATION
from ...templates.schema.migration import (
    TemplateDiffItemData,
    TemplateMigrationData,
    render_migration_diff,
)
from ._error_handlers import command_error_handler
from ...utils.token_generate import TokenManager

@matcher_group_migration.handle()
@inject
async def handle_group_migration(
    event: GroupMessageEvent,
    source: Match[str],
    target: Match[str],
    overwrite: Query[bool] = Query("overwrite.value", False),
    duplicate: Query[bool] = Query("duplicate.value", False),
    exclude_member: Query[bool] = Query("exclude_member.value", False),
    clear_member_info: Query[bool] = Query("clear_member_info.value", False),
    keep_source: Query[bool] = Query("keep_source.value", False),
    migration_svc: MigrationService = Inject(MigrationService),
    group_svc: GroupService = Inject(GroupService),
    token_mgr: TokenManager = Inject(TokenManager),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """
    处理群语录迁移命令。

    批量迁移一个群的语录到另一个群，支持覆写、去重、排除非成员等选项。
    迁移前生成确认卡片，需用户输入 Token 确认后执行。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param source: Alconna 匹配的源群号参数
    :type source: Match[str]
    :param target: Alconna 匹配的目标群号参数
    :type target: Match[str]
    :param overwrite: 是否完全覆盖目标群语录
    :type overwrite: Query[bool]
    :param duplicate: 是否基于内容去重
    :type duplicate: Query[bool]
    :param exclude_member: 是否排除不在新群的成员语录
    :type exclude_member: Query[bool]
    :param clear_member_info: 是否清除源群用户群昵称信息
    :type clear_member_info: Query[bool]
    :param keep_source: 是否保留源群语录信息
    :type keep_source: Query[bool]
    :param migration_svc: 迁移服务（DI 注入）
    :type migration_svc: MigrationService
    :param group_svc: 群组服务（DI 注入）
    :type group_svc: GroupService
    :param token_mgr: Token 管理器（DI 注入）
    :type token_mgr: TokenManager
    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    """
    # 群聊存在性确认
    async with command_error_handler(
        matcher_group_migration, "群聊存在性确认"
    ):
        if not source.available or not target.available:
            await matcher_group_migration.finish(
                "请提供源群号和目标群号哦~"
            )

        if not await group_svc.group_exists(str(source.result)):
            await matcher_group_migration.finish(
                "呀呀，找不到来源群呢 >.<"
            )
        if not await group_svc.group_exists(str(target.result)):
            await matcher_group_migration.finish(
                "咦？我还没有目标群的信息哦，"
                "请在目标群启用语录功能哦"
            )

        if source.result == target.result:
            await matcher_group_migration.finish(
                "来源群不能与目标群相同哦~"
            )

    # 群聊语录信息统计
    result: dict[str, Any] = {}
    source_count = 0
    target_count = 0
    final_quotes: list[Any] = []
    final_count = 0
    before_members = 0
    after_members = 0

    async with command_error_handler(
        matcher_group_migration, "群聊语录信息统计"
    ):
        result = await migration_svc.prepare_migration(
            source=source.result,
            target=target.result,
            overwrite=overwrite.result,
            deduplicate=duplicate.result,
            exclude_non_member=exclude_member.result,
            keep_source=keep_source.result,
        )

        source_count = result["source_count"]
        target_count = result["target_count"]
        final_quotes = result["final_quotes"]
        final_count = result["final_count"]
        before_members = result["before_members"]
        after_members = result["after_members"]

        if source_count <= 0:
            await matcher_group_migration.finish(
                "来源群没有语录，无法进行迁移哦~"
            )

    # 生成 Token
    check_wait_time = 60
    token = token_mgr.generate(ttl=check_wait_time)
    logger.warning("迁移语录请求")
    logger.warning(
        "来源群：{} -> 目标群：{}", source.result, target.result,
    )
    logger.warning("TOKEN: {}", token)

    # 构建迁移确认卡片数据
    migration_data = TemplateMigrationData(
        status_title="迁移确认",
        title="📋 群语录迁移",
        description=(
            f"来源群 {source.result} → 目标群 {target.result}"
        ),
        diff_items=[
            TemplateDiffItemData(
                label="来源群语录数",
                oldval=str(source_count),
                newval=str(source_count),
            ),
            TemplateDiffItemData(
                label="目标群语录数",
                oldval=str(target_count),
                newval=str(final_count),
            ),
            TemplateDiffItemData(
                label="覆写模式",
                oldval="-",
                newval="是" if overwrite.result else "否",
            ),
            TemplateDiffItemData(
                label="去重",
                oldval="-",
                newval="是" if duplicate.result else "否",
            ),
            TemplateDiffItemData(
                label="排除非成员",
                oldval="-",
                newval="是" if exclude_member.result else "否",
            ),
            TemplateDiffItemData(
                label="清除源群信息",
                oldval="-",
                newval="是" if clear_member_info.result else "否",
            ),
            TemplateDiffItemData(
                label="保留源群语录",
                oldval="-",
                newval="是" if keep_source.result else "否",
            ),
            TemplateDiffItemData(
                label="成员数",
                oldval=str(before_members),
                newval=str(after_members),
            ),
        ],
        right_button=f"确认 {token}",
        left_button="取消",
    )

    # 尝试渲染为图片，失败时降级为纯文本
    confirm_fallback_text = (
        f"📋 群语录迁移确认\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"来源群：{source.result}\n"
        f"目标群：{target.result}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"来源群语录数：{source_count}\n"
        f"目标群原语录数：{target_count}\n"
        f"迁移后语录数：{final_count}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"覆写模式：{'是' if overwrite.result else '否'}\n"
        f"去重：{'是' if duplicate.result else '否'}\n"
        f"排除非成员：{'是' if exclude_member.result else '否'}\n"
        f"清除源群信息：{'是' if clear_member_info.result else '否'}\n"
        f"保留源群语录：{'是' if keep_source.result else '否'}\n"
        f"成员变化：{before_members} → {after_members}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )

    token_hint = (
        f"请输入「确认 {token}」执行迁移"
        f"（{check_wait_time}秒内有效）"
    )

    try:
        html = render_migration_diff(migration_data)
        img = await html_render_svc.render(
            html, width=MIGRATION.width, height=MIGRATION.height,
        )
        prompt_msg = MsgSeg.image(img) + token_hint
    except Exception as e:
        logger.warning("迁移确认卡片图片渲染失败，降级为纯文本: {}", e)
        prompt_msg = confirm_fallback_text + token_hint

    import nonebot_plugin_waiter as waiter

    resp = await waiter.prompt(  # type: ignore[misc]
        prompt_msg, timeout=check_wait_time,
    )

    if resp is None:
        await matcher_group_migration.finish("已取消迁移操作~")
    msgs = resp.extract_plain_text().split(" ")

    if len(msgs) != 2 or msgs[0] != "确认":
        await matcher_group_migration.finish("已取消迁移操作~")

    token_suc, reason = token_mgr.verify_and_use(msgs[1].strip())
    if not token_suc:
        await matcher_group_migration.finish(
            f"Token 验证失败喵~ 原因：{reason}"
        )

    # 验证成功，执行迁移
    async with command_error_handler(
        matcher_group_migration, "群聊语录迁移执行"
    ):
        await migration_svc.execute_migration(
            final_quotes=final_quotes,
            source=str(source.result),
            target=str(target.result),
            overwrite=overwrite.result,
            keep_source=keep_source.result,
            clear_member_info=clear_member_info.result,
            deduplicate=duplicate.result,
            exclude_non_member=exclude_member.result,
        )

        await matcher_group_migration.finish(
            f"迁移成功！\n"
            f"已将 {source_count} 条语录从 "
            f"{source.result} 迁移至 {target.result}。\n"
            f"最终目标群语录数：{final_count}。"
        )
