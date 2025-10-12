from ...imports import *

def s_get_listing_html(group_id: str, qq_id: str, time: str):
    from ...services.quote_management.showcase.quote_image_service import to_data_uri
    from ...services.review_management.review_service import AUTHOR_AI, s_get_reviews_by_quote_id
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...templates import listing
    from ...templates.schema.listing import QuoteBox
    from ...utils.hitokoto import get_hitokoto

    with service_exception("获取用户信息"):
        exists = db.dao.get_user_dao().user_exists(qq_id)
        if not exists:
            raise ValueError(f"用户 {qq_id} 不存在")
        current_card = s_get_user_current_display_name(qq_id, group_id)

    with service_exception("获取用户语录列表"):
        quotes_data = db.dao.get_quote_dao().get_quotes_by_group_and_author(group_id, qq_id)
    if not quotes_data:
        raise ValueError(f"用户 {qq_id} 在群组 {group_id} 中没有语录")
    
    with service_exception("获取并转换语录信息"):
        max_showcase_number = cfg[int(group_id)].showcase.max_quotes_in_list
        current_quotes_length = len(quotes_data)
        if current_quotes_length > max_showcase_number:
            quotes_data = quotes_data[-max_showcase_number:]
        
        quotes_params: List[QuoteBox] = []
        for qd in quotes_data:
            # 首条评论
            reviews = s_get_reviews_by_quote_id(qd.quote_id)
            review = next((r for r in reviews if r.author_id != AUTHOR_AI), None)
            review_author = s_get_user_current_display_name(review.author_id, group_id) if review else None

            # 图片
            image_uri = None
            if qd.image_content_uuid is not None:
                with service_exception(f"语录列表获取语录 {qd.quote_id} 图片", raise_again=False):
                    img_bytes = qimg_store.get_path(qd.image_content_uuid).read_bytes()
                    image_uri = to_data_uri(img_bytes)
            
            # 加入列表
            quotes_params.append(QuoteBox(
                quote_id=qd.quote_id,
                quote_text=qd.content,
                quote_image=image_uri,
                quote_author=current_card,
                quote_comment=f"{review}  ——{review_author}" if review else None,
            ))

    with service_exception("拼接装饰性文字"):
        # 标题
        title_text = f"{current_card}的语录列表"

        # 描述
        if current_quotes_length > max_showcase_number:
            desc_text = f"{time} / {len(quotes_data)} 条语录 (最新 {max_showcase_number} 条)"
        else:
            desc_text = f"{time} / {len(quotes_data)} 条语录"

        # 名人名言（真的
        hitokoto_content, hitokoto_author = get_hitokoto()
        if hitokoto_content and hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」 ——{hitokoto_author}"
        elif hitokoto_content and not hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」"
        else:
            hitokoto_text = None

    with service_exception("生成语录列表 HTML"):
        return listing.render_list(
            title=title_text,
            desc=desc_text,
            addition=hitokoto_text,
            quotes=quotes_params,
        )
