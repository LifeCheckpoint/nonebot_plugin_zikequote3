from ...imports import *
from ..comand_definition import *
from ...utils.hitokoto import get_hitokoto


@matcher_rank.handle()
async def f_rank(event: GroupME, arg: Message = CommandArg()):
    """
    语录排行
    """
    key = arg.extract_plain_text().strip()
    num_topn = cfg.showcase.max_rank_user_num
    if key.isdigit() and 0 < int(key) <= cfg.showcase.max_rank_user_num:
        num_topn = int(key)
    
    msg_pending_num = len(get_typed_message_list(event.group_id))
    rank_info = get_quote_rank(event.group_id, top_n=num_topn)
    rank_info["stats"]["pending_quotes"] = msg_pending_num

    try:
        image_data = await full_render_html(cfg.path.templates / "rank.html", cfg.path.templates, data=rank_info, width=800, height=600)
    except Exception as e:
        print("生成语录排行失败：", e)
        await mfinish(matcher_rank, msg_rank_failed, error=str(e))

    await matcher_rank.finish(MsgSeg.image(image_data))


@matcher_quote_list.handle()
async def f_quote_list(event: GroupME, arg: Message = CommandArg()):
    """
    语录列表
    """
    key = arg.extract_plain_text().strip()
    # 默认以发送者 QQ 为关键词检索列表
    if key == "":
        key = event.sender.user_id

    # 精确匹配
    filt: Callable[[QuoteInfoV2], bool] = lambda quote: key == quote.author_name or key == quote.author_card or str(key) == str(quote.author_id)
    quotes = get_typed_quote_list(event.group_id, filter=filt)
    author_id_set = set(quote.author_id for quote in quotes)

    if not author_id_set:
        await mfinish(matcher_quote_list, msg_quote_list_not_found, key=key)

    if len(author_id_set) > 1:
        await mfinish(matcher_quote_list, msg_quote_list_ambiguous, key=key, num=len(author_id_set))

    # 重新获取用户所有格式化的语录列表
    quotes = get_typed_quote_list(event.group_id, filter=lambda quote: quote.author_id in author_id_set)
    data = get_formatted_quote_list(quotes)
    author = quotes[0].author_name if quotes else key

    time_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    author_stat = f"{len(quotes)} 条语录" + (f"（最新 {cfg.quote_list_page_limit} 页）" if len(quotes) > cfg.quote_list_num_perpage * cfg.quote_list_page_limit else "")
    addition_text = get_hitokoto()[0] or "桃李不言，下自成蹊"

    data = data | {
        "title": f"来自{author}的语录",
        "description": f"{time_text} / {author_stat}",
        "addition": addition_text,
    }

    # 生成图片
    try:
        image_data = await full_render_html(cfg.path.templates / "list.html", cfg.path.templates, data=data, width=800, height=200)
        await matcher_quote_list.send(MsgSeg.image(image_data))
    except Exception as e:
        print(f"生成语录列表失败：{e}")
        await mfinish(matcher_quote_list, msg_quote_list_generate_failed, error=str(e))

