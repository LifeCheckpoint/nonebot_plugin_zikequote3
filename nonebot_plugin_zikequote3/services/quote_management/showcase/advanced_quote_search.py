from ....imports import *
import re


def s_search_quote_by_regex(group_id: str, pattern: str):
    from ....services.quote_management.showcase.basic_quote_service import s_get_quote_by_group

    with service_exception("正则表达式筛选语录"):
        quotes = s_get_quote_by_group(group_id)
        matched_quotes = [
            q for q in quotes
            if q.content is not None and re.search(pattern, q.content)
        ]
        return matched_quotes
