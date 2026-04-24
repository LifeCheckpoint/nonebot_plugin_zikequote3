"""语录去重命令处理器。"""

from __future__ import annotations

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.params import CommandArg

from ..command_definition import matcher_quote_deduplicate, perm_nodes
from ...di import Inject, inject
from ...exceptions import PermissionDeniedError, ValidationException
from ...services import QuoteWriteService
from ._error_handlers import command_error_handler


def _parse_user_only_flag(arg_text: str) -> bool:
    """解析 ``/语录去重`` 命令参数。"""
    if arg_text == "":
        return False
    if arg_text == "--user_only":
        return True
    raise ValidationException("仅支持可选参数 --user_only")


@matcher_quote_deduplicate.handle()
@inject
async def handle_quote_deduplicate(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
) -> None:
    """处理群组语录去重命令。"""
    group_id = str(event.group_id)
    operator_id = str(event.user_id)
    arg_text = arg.extract_plain_text().strip()

    async with command_error_handler(matcher_quote_deduplicate, "语录去重"):
        user_only = _parse_user_only_flag(arg_text)

        if user_only:
            allowed = await perm_nodes.n_quote_delete_self.check(
                bot,
                event,
                throw_on_fail=False,
            )
            if not allowed:
                raise PermissionDeniedError("缺少去重自己语录权限")
        else:
            allowed = await perm_nodes.n_quote_delete_others.check(
                bot,
                event,
                throw_on_fail=False,
            )
            if not allowed:
                raise PermissionDeniedError("缺少全群语录去重权限")

        result = await quote_write_svc.deduplicate_group_quotes(
            group_id,
            operator_id=operator_id,
            user_only=user_only,
        )

    scope_text = "仅当前用户" if result.user_only else "当前群全部成员"
    summary = (
        "语录去重完成\n"
        f"作用范围：{scope_text}\n"
        f"数据库备份：{result.backup_path}\n"
        f"检查语录：{result.scanned_count} 条\n"
        f"重复内容组：{result.duplicate_groups} 组\n"
        f"删除重复语录：{result.deleted_count} 条\n"
        f"保留较早语录：{result.kept_count} 条"
    )
    await matcher_quote_deduplicate.finish(summary)
