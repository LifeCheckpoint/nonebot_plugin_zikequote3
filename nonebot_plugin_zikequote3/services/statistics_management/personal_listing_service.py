from ...imports import *

def s_get_listing_html(
    group_id: str,
    qq_id: str,
    time: str,
    from_page: int | None = None,
    to_page: int | None = None,
) -> str:
    """
    获取用户语录列表 HTML

    Args:
        :param group_id: 群组 ID
        :param qq_id: 用户 QQ 号
        :param time: 当前时间字符串
        :param quote_range: 语录范围，None 表示所有语录，int 表示从第 N 到 N + 最大显示条数，(start, end) 表示从 start 到 end 的语录（包含 start，不包含 end）
    """
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
        # 裁剪语录范围
        max_showcase_number = cfg[int(group_id)].showcase.max_quotes_in_list
        current_quotes_length = len(quotes_data)

        if from_page is None and to_page is None:
            if current_quotes_length > max_showcase_number:
                start = current_quotes_length - max_showcase_number
                end = current_quotes_length - 1
                quotes_data = quotes_data[-max_showcase_number:]
            else:
                start = 0
                end = current_quotes_length - 1
                quotes_data = quotes_data

        elif from_page is not None and to_page is None:
            start = max(0, from_page)
            end = min(current_quotes_length, start + max_showcase_number)
            quotes_data = quotes_data[start:end]

        elif from_page is not None and to_page is not None:
            start = max(0, from_page)
            end = min(current_quotes_length, to_page)
            quotes_data = quotes_data[start:end]

        else:
            raise ValueError("语录范围参数不正确")
        
        # 将语录转换为模板参数
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
                # quote_author=current_card, # 作者统一为当前用户，没必要显示
                quote_comment=f"{review.content}  ——{review_author}" if review else None,
            ))

    with service_exception("拼接装饰性文字"):
        # 标题
        title_text = f"{current_card}的语录列表"

        # 描述
        desc_text = f"{time} / {current_quotes_length} 条语录 (第 {start} - {end} 条)"

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
