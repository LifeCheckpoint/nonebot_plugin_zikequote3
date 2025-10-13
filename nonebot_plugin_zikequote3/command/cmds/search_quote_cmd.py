from ...imports import *
from ..command_definition import *

@matcher_search_quote.handle()
async def f_search_quote(event: GroupME, arg: Message = CommandArg()):
    """
    语录搜索
    """