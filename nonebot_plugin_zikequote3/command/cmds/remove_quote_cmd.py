from ...imports import *
from ..command_definition import *


@matcher_remove_quote.handle()
async def f_remove_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除语录
    """