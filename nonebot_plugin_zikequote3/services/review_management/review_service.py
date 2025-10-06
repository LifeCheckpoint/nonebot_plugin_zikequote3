from ...imports import *

AUTHOR_AI = "-1"

def s_add_review(user_id: str, quote_id: str, content: str):
    """
    为语录添加评论
    """
    with exception_report("查找语录"):
        quote = db.dao.get_quote_dao().get_quote_by_id(quote_id)
        if quote is None:
            raise ValueError(f"语录 {quote_id} 不存在")
    
    with exception_report("添加评论"):
        db.dao.get_review_dao().create_review(
            review_id=str(random.randint(10 ** 10, 10 ** 11 - 1)),
            author_id=user_id,
            quote_id=quote_id,
            content=content.strip(),
        )
    