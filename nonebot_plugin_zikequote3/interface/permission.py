from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupME
from typing import Optional
from ..imports import cfg

async def quote_permission(event: GroupME):
    return True