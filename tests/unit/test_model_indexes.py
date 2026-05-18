"""
Verify frequently-queried columns have explicit Index() after fix #11.
"""

from sqlalchemy import Index


def _get_indexed_columns(model_class):
    table_args = getattr(model_class, '__table_args__', None)
    if table_args is None:
        return set()
    indexed = set()
    items = table_args if isinstance(table_args, tuple) else (table_args,)
    for item in items:
        if isinstance(item, Index):
            for col in item.columns:
                indexed.add(col.name)
    return indexed


class TestQuoteModelIndexes:
    def test_quote_has_group_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.quote import QuoteModel
        assert 'group_id' in _get_indexed_columns(QuoteModel)

    def test_quote_has_author_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.quote import QuoteModel
        assert 'author_id' in _get_indexed_columns(QuoteModel)

    def test_quote_has_total_show_time_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.quote import QuoteModel
        assert 'total_show_time' in _get_indexed_columns(QuoteModel)


class TestReviewModelIndexes:
    def test_review_has_quote_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.review import ReviewModel
        assert 'quote_id' in _get_indexed_columns(ReviewModel)

    def test_review_has_author_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.review import ReviewModel
        assert 'author_id' in _get_indexed_columns(ReviewModel)


class TestMsgQueueModelIndexes:
    def test_msg_queue_has_group_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.msg_queue import MsgQueueModel
        assert 'group_id' in _get_indexed_columns(MsgQueueModel)

    def test_msg_queue_has_qq_id_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.msg_queue import MsgQueueModel
        assert 'qq_id' in _get_indexed_columns(MsgQueueModel)

    def test_msg_queue_has_time_stamp_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.msg_queue import MsgQueueModel
        assert 'time_stamp' in _get_indexed_columns(MsgQueueModel)


class TestImageModelIndexes:
    def test_image_has_checksum_index(self):
        from nonebot_plugin_zikequote3.database.sa.models.image import ImageModel
        assert 'checksum_sha256' in _get_indexed_columns(ImageModel)
