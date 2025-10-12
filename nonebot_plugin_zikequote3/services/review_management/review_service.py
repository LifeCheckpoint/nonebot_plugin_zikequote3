from ...imports import *
from ...database.models.reviews import Review

AUTHOR_AI = "-1"

def s_add_review(user_id: str, quote_id: str, content: str):
    """
    为语录添加评论
    """
    with service_exception("查找语录"):
        quote = db.dao.get_quote_dao().get_quote_by_id(quote_id)
        if quote is None:
            raise ValueError(f"语录 {quote_id} 不存在")
    
    with service_exception("添加评论"):
        db.dao.get_review_dao().create_review(
            review_id=str(random.randint(10 ** 10, 10 ** 11 - 1)),
            author_id=user_id,
            quote_id=quote_id,
            content=content.strip(),
        )


def s_get_reviews_by_quote_id(quote_id: str) -> List[Review]:
    """
    获取语录的所有评论
    """
    with service_exception("获取评论"):
        return db.dao.get_review_dao().get_reviews_by_quote(quote_id)