from ...imports import *
from ..command_definition import *


@matcher_random_quote.handle()
async def f_random_quote(event: GroupME, arg: Message = CommandArg()):
    """
    随机语录
    """
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.rand_quote_service import s_get_random_quote, s_increase_quote_appearance_count
    from ...services.quote_management.showcase.quote_image_service import s_get_quote_image_data
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...msgtexts.quote_read import send_quote
    
    key = arg.extract_plain_text().strip()
    send_msg = None
    async with event_exception_failmsg_a(matcher_random_quote, "获取随机语录"):
        q_result = s_get_random_quote(key, event)

        if q_result is None:
            await matcher_random_quote.finish("没有找到符合条件的语录哦~")

        # 获取语录作者当前昵称
        author_card = s_get_user_current_display_name(q_result.author_id, str(event.group_id))

        with event_exception(operation="ignore"):
            if q_result.content is not None:
                text_msg = MsgSeg.text(send_quote(author_card, q_result.content))
            else:
                text_msg = None
            
            if q_result.image_content_uuid == None and text_msg is not None:
                await matcher_random_quote.send(text_msg)
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

    # 添加消息映射
    if send_msg is not None:
        with event_exception(operation="ignore"):
            s_create_mapping_from_msgid_to_quoteid(str(send_msg["message_id"]), q_result.quote_id)


@matcher_quote_card.handle()
async def f_quote_card(event: GroupME, arg: Message = CommandArg()):
    """
    随机语录卡，基本与随机语录逻辑一致
    """
    from ...services.quote_management.mapping_service import s_create_mapping_from_msgid_to_quoteid
    from ...services.quote_management.showcase.rand_quote_service import s_get_random_quote, s_increase_quote_appearance_count, s_get_quote_card_html

    key = arg.extract_plain_text().strip()
    send_msg = None
    async with event_exception_failmsg_a(matcher_quote_card, "获取语录卡"):
        q_result = s_get_random_quote(key, event)

        if q_result is None:
            await matcher_quote_card.finish("没有找到符合条件的语录哦~")

        # 发送语录
        quote_card_html = s_get_quote_card_html(str(event.group_id), q_result)
        quote_card = await html_img_render(quote_card_html, module_render_image_root, width=800, height=120)
        send_msg = await matcher_quote_card.send(MsgSeg.image(quote_card))
        
    # 更新语录出现次数
    with event_exception(operation="ignore"):
        s_increase_quote_appearance_count(q_result.quote_id)
    
    # 添加消息映射
    if send_msg is not None:
        with event_exception(operation="ignore"):
            s_create_mapping_from_msgid_to_quoteid(str(send_msg["message_id"]), q_result.quote_id)


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


@matcher_quote_search.handle()
async def f_quote_search(event: GroupME, arg: Message = CommandArg()):
    """
    语录搜索
    """
    # key = arg.extract_plain_text().strip()
    # if key == "":
    #     await mfinish(matcher_quote_search, msg_quote_search_empty)

    # # 精确匹配
    # filt: Callable[[QuoteInfoV2], bool] = lambda quote: key in quote.quote
    # quotes = get_typed_quote_list(event.group_id, filter=filt)

    # if not quotes:
    #     await mfinish(matcher_quote_search, msg_quote_not_found, key=key)

    # # 获取用户所有格式化的语录列表
    # data = get_formatted_quote_list(quotes)

    # time_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    # author_stat = f"{len(quotes)} 条搜索结果" + f"（最新 {cfg.quote_list_page_limit} 页）" if len(quotes) > cfg.quote_list_num_perpage * cfg.quote_list_page_limit else ""
    # addition_text = get_hitokoto()[0] or "桃李不言，下自成蹊"

    # data = data | {
    #     "title": f"包含{key}的语录",
    #     "description": f"{time_text} / {author_stat}",
    #     "addition": addition_text,
    # }

    # # 生成图片
    # try:
    #     image_data = await html_img_render(cfg.path.templates / "list.html", cfg.path.templates, data=data, width=800, height=200)
    #     await matcher_quote_search.send(MsgSeg.image(image_data))
    # except Exception as e:
    #     print(f"生成语录搜索列表失败：{e}")
    #     await mfinish(matcher_quote_search, msg_quote_list_generate_failed, error=str(e))
