from ...imports import *
from ...database.models.quotes import Quote
from ...templates.schema.listing import TemplateQuoteBoxData, TemplateQuoteListData, render_list

def s_transform_quotedata_to_quotebox(
    group_id: str,
    quotes_data: List[Quote],
    show_id: bool = True,
    show_image: bool = True,
    show_author: bool = False,
    show_comment: bool = True,
):
    from ...services.review_management.review_service import AUTHOR_AI, s_get_reviews_by_quote_id
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...services.quote_management.showcase.quote_image_service import to_data_uri
    
    with service_exception("语录信息格式转换"):
        # 将语录转换为模板参数
        quote_boxes: List[TemplateQuoteBoxData] = []
        for qd in quotes_data:
            # 作者
            author_name = None
            if show_author:
                author_name = s_get_user_current_display_name(qd.author_id, group_id)

            # 首条评论
            if show_comment:
                reviews = s_get_reviews_by_quote_id(qd.quote_id)
                review = next((r for r in reviews if r.author_id != AUTHOR_AI), None)
                review_author = s_get_user_current_display_name(review.author_id, group_id) if review else None
            else:
                review = None
                review_author = None

            # 图片
            image_uri = None
            if qd.image_content_uuid is not None and show_image:
                with service_exception(f"语录列表获取语录 {qd.quote_id} 图片", raise_again=False):
                    img_bytes = qimg_store.get_path(qd.image_content_uuid).read_bytes()
                    image_uri = to_data_uri(img_bytes)
            
            # 加入列表
            quote_boxes.append(TemplateQuoteBoxData(
                quote_id=qd.quote_id if show_id else None,
                quote_text=qd.content,
                quote_image=image_uri,
                quote_author= author_name,
                quote_comment=f"{review.content}  ——{review_author}" if review else None,
            ))

        return quote_boxes


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
        return render_list(
            TemplateQuoteListData(
                title=title_text,
                desc=desc_text,
                addition=hitokoto_text,
                quotes=quote_boxes,
            )
        )