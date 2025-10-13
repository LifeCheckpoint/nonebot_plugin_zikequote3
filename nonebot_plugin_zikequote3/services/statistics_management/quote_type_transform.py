from ...imports import *
from ...database.models.quotes import Quote
from ...templates.schema.listing import QuoteBox

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
        quote_boxes: List[QuoteBox] = []
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
            quote_boxes.append(QuoteBox(
                quote_id=qd.quote_id if show_id else None,
                quote_text=qd.content,
                quote_image=image_uri,
                quote_author= author_name,
                quote_comment=f"{review.content}  ——{review_author}" if review else None,
            ))

        return quote_boxes