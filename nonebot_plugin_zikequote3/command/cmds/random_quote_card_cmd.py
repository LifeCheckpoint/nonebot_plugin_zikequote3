from ...imports import *
from ..command_definition import *


@matcher_random_quote_card.handle()
async def f_quote_card(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    随机语录卡，基本与随机语录逻辑一致
    """
    from ...services.user_management.personal_info_service import s_update_personal_info_api
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.rand_quote_service import s_get_random_quote, s_increase_quote_appearance_count, s_get_quote_card_html

    key = arg.extract_plain_text().strip()
    send_msg = None
    async with event_exception_failmsg_a(matcher_random_quote_card, "获取语录卡"):
        q_result = s_get_random_quote(key, event)

        if q_result is None:
            await matcher_random_quote_card.finish("没有找到符合条件的语录哦~")

        # 发起一个异步要求更新用户信息
        asyncio.create_task(s_update_personal_info_api(str(event.group_id), q_result.author_id, bot))

        # 发送语录
        quote_card_html = s_get_quote_card_html(str(event.group_id), q_result)
        quote_card = await html_img_render(quote_card_html, width=800, height=120)
        send_msg = await matcher_random_quote_card.send(MsgSeg.image(quote_card))
        
    # 更新语录出现次数
    with event_exception(operation="ignore"):
        s_increase_quote_appearance_count(q_result.quote_id)

    # 检查用户-群映射存在性
    with event_exception(operation="ignore"):
        from ...services.user_management.group_relationship_service import s_ensure_user_group_mapping
        await s_ensure_user_group_mapping(str(event.group_id), q_result.author_id, bot)
    
    # 添加消息映射
    if send_msg is not None:
        with event_exception(operation="ignore"):
            s_create_mapping_from_msgid_to_quoteid(str(send_msg["message_id"]), q_result.quote_id)