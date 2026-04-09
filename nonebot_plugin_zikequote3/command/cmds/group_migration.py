"""
群语录迁移命令处理器。

通过显式的“预览 / 等待确认 / 执行”三阶段流程，
避免数据库会话跨越用户确认等待窗口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment as MsgSeg
from nonebot_plugin_alconna import Match, Query

from ..command_definition import matcher_group_migration
from ...di import Inject, inject
from ...services.group_service import GroupService
from ...services.html_render_service import HtmlRenderServiceBase
from ...services.migration_service import MigrationPreview, MigrationService
from ...templates.registry import MIGRATION
from ...templates.schema.migration import (
    TemplateDiffItemData,
    TemplateMigrationData,
    render_migration_diff,
)
from ._error_handlers import command_error_handler
from ...utils.token_generate import TokenManager

MIGRATION_CONFIRM_TIMEOUT = 60


@dataclass(slots=True, frozen=True)
class _MigrationPromptContext:
    preview: MigrationPreview
    token: str
    prompt_msg: Any


@inject
async def _group_exists(
    group_id: str,
    group_svc: GroupService = Inject(GroupService),
) -> bool:
    return await group_svc.group_exists(group_id)


@inject
async def _prepare_migration_preview(
    source_group_id: str,
    target_group_id: str,
    *,
    overwrite: bool,
    deduplicate: bool,
    exclude_non_member: bool,
    keep_source: bool,
    migration_svc: MigrationService = Inject(MigrationService),
) -> MigrationPreview:
    return await migration_svc.prepare_migration(
        source=source_group_id,
        target=target_group_id,
        overwrite=overwrite,
        deduplicate=deduplicate,
        exclude_non_member=exclude_non_member,
        keep_source=keep_source,
    )


@inject
async def _build_migration_prompt(
    source_group_id: str,
    target_group_id: str,
    *,
    preview: MigrationPreview,
    overwrite: bool,
    deduplicate: bool,
    exclude_non_member: bool,
    clear_member_info: bool,
    keep_source: bool,
    token_mgr: TokenManager = Inject(TokenManager),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> _MigrationPromptContext:
    token = token_mgr.generate(ttl=MIGRATION_CONFIRM_TIMEOUT)
    logger.warning("迁移语录请求")
    logger.warning("来源群：{} -> 目标群：{}", source_group_id, target_group_id)
    logger.warning("TOKEN: {}", token)

    migration_data = TemplateMigrationData(
        status_title="迁移确认",
        title="📋 群语录迁移",
        description=f"来源群 {source_group_id} → 目标群 {target_group_id}",
        diff_items=[
            TemplateDiffItemData(
                label="来源群语录数",
                oldval=str(preview.source_count),
                newval=str(preview.source_count),
            ),
            TemplateDiffItemData(
                label="目标群语录数",
                oldval=str(preview.target_count),
                newval=str(preview.final_count),
            ),
            TemplateDiffItemData(
                label="覆写模式",
                oldval="-",
                newval="是" if overwrite else "否",
            ),
            TemplateDiffItemData(
                label="去重",
                oldval="-",
                newval="是" if deduplicate else "否",
            ),
            TemplateDiffItemData(
                label="排除非成员",
                oldval="-",
                newval="是" if exclude_non_member else "否",
            ),
            TemplateDiffItemData(
                label="清除源群信息",
                oldval="-",
                newval="是" if clear_member_info else "否",
            ),
            TemplateDiffItemData(
                label="保留源群语录",
                oldval="-",
                newval="是" if keep_source else "否",
            ),
            TemplateDiffItemData(
                label="成员数",
                oldval=str(preview.before_members),
                newval=str(preview.after_members),
            ),
        ],
        right_button=f"确认 {token}",
        left_button="取消",
    )

    confirm_fallback_text = (
        f"📋 群语录迁移确认\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"来源群：{source_group_id}\n"
        f"目标群：{target_group_id}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"来源群语录数：{preview.source_count}\n"
        f"目标群原语录数：{preview.target_count}\n"
        f"迁移后语录数：{preview.final_count}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"覆写模式：{'是' if overwrite else '否'}\n"
        f"去重：{'是' if deduplicate else '否'}\n"
        f"排除非成员：{'是' if exclude_non_member else '否'}\n"
        f"清除源群信息：{'是' if clear_member_info else '否'}\n"
        f"保留源群语录：{'是' if keep_source else '否'}\n"
        f"成员变化：{preview.before_members} → {preview.after_members}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )
    token_hint = (
        f"请输入「确认 {token}」执行迁移"
        f"（{MIGRATION_CONFIRM_TIMEOUT}秒内有效）"
    )

    try:
        html = render_migration_diff(migration_data)
        img = await html_render_svc.render(
            html,
            width=MIGRATION.width,
            height=MIGRATION.height,
        )
        prompt_msg = MsgSeg.image(img) + token_hint
    except Exception as e:
        logger.warning("迁移确认卡片图片渲染失败，降级为纯文本: {}", e)
        prompt_msg = confirm_fallback_text + token_hint

    return _MigrationPromptContext(
        preview=preview,
        token=token,
        prompt_msg=prompt_msg,
    )


@inject
async def _verify_group_migration_token(
    token: str,
    token_mgr: TokenManager = Inject(TokenManager),
) -> tuple[bool, str]:
    return token_mgr.verify_and_use(token)


@inject
async def _execute_group_migration(
    snapshot,
    *,
    clear_member_info: bool,
    migration_svc: MigrationService = Inject(MigrationService),
) -> dict[str, Any]:
    return await migration_svc.execute_migration(
        snapshot=snapshot,
        clear_member_info=clear_member_info,
    )


@matcher_group_migration.handle()
async def handle_group_migration(
    event: GroupMessageEvent,
    source: Match[str],
    target: Match[str],
    overwrite: Query[bool] = Query("overwrite.value", False),
    duplicate: Query[bool] = Query("duplicate.value", False),
    exclude_member: Query[bool] = Query("exclude_member.value", False),
    clear_member_info: Query[bool] = Query("clear_member_info.value", False),
    keep_source: Query[bool] = Query("keep_source.value", False),
) -> None:
    """
    处理群语录迁移命令。

    批量迁移一个群的语录到另一个群，支持覆写、去重、排除非成员等选项。
    迁移前生成确认卡片，需用户输入 Token 确认后执行。

    实际依赖在各阶段内部通过 ``@inject`` 单独解析。

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
    """
    del event  # 事件对象当前仅用于保持命令签名兼容

    source_group_id = str(source.result) if source.available else ""
    target_group_id = str(target.result) if target.available else ""

    async with command_error_handler(matcher_group_migration, "群聊存在性确认"):
        if not source.available or not target.available:
            await matcher_group_migration.finish("请提供源群号和目标群号哦~")

        if not await _group_exists(source_group_id):
            await matcher_group_migration.finish("呀呀，找不到来源群呢 >.<")
        if not await _group_exists(target_group_id):
            await matcher_group_migration.finish(
                "咦？我还没有目标群的信息哦，请在目标群启用语录功能哦"
            )
        if source_group_id == target_group_id:
            await matcher_group_migration.finish("来源群不能与目标群相同哦~")

    async with command_error_handler(matcher_group_migration, "群聊语录信息统计"):
        preview = await _prepare_migration_preview(
            source_group_id,
            target_group_id,
            overwrite=overwrite.result,
            deduplicate=duplicate.result,
            exclude_non_member=exclude_member.result,
            keep_source=keep_source.result,
        )

    if preview.source_count <= 0:
        await matcher_group_migration.finish("来源群没有语录，无法进行迁移哦~")

    prompt_context = await _build_migration_prompt(
        source_group_id,
        target_group_id,
        preview=preview,
        overwrite=overwrite.result,
        deduplicate=duplicate.result,
        exclude_non_member=exclude_member.result,
        clear_member_info=clear_member_info.result,
        keep_source=keep_source.result,
    )

    import nonebot_plugin_waiter as waiter

    resp = await waiter.prompt(  # type: ignore[misc]
        prompt_context.prompt_msg,
        timeout=MIGRATION_CONFIRM_TIMEOUT,
    )
    if resp is None:
        await matcher_group_migration.finish("已取消迁移操作~")

    msgs = resp.extract_plain_text().split(" ")
    if len(msgs) != 2 or msgs[0] != "确认":
        await matcher_group_migration.finish("已取消迁移操作~")

    token_suc, reason = await _verify_group_migration_token(msgs[1].strip())
    if not token_suc:
        await matcher_group_migration.finish(f"Token 验证失败喵~ 原因：{reason}")

    async with command_error_handler(matcher_group_migration, "群聊语录迁移执行"):
        await _execute_group_migration(
            prompt_context.preview.snapshot,
            clear_member_info=clear_member_info.result,
        )
        await matcher_group_migration.finish(
            f"迁移成功！\n"
            f"已将 {prompt_context.preview.source_count} 条语录从 "
            f"{source_group_id} 迁移至 {target_group_id}。\n"
            f"最终目标群语录数：{prompt_context.preview.final_count}。"
        )
