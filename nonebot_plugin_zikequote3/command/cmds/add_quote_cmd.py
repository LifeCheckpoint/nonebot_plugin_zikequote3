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
    
    reply = event.reply
    if reply == None:
        await matcher_add_quote.finish("您还没有回复想要加的语录呢(^///^)")
    
    if reply.sender.user_id == bot.self_id:
        await matcher_add_quote.finish("呀呀呀，怎么在添加我的语录呢？(>_<)")    
    
    if reply.message.extract_plain_text().strip() == "" and reply.message.count("image") == 0:
        await matcher_add_quote.finish("语录内容不能为空哦~")

    # 检查图片数据存在性
    img = None
    if reply.message.count("image") >= 1:
        async with event_exception_failmsg_a(matcher_add_quote, "获取将要添加的图片数据"):
            picseg_data = reply.message.get("image")[0].data
            img_url_or_file = picseg_data["url"] if "url" in picseg_data else picseg_data["file"]
            img = await s_get_image_data_from_file_or_url(img_url_or_file)

    # 检查语录内容存在性
    content_text = reply.message.extract_plain_text().strip() if not reply.message.only("image") else None

    async with event_exception_failmsg_a(matcher_add_quote, "添加语录"):
        if img is not None:
            uuid = await s_image_info_register(img, img_url_or_file)
        else:
            uuid = None
        
        qid = s_add_quote(
            group_id=str(event.group_id),
            author_id=str(reply.sender.user_id),
            content=content_text,
            image_uuid=uuid if img is not None else None,
        )
    
    await matcher_add_quote.send("语录添加成功~(≧▽≦)")
    
    # 添加消息映射
    with event_exception(operation="ignore"):
        s_create_mapping_from_msgid_to_quoteid(str(reply.message_id), qid)