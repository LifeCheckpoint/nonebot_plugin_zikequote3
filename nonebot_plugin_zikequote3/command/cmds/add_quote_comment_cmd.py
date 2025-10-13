from ...imports import *
from ..command_definition import *


@matcher_add_quote_comment.handle()
async def f_add_quote_comment(event: GroupME, bot: Bot, arg: Message = CommandArg()):
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
        await matcher_add_quote_comment.finish("请回复一条语录并输入评论内容哦~")

    async with event_exception_failmsg_a(matcher_add_quote_comment, "添加评论"):
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

        await matcher_add_quote_comment.send("评论添加成功~(≧▽≦)")
    
    # TODO: 添加消息映射



if matcher_add_quote_comment_no_prefix is not None:
    @matcher_add_quote_comment_no_prefix.handle()
    async def f_add_quote_comment_no_prefix(event: GroupME, bot: Bot):
        """
        静默评论语录（无前缀）

        语录评论方式：
        `(reply) 评价`
        """
        from ...services.quote_management.mapping_service import s_get_mapping_by_msgid
        from ...services.review_management.review_service import s_add_review
        
        # 判断 reply
        reply = event.reply
        content = event.get_plaintext().strip()
        if reply == None or content == "":
            return  # 不处理

        async with event_exception_failmsg_a(matcher_add_quote_comment_no_prefix, "添加评论"):
            # 获取语录 ID
            quote_id = s_get_mapping_by_msgid(str(reply.message_id))
            if quote_id is None:
                # 正常消息，不要处理
                return
            
            # 添加评论
            s_add_review(
                user_id=str(event.sender.user_id),
                quote_id=quote_id,
                content=content,
            )