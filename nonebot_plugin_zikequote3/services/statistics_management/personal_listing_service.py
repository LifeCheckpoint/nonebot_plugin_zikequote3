from ...imports import *

def s_get_listing_html(group_id: str, qq_id: str, time: str):
    from ...templates import listing
    from ...templates.schema.listing import QuoteBox
    from ...services.user_management.user_service import s_get_user_current_display_name

    with service_exception("获取用户信息"):
        exists = db.dao.get_user_dao().user_exists(qq_id)
    
    if not exists:
        raise ValueError(f"用户 {qq_id} 不存在")
    
    with service_exception("获取用户群名片信息"):
        current_card = s_get_user_current_display_name(qq_id, group_id)
        used_cards = [n.name for n in db.dao.get_group_nickname_dao().get_all_group_nicknames(qq_id, group_id) if n.name != current_card]

    with service_exception("获取用户语录列表"):
        quotes_data = db.dao.get_quote_dao().get_quotes_by_group_and_author(group_id, qq_id)
        quotes_data = [QuoteBox(quote=qd.content) for qd in quotes_data]
    
    if not quotes_data:
        raise ValueError(f"用户 {qq_id} 在群组 {group_id} 中没有语录")

    with service_exception("生成语录列表 HTML"):
        return listing.render_list(
            title=f"{current_card}的语录列表",
            description=f"{time} / {len(quotes_data)} 条语录",
            addition="曾用名片 / " + "，".join(list(
                reversed([c for c in used_cards if c != current_card])
            )[:5]),
            quotes=quotes_data,
            page_title_template="第 {page_number} 页 / 共 {total_page} 页",
        )