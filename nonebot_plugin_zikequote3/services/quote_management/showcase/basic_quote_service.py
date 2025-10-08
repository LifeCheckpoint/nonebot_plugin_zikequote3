from ....imports import *

def s_get_quote_by_group(group_id: str):
    with service_exception("获取群组语录"):
        quotes = db.dao.get_quote_dao().get_quotes_by_group(group_id)
        return quotes
