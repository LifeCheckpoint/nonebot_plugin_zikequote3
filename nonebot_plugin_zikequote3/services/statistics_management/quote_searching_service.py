from ...imports import *


def s_get_searching_quote_html(
    group_id: str,
    pattern: str = "",
    qq_id: Optional[str] = None,
    search_with_image: bool = True,
    max_result: Optional[int] = None,
    use_regex: bool = False,
    time: str = "",
):
    from ...services.quote_management.showcase.basic_quote_service import s_get_quote_by_group
    from ...services.statistics_management.quote_type_transform import s_transform_quotedata_to_quotebox
    from ...templates import listing
    from ...utils.hitokoto import get_hitokoto
    import re

    with service_exception("语录搜索筛选"):
        quotes = s_get_quote_by_group(group_id)
        quotes = [q for q in quotes if q.content]

        if use_regex:
            quotes = [q for q in quotes if q.content and re.search(pattern, q.content)]
        else:
            quotes = [q for q in quotes if q.content and pattern in q.content]

        if qq_id:
            quotes = [q for q in quotes if q.author_id == qq_id]

        if not search_with_image:
            quotes = [q for q in quotes if not q.image_content_uuid]

        total_found = len(quotes)
        if max_result:
            quotes = quotes[:max_result]

        quote_boxes = s_transform_quotedata_to_quotebox(group_id, quotes, show_author=True)

    with service_exception("拼接说明文字"):
        # 标题
        title_text = f"有关{pattern}的语录搜索结果"
        
        # 描述
        desc_text = " | ".join([
            f"{time}",
            f"{'正则' if use_regex else '普通'}搜索模式",
            f"筛选 QQ: {qq_id}" if qq_id else "不筛选 QQ",
            f"{'' if search_with_image else '不'} 包含图片",
            f"共 {total_found} 条 (显示 {len(quote_boxes)} 条)",
        ])

        # 名人名言
        hitokoto_content, hitokoto_author = get_hitokoto()
        if hitokoto_content and hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」 ——{hitokoto_author}"
        elif hitokoto_content and not hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」"
        else:
            hitokoto_text = None

    with service_exception("生成语录搜索结果 HTML"):
        return listing.render_list(
            title=title_text,
            desc=desc_text,
            addition=hitokoto_text,
            quotes=quote_boxes,
        )