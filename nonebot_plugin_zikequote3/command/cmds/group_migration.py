"""
群语录迁移命令处理器（dishka DI 版本）。

替代旧的 group_migration.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

注意：
- 旧版本使用 HTML 截图生成迁移确认卡片，新版本暂用文本方式展示。
- waiter 和 token_manager 是工具模块，保留引用。
"""

from __future__ import annotations

import logging
from typing import Any

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_alconna import Match, Query

from ..command_definition import matcher_group_migration
from ...di import get_container
from ...services import MigrationService, GroupService
from ...utils.error_report import event_exception_failmsg_a
from ...utils.token_generate import TokenManager

logger = logging.getLogger(__name__)

# Token 管理器实例
_token_manager = TokenManager()


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
    """群语录迁移功能，批量迁移一个群的语录并进行合并。"""
    container = get_container()
    async with container() as request_scope:
        migration_svc = await request_scope.get(MigrationService)
        group_svc = await request_scope.get(GroupService)

        # 群聊存在性确认
        async with event_exception_failmsg_a(
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

        async with event_exception_failmsg_a(
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

        # 生成确认信息（文本方式）
        # TODO: 旧版本使用 HTML 截图生成迁移确认卡片图片，
        # 新版本暂用文本方式展示，后续可恢复图片方式。
        confirm_text = (
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

        # 生成 Token，发出提示并等待用户确认
        check_wait_time = 60
        token = _token_manager.generate(ttl=check_wait_time)
        logger.warning("迁移语录请求")
        logger.warning(
            "来源群：%s -> 目标群：%s", source.result, target.result,
        )
        logger.warning("TOKEN: %s", token)

        import nonebot_plugin_waiter as waiter

        prompt_msg = (
            confirm_text
            + f"请输入「确认 {token}」执行迁移"
            + f"（{check_wait_time}秒内有效）"
        )
        resp = await waiter.prompt(  # type: ignore[misc]
            prompt_msg, timeout=check_wait_time,
        )

        if resp is None:
            await matcher_group_migration.finish("已取消迁移操作~")
        msgs = resp.extract_plain_text().split(" ")

        if len(msgs) != 2 or msgs[0] != "确认":
            await matcher_group_migration.finish("已取消迁移操作~")

        token_suc, reason = _token_manager.verify_and_use(msgs[1].strip())
        if not token_suc:
            await matcher_group_migration.finish(
                f"Token 验证失败喵~ 原因：{reason}"
            )

        # 验证成功，执行迁移
        await migration_svc.execute_migration(
            final_quotes=final_quotes,
            source=str(source.result),
            target=str(target.result),
            overwrite=overwrite.result,
            keep_source=keep_source.result,
            clear_member_info=clear_member_info.result,
        )

        await matcher_group_migration.finish(
            f"迁移成功！\n"
            f"已将 {source_count} 条语录从 "
            f"{source.result} 迁移至 {target.result}。\n"
            f"最终目标群语录数：{final_count}。"
        )
