from ....imports import *


def s_add_quote(group_id: str, author_id: str, content: str, image_uuid: str | None = None):
    """
    添加语录
    """
    with exception_report("添加语录"):
        db.dao.get_quote_dao().create_quote(
            quote_id=str(random.randint(10 ** 10, 10 ** 11 - 1)),
            author_id=author_id,
            group_id=group_id,
            content=content,
            image_content_uuid=image_uuid
        )