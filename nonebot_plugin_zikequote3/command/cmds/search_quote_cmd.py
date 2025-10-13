from ...imports import *
from ..command_definition import *

@matcher_quote_search.handle()
async def f_quote_search(event: GroupME, arg: Message = CommandArg()):
    """
    语录搜索
    """