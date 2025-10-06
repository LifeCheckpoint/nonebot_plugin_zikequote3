from ....imports import *
from ....database.models.quotes import Quote

def s_increase_quote_appearance_count(quote_id: str):
    """
    增加语录出现次数统计
    """
    with exception_report("增加语录展示次数"):
        db.dao.get_quote_dao().increment_show_time(quote_id)

def s_search_quotes_by_keyword(group_id: str, keyword: str, limit: Optional[int] = None):
    """
    通过关键词搜索语录
    """
    with exception_report("通过关键词搜索语录"):
        quotes = db.dao.get_quote_dao().get_quotes_by_group(group_id, limit=limit)
        return [q for q in quotes if keyword in q.content]

def s_search_quotes_by_author_id(group_id: str, author_id: str, limit: Optional[int] = None):
    """
    通过作者 QQ 搜索语录
    """
    with exception_report("通过作者搜索语录"):
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

    with exception_report("解析算法命令参数"):
        schema = parse_command(rsap, algorithm_cmd)

    with exception_report("语录随机选择计算"):
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