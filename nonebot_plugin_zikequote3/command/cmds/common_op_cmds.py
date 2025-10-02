from ...imports import *
from ..comand_definition import *
from ...interface.message_handle import read_msg_and_pickup


@matcher_update_quote.handle()
async def f_update_quote(event: GroupME):
    """
    强制更新语录
    """
    await msend(matcher_update_quote, msg_quote_on_update)
    result = await read_msg_and_pickup(event.group_id)
    if result:
        await mfinish(matcher_update_quote, msg_quote_update_success)
    else:
        await mfinish(matcher_update_quote, msg_quote_update_failed)