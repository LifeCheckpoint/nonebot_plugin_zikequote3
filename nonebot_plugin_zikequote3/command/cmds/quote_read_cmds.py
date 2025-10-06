from ...imports import *
from ..comand_definition import *


@matcher_random_quote.handle()
async def f_random_quote(event: GroupME, bot: Bot, arg: Message = CommandArg()):
    """
    随机语录
    """
    from ...database.models.quotes import Quote
    from ...services.algorithm_management.common_algo_service import s_deduplicate_by_field_last
    from ...services.quote_management.showcase.rand_quote_service import s_search_quotes_by_author_id, s_search_quotes_by_keyword, s_rand_quote_choice_by_algorithm, s_increase_quote_appearance_count
    from ...services.user_management.user_parser_service import s_parse_at_and_str_user
    from ...services.quote_management.showcase.quote_image_service import s_get_quote_image_data
    from msgtexts.quote_read import send_quote
    
    async with exception_finish_failure(matcher_random_quote, "获取随机语录"):
        key = arg.extract_plain_text().strip()
        
        quotes_pool: List[Quote] = []

        # 尝试从昵称、QQ 等解析目标用户，如果解析到多个用户则取并集
        # 解析结果也将和语录内容查询结果合并
        # TODO: 通过参数控制解析范围

        union_users = s_parse_at_and_str_user(key, event, exact=False, empty_parse_to_self=False, multiple_at=True, parse_at_all=True)
        for u in union_users:
            with exception_report(not_raise=True):
                if u == "all":
                    break
                quotes_pool.extend(s_search_quotes_by_author_id(str(event.group_id), u))
        quotes_pool.extend(s_search_quotes_by_keyword(str(event.group_id), key))

        # 去重
        filter_key_q: Callable[[Quote], str] = lambda q: q.quote_id
        quotes_pool = s_deduplicate_by_field_last(quotes_pool, filter_key_q)

        # 通过指定算法对语录池进行随机选择
        result = s_rand_quote_choice_by_algorithm(quotes_pool, cfg[event.group_id].fetching.algorithm)

        if not result:
            await matcher_random_quote.finish("没有找到符合条件的语录哦~")

        # 发送语录
        text_msg = MsgSeg.text(send_quote(result.author_id, result.content))
        if result.image_content_uuid == None:
            await matcher_random_quote.send(text_msg)
        else:
            try:
                image_data = s_get_quote_image_data(result.image_content_uuid)
                full_msg = text_msg + MsgSeg.image(image_data)
            except FileNotFoundError:
                full_msg = text_msg + MsgSeg.text("\n（语录图片文件已丢失 O.O）")
            await matcher_random_quote.send(full_msg)
        
        # 更新语录出现次数
        s_increase_quote_appearance_count(result.quote_id)


@matcher_quote_card.handle()
async def f_quote_card(event: GroupME, arg: Message = CommandArg()):
    """
    语录卡生成
    """
    key = arg.extract_plain_text().strip()
    if key == "":
        result: QuoteInfoV2 = get_random_quote(event.group_id) # type: ignore
    else:
        filt: Callable[[QuoteInfoV2], bool] = lambda quote: key in quote.quote or key in quote.author_name or key in quote.author_card
        result: QuoteInfoV2 = get_random_quote(event.group_id, filt) # type: ignore

    if not result:
        await mfinish(matcher_quote_card, msg_quote_not_found, key=key)
    else:
        # 生成图片
        try:
            image_data = await html_img_render(cfg.path.templates / "card.html", cfg.path.templates, data=asdict(result), width=630, height=120)
            send_msg = await matcher_quote_card.send(MsgSeg.image(image_data))
            add_mapping(event.group_id, send_msg["message_id"], result.quote_id)
        except Exception as e:
            print(f"生成语录卡失败：{e}")
            await mfinish(matcher_quote_card, msg_quote_card_failed, error=str(e))


@matcher_quote_search.handle()
async def f_quote_search(event: GroupME, arg: Message = CommandArg()):
    """
    语录搜索
    """
    key = arg.extract_plain_text().strip()
    if key == "":
        await mfinish(matcher_quote_search, msg_quote_search_empty)

    # 精确匹配
    filt: Callable[[QuoteInfoV2], bool] = lambda quote: key in quote.quote
    quotes = get_typed_quote_list(event.group_id, filter=filt)

    if not quotes:
        await mfinish(matcher_quote_search, msg_quote_not_found, key=key)

    # 获取用户所有格式化的语录列表
    data = get_formatted_quote_list(quotes)

    time_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    author_stat = f"{len(quotes)} 条搜索结果" + f"（最新 {cfg.quote_list_page_limit} 页）" if len(quotes) > cfg.quote_list_num_perpage * cfg.quote_list_page_limit else ""
    addition_text = get_hitokoto()[0] or "桃李不言，下自成蹊"

    data = data | {
        "title": f"包含{key}的语录",
        "description": f"{time_text} / {author_stat}",
        "addition": addition_text,
    }

    # 生成图片
    try:
        image_data = await html_img_render(cfg.path.templates / "list.html", cfg.path.templates, data=data, width=800, height=200)
        await matcher_quote_search.send(MsgSeg.image(image_data))
    except Exception as e:
        print(f"生成语录搜索列表失败：{e}")
        await mfinish(matcher_quote_search, msg_quote_list_generate_failed, error=str(e))
