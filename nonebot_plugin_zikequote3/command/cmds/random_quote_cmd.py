from ...imports import *
from ..command_definition import *


@matcher_random_quote.handle()
async def f_random_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    随机语录
    """
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.quote_image_service import s_get_quote_image_data
    from ...services.quote_management.showcase.rand_quote_service import s_get_random_quote, s_increase_quote_appearance_count
    from ...services.user_management.group_relationship_service import s_ensure_user_group_mapping
    from ...services.user_management.personal_info_service import s_update_personal_info_api
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...msgtexts.quote_read import send_quote
    
    key = arg.extract_plain_text().strip()
    send_msg = None
    async with event_exception_failmsg_a(matcher_random_quote, "获取随机语录"):
        q_result = s_get_random_quote(key, event)

        if q_result is None:
            await matcher_random_quote.finish("没有找到符合条件的语录哦~")

        # 发起一个异步要求更新用户信息
        asyncio.create_task(s_update_personal_info_api(str(event.group_id), q_result.author_id, bot))

        # 获取语录作者当前昵称
        author_card = s_get_user_current_display_name(q_result.author_id, str(event.group_id))

        with event_exception(operation="ignore"):
            if q_result.content is not None:
                text_msg = MsgSeg.text(send_quote(author_card, q_result.content))
            else:
                text_msg = None
            
            if q_result.image_content_uuid == None and text_msg is not None:
                send_msg = await matcher_random_quote.send(text_msg)
            elif q_result.image_content_uuid is not None and text_msg is not None:
                try:
                    image_data = s_get_quote_image_data(q_result.image_content_uuid)
                    full_msg = text_msg + MsgSeg.image(image_data)
                except FileNotFoundError:
                    full_msg = text_msg + MsgSeg.text("\n（语录图片文件已丢失 O.O）")
                send_msg = await matcher_random_quote.send(full_msg)
            elif q_result.image_content_uuid is not None and text_msg is None:
                try:
                    image_data = s_get_quote_image_data(q_result.image_content_uuid)
                    send_msg = await matcher_random_quote.send(MsgSeg.image(image_data))
                except FileNotFoundError:
                    send_msg = await matcher_random_quote.send("（语录图片文件已丢失 O.O）")
            else:
                raise ValueError("语录内容和图片均为空")
        
    # 更新语录出现次数
    with event_exception(operation="ignore"):
        s_increase_quote_appearance_count(q_result.quote_id)
    
    # 检查用户-群映射存在性
    with event_exception(operation="ignore"):
        await s_ensure_user_group_mapping(str(event.group_id), q_result.author_id, bot)

    # 添加消息映射
    if send_msg is not None:
        with event_exception(operation="ignore"):
            s_create_mapping_from_msgid_to_quoteid(str(send_msg["message_id"]), q_result.quote_id)