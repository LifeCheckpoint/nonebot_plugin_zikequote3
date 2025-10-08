from __future__ import annotations

from ....imports import *
from ....database.models.quotes import Quote

def s_increase_quote_appearance_count(quote_id: str):
    """
    增加语录出现次数统计
    """
    with service_exception("增加语录展示次数"):
        db.dao.get_quote_dao().increment_show_time(quote_id)


def s_search_quotes_by_keyword(group_id: str, keyword: str, limit: Optional[int] = None):
    """
    通过关键词搜索语录
    """
    with service_exception("通过关键词搜索语录"):
        quotes = db.dao.get_quote_dao().get_quotes_by_group(group_id, limit=limit)
        return [q for q in quotes if keyword in q.content]


def s_search_quotes_by_author_id(group_id: str, author_id: str, limit: Optional[int] = None):
    """
    通过作者 QQ 搜索语录
    """
    with service_exception("通过作者搜索语录"):
        quotes = db.dao.get_quote_dao().get_quotes_by_group_and_author(group_id, author_id, limit=limit)
        return quotes


def s_rand_quote_choice_by_algorithm(quotes: List[Quote], algorithm_cmd: str = "IFW --lambda 1.0") -> Quote | None:
    """
    通过指定算法，从语录池中抽选一个语录
    """
    from .rand_quote_algo_function import s_ifw, s_logifw
    from ...algorithm_management.showcase_algo_parse_service import (
        rand_showcase_algo_parser as rsap,
        AlgoInverseFrequencyWeight as IFW,
        AlgoLogInverseFrequencyWeight as LogIFW,
    )
    from ....utils.click_cmd_parser import parse_command

    if not quotes:
        return None

    if len(quotes) == 1:
        return quotes[0]

    with service_exception("解析算法命令参数"):
        schema = parse_command(rsap, algorithm_cmd)

    with service_exception("语录随机选择计算"):
        if isinstance(schema, IFW):
            id_weights = s_ifw(quotes, schema)
        elif isinstance(schema, LogIFW):
            id_weights = s_logifw(quotes, schema)
        else:
            raise ValueError(f"不支持的算法参数类型: {type(schema)}")
    
    chosen_quote_id = random.choices(
        list(id_weights.keys()),
        weights=list(id_weights.values()),
        k=1
    )[0]

    return next((q for q in quotes if q.quote_id == chosen_quote_id), None)


def s_get_random_quote(key: str, event: GroupME, filter_: Optional[Callable[[Quote], bool]] = None) -> Quote | None:
    """
    获取群内随机语录，并处理自增等逻辑
    """
    from ....services.algorithm_management.common_algo_service import s_deduplicate_by_field_last
    from ....services.quote_management.showcase.basic_quote_service import s_get_quote_by_group
    from ....services.user_management.user_parser_service import s_parse_at_and_str_user

    quotes_pool: List[Quote] = []

    # 尝试从昵称、QQ 等解析目标用户，如果解析到多个用户则取并集
    # 解析结果也将和语录内容查询结果合并
    # TODO: 通过参数控制解析范围

    with service_exception("解析用户参数"):
        union_users = s_parse_at_and_str_user(key, event, exact=False, empty_parse_to_self=False, multiple_at=True, parse_at_all=True)
        for u in union_users:
            with service_exception(raise_again=False):
                if u == "all":
                    # @全体，视为获取群内所有语录
                    quotes_pool = s_get_quote_by_group(str(event.group_id))
                    break
                quotes_pool.extend(s_search_quotes_by_author_id(str(event.group_id), u))
        quotes_pool.extend(s_search_quotes_by_keyword(str(event.group_id), key))

    with service_exception("语录去重过滤"):
        filter_key_q: Callable[[Quote], str] = lambda q: q.quote_id
        quotes_pool = s_deduplicate_by_field_last(quotes_pool, filter_key_q)

        if filter_ is not None:
            quotes_pool = [q for q in quotes_pool if filter_(q)]

    with service_exception("通过算法随机选择语录"):
        result = s_rand_quote_choice_by_algorithm(quotes_pool, cfg[event.group_id].fetching.algorithm)

    return result


def s_get_quote_card_html(group_id: str, quote: Quote) -> str:
    """
    获取渲染好的语录卡 HTML 图片
    """
    from ....services.quote_management.showcase.quote_image_service import s_get_quote_image_data, to_data_uri
    from ....services.user_management.user_service import s_get_user_current_display_name
    from ....services.review_management.review_service import AUTHOR_AI
    from ....templates import card
    from ....templates.schema.card import Comment
    
    with service_exception("获取语录作者信息"):
        author = s_get_user_current_display_name(quote.author_id, group_id)

    with service_exception("获取语录相关评论"):
        reviews = db.dao.get_review_dao().get_reviews_by_quote(quote.quote_id)
    
    with service_exception("转换评论数据"):
        comments = []
        for r in reviews:
            
            comment_author = s_get_user_current_display_name(r.author_id, group_id)
            if comment_author == AUTHOR_AI:
                comment_author = "AI"
            
            comments.append(Comment(
                comment_id=r.review_id,
                author_name=comment_author,
                content=r.content,
            ))

    image_data = None
    if quote.image_content_uuid is not None:
        with service_exception("获取语录图片"):
            image_data = to_data_uri(s_get_quote_image_data(quote.image_content_uuid))
    
    with service_exception("渲染语录卡"):
        return card.render_card(
            quote_id=quote.quote_id,
            quote=quote.content,
            image_uri=image_data,
            author_name=author,
            comments=comments
        )
    