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
        :param from_page: 起始语录索引（包含），1-based
        :param to_page: 结束语录索引（包含），1-based
    """
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...templates.schema.listing import render_list, TemplateQuoteListData
    from ...services.statistics_management.quote_searching_service import s_transform_quotedata_to_quotebox
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
                real_page_from = current_quotes_length - max_showcase_number
                real_page_to = current_quotes_length - 1
                quotes_data = quotes_data[-max_showcase_number: ]
            else:
                real_page_from = 0
                real_page_to = current_quotes_length - 1
                quotes_data = quotes_data

        elif from_page is not None and to_page is None:
            real_page_from = max(0, from_page - 1)
            real_page_to = min(current_quotes_length - 1, real_page_from + max_showcase_number)
            quotes_data = quotes_data[real_page_from: real_page_to + 1]

        elif from_page is not None and to_page is not None:
            real_page_from = max(0, from_page - 1)
            real_page_to = min(current_quotes_length - 1, to_page - 1)
            quotes_data = quotes_data[real_page_from: real_page_to + 1]

        else:
            raise ValueError("语录范围参数不正确")
        
        quotes_boxes = s_transform_quotedata_to_quotebox(group_id, quotes_data)

    with service_exception("拼接说明文字"):
        # 标题
        title_text = f"{current_card}的语录列表"

        # 描述
        desc_text = f"{time} / {current_quotes_length} 条语录 (第 {real_page_from + 1} - {real_page_to + 1} 条)"

        # 名人名言（真的
        hitokoto_content, hitokoto_author = get_hitokoto()
        if hitokoto_content and hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」 ——{hitokoto_author}"
        elif hitokoto_content and not hitokoto_author:
            hitokoto_text = f"「{hitokoto_content}」"
        else:
            hitokoto_text = None

    with service_exception("生成语录列表 HTML"):
        return render_list(
            TemplateQuoteListData(
                title=title_text,
                desc=desc_text,
                addition=hitokoto_text,
                quotes=quotes_boxes,
            )
        )
