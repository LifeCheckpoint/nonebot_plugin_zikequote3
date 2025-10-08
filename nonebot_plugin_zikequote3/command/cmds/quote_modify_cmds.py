from ...imports import *
from ..command_definition import *


@matcher_add_quote.handle()
async def f_add_quote(event: GroupME, bot: Bot):
    """
    添加语录
    """
    from ...services.quote_management.addtion.add_quote_service import s_add_quote
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.quote_image_service import s_get_image_data_from_file_or_url, s_image_info_register
    from ...msgtexts.quote_modify import add_quote_success
    
    reply = event.reply
    if reply == None:
        await matcher_add_quote.finish("您还没有回复想要加的语录呢(^///^)")
    
    if reply.sender.user_id == bot.self_id:
        await matcher_add_quote.finish("呀呀呀，怎么在添加我的语录呢？(>_<)")    
    
    if reply.message.only("image"):
        # TODO: 修改数据模型以支持纯图片语录
        await matcher_add_quote.finish("暂不支持纯图片语录哦~")

    if reply.message.extract_plain_text().strip() == "":
        await matcher_add_quote.finish("语录内容不能为空哦~")

    # 检查图片数据存在性
    img = None
    if reply.message.count("image") >= 1:
        async with event_exception_failmsg_a(matcher_add_quote, "获取将要添加的图片数据"):
            picseg_data = reply.message.get("image")[0].data
            img_url_or_file = picseg_data["url"] if "url" in picseg_data else picseg_data["file"]
            img = await s_get_image_data_from_file_or_url(img_url_or_file)

    async with event_exception_failmsg_a(matcher_add_quote, "添加语录"):
        if img is not None:
            uuid = await s_image_info_register(img, img_url_or_file)
        else:
            uuid = None
        
        qid = s_add_quote(
            group_id=str(event.group_id),
            author_id=str(reply.sender.user_id),
            content=reply.message.extract_plain_text().strip(),
            image_uuid=uuid if img is not None else None,
        )
    
    await matcher_add_quote.send(add_quote_success())
    
    # 添加消息映射
    with event_exception(operation="ignore"):
        s_create_mapping_from_msgid_to_quoteid(str(reply.message_id), qid)


@matcher_remove_quote.handle()
async def f_remove_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除语录
    """
    # # 判断权限
    # if is_quote_manager(event.sender.user_id):
    #     await mfinish(matcher_remove_quote, msg_no_permission, event="删语录")
    
    # # 判断 reply
    # reply = event.reply
    # key = arg.extract_plain_text().strip()
    # if reply == None and key == "":
    #     await mfinish(matcher_remove_quote, msg_remove_quote_reply_args_missing)
    #     return
    
    # # 获取语录 ID
    # if reply != None:
    #     quote_id = get_mapping(event.group_id, reply.message_id)
    # else:
    #     quote_id = int(key) if key.isdigit() else None
        
    # if quote_id == None:
    #     await mfinish(matcher_remove_quote, quote_not_found)
    #     return
    
    # # 删除语录
    # result = remove_quote(event.group_id, quote_id)
    # if result:
    #     await mfinish(matcher_remove_quote, msg_remove_quote_success)
    # else:
    #     await mfinish(matcher_remove_quote, msg_remove_quote_failed)


@matcher_comment_quote.handle()
async def f_comment_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    评论语录

    语录评论方式：
    `(reply) /评语录 评价`
    """
    from ...services.quote_management.mapping_service import s_get_mapping_by_msgid
    from ...services.review_management.review_service import s_add_review
    
    # 判断 reply
    reply = event.reply
    content = arg.extract_plain_text().strip()
    if reply == None or content == "":
        await matcher_comment_quote.finish("请回复一条语录并输入评论内容哦~")

    async with event_exception_failmsg_a(matcher_comment_quote, "添加评论"):
        # 获取语录 ID
        quote_id = s_get_mapping_by_msgid(str(reply.message_id))
        if quote_id is None:
            raise ValueError("未找到对应语录，无法评论呢~")
        
        # 添加评论
        s_add_review(
            user_id=str(event.sender.user_id),
            quote_id=quote_id,
            content=content,
        )

        await matcher_comment_quote.send("评论添加成功~(≧▽≦)")
    
    # TODO: 添加消息映射


@matcher_del_comment.handle()
async def f_del_comment(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    删除评论

    语录删除评论方式：
    `/删评论 评论ID`

    除管理员外，只有评论作者可以删除自己的评论
    """
    # # 获取评论 ID
    # key = arg.extract_plain_text().strip()
    # if key == "":
    #     await mfinish(matcher_del_comment, msg_remove_quote_reply_args_missing)
    #     return
    
    # if not key.isdigit():
    #     await mfinish(matcher_del_comment, msg_remove_quote_id_invalid)
    #     return
    
    # # 判断权限
    # if is_quote_manager(event.sender.user_id):
    #     filt: Callable[[QuoteInfoV2], bool] = lambda q: any([(comment.comment_id == int(key) and comment.author_id == event.sender.user_id) for comment in q.comments])
    #     quotes = get_typed_quote_list(event.group_id, filter=filt)

    #     if len(quotes) == 0:
    #         await mfinish(matcher_del_comment, msg_no_permission, event="删评论")
    #         return

    # # 删除评论
    # result = remove_quote(event.group_id, int(key))
    # if result:
    #     await mfinish(matcher_del_comment, msg_remove_quote_success)
    # else:
    #     await mfinish(matcher_del_comment, msg_remove_quote_failed)