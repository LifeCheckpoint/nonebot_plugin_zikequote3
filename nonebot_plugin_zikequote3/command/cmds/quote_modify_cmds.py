from ...imports import *
from ..comand_definition import *
from ...interface.message_handle import (
    get_group_member_cardname,
    get_mapping
)


@matcher_add_quote.handle()
async def f_add_quote(event: GroupME, bot: Bot):
    """
    添加语录

    语录添加方式有两种，通过是否有 reply 进行判断：
    1. `(reply) /加语录`
    2. `/加语录 @某人 语录内容`
    """
    # 判断 reply
    reply = event.reply

    if reply != None:
        reply_msg = reply.message.extract_plain_text().strip()
        if reply_msg == "":
            await mfinish(matcher_add_quote, msg_add_quote_reply_args_missing)
        
        try:
            add_quote(event.group_id, QuoteInfoV2(
                quote_id = reply.message_id,
                author_id = reply.sender.user_id or -1,
                author_name = reply.sender.nickname or "",
                author_card = await get_group_member_cardname(event.group_id, reply.sender.user_id or -1, bot) or "",
                time_stamp = event.time,
                quote = reply_msg,
            ))
        except Exception as e:
            await mfinish(matcher_add_quote, msg_add_quote_failed, error=str(e))

        await mfinish(matcher_add_quote, msg_add_quote_success, author=reply.sender.nickname)

    else:
        # 检查 At 消息段
        # TODO
        pass


@matcher_remove_quote.handle()
async def f_remove_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除语录

    语录删除方式：
    1. `(reply) /删语录`
    2. `/删语录 语录ID`
    """
    # 判断权限
    if is_quote_manager(event.sender.user_id):
        await mfinish(matcher_remove_quote, msg_no_permission, event="删语录")
    
    # 判断 reply
    reply = event.reply
    key = arg.extract_plain_text().strip()
    if reply == None and key == "":
        await mfinish(matcher_remove_quote, msg_remove_quote_reply_args_missing)
        return
    
    # 获取语录 ID
    if reply != None:
        quote_id = get_mapping(event.group_id, reply.message_id)
    else:
        quote_id = int(key) if key.isdigit() else None
        
    if quote_id == None:
        await mfinish(matcher_remove_quote, quote_not_found)
        return
    
    # 删除语录
    result = remove_quote(event.group_id, quote_id)
    if result:
        await mfinish(matcher_remove_quote, msg_remove_quote_success)
    else:
        await mfinish(matcher_remove_quote, msg_remove_quote_failed)


@matcher_comment_quote.handle()
async def f_comment_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    评论语录

    语录评论方式：
    `(reply) /评语录 评价`
    """
    # 判断 reply
    reply = event.reply
    content = arg.extract_plain_text().strip()
    if reply == None or content == "":
        await mfinish(matcher_comment_quote, msg_comment_quote_reply_args_missing)
        return

    # 获取语录 ID
    quote_id = get_mapping(event.group_id, reply.message_id)
    if quote_id == None:
        await mfinish(matcher_comment_quote, quote_not_found)
        return
    
    # 添加评论
    result = add_comment(event.group_id, quote_id, QuoteV2Comment(
        content=content,
        author_id=event.sender.user_id or -1,
        author_name=await get_group_member_cardname(event.group_id, event.sender.user_id or -1, bot) or event.sender.nickname or "",
        time_stamp=event.time,
    ))

    if result:
        await mfinish(matcher_comment_quote, msg_comment_quote_success)
    else:
        await mfinish(matcher_comment_quote, msg_comment_quote_failed)


@matcher_del_comment.handle()
async def f_del_comment(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除评论

    语录删除评论方式：
    `/删评论 评论ID`

    除管理员外，只有评论作者可以删除自己的评论
    """
    # 获取评论 ID
    key = arg.extract_plain_text().strip()
    if key == "":
        await mfinish(matcher_del_comment, msg_remove_quote_reply_args_missing)
        return
    
    if not key.isdigit():
        await mfinish(matcher_del_comment, msg_remove_quote_id_invalid)
        return
    
    # 判断权限
    if is_quote_manager(event.sender.user_id):
        filt: Callable[[QuoteInfoV2], bool] = lambda q: any([(comment.comment_id == int(key) and comment.author_id == event.sender.user_id) for comment in q.comments])
        quotes = get_typed_quote_list(event.group_id, filter=filt)

        if len(quotes) == 0:
            await mfinish(matcher_del_comment, msg_no_permission, event="删评论")
            return

    # 删除评论
    result = remove_quote(event.group_id, int(key))
    if result:
        await mfinish(matcher_del_comment, msg_remove_quote_success)
    else:
        await mfinish(matcher_del_comment, msg_remove_quote_failed)