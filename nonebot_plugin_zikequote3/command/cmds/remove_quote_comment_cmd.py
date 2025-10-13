from ...imports import *
from ..command_definition import *


@matcher_del_comment.handle()
async def f_del_comment(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除评论

    语录删除评论方式：
    `/删评论 评论ID`
    """