from ...imports import *
from ..command_definition import *


@matcher_quote_image_fetching.handle()
async def f_quote_image_fetching(event: GroupME, arg: Message = CommandArg()):
    """
    随机语录图，基本与随机语录逻辑一致
    """
    from ...database.models.quotes import Quote
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.rand_quote_service import s_get_random_quote, s_increase_quote_appearance_count
    from ...services.quote_management.showcase.quote_image_service import s_get_quote_image_data

    key = arg.extract_plain_text().strip()
    async with event_exception_failmsg_a(matcher_quote_image_fetching, "获取语录图片"):
        image_filter: Callable[[Quote], bool] = lambda q: q.image_content_uuid is not None
        q_result = s_get_random_quote(key, event, filter_=image_filter)

        if q_result is None or q_result.image_content_uuid is None:
            await matcher_quote_image_fetching.finish("没有找到符合条件的语录哦~")

        # 发送语录图片
        await matcher_quote_image_fetching.send(MsgSeg.image(s_get_quote_image_data(q_result.image_content_uuid)))
        
    # 更新语录出现次数
    with event_exception(operation="ignore"):
        s_increase_quote_appearance_count(q_result.quote_id)

    # 添加消息映射
    with event_exception(operation="ignore"):
        s_create_mapping_from_msgid_to_quoteid(str(event.message_id), q_result.quote_id)