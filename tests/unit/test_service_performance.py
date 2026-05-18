"""
P1 Bugs #5, #6, #8, #11: Performance issues.
"""
import inspect


class TestNPlusOneQuery:
    def test_get_group_member_quotes_avoids_per_member_loop(self):
        """Should use GROUP BY query, not per-member loop."""
        from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
        source = inspect.getsource(StatisticsService.get_group_member_quote_counts)
        has_per_member_query = 'count_quotes_by_group_and_author' in source or 'for' in source
        has_group_by = 'GROUP BY' in source.upper() or 'group_by' in source
        assert has_group_by, (
            "BUG CONFIRMED: get_group_member_quote_counts iterates members and issues\n"
            "a separate count_quotes_by_group_and_author per member (N+1 queries).\n"
            "Should use a single GROUP BY author_id query."
        )


class TestFullTableScan:
    def test_search_quotes_uses_db_filtering(self):
        """search_quotes should push filtering to DB, not load all into memory."""
        from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
        source = inspect.getsource(StatisticsService.search_quotes)
        has_load_all = 'get_quotes_by_group' in source
        has_db_filter = 'LIKE' in source.upper() or 'like' in source or '.filter(' in source
        assert has_db_filter or not has_load_all, (
            "BUG CONFIRMED: search_quotes loads ALL quotes into memory via\n"
            "get_quotes_by_group, then filters in Python. Should push LIKE/filter to DB."
        )


class TestSyncSqliteBackup:
    def test_backup_uses_async_or_threadpool(self):
        """_backup_database should not block event loop with sync sqlite3."""
        from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
        source = inspect.getsource(QuoteWriteService._backup_database)
        has_sync_sqlite = 'sqlite3.connect' in source
        has_run_in_executor = 'run_in_executor' in source
        has_aiofiles = 'aiofiles' in source
        assert has_run_in_executor or has_aiofiles, (
            "BUG CONFIRMED: _backup_database calls synchronous sqlite3.connect\n"
            "and backup() directly, blocking the async event loop."
        )


class TestAvatarSessionReuse:
    def test_fetch_avatar_reuses_session(self):
        """fetch_avatar should reuse a shared ClientSession, not create per call."""
        from nonebot_plugin_zikequote3.services.user_service import UserService
        source = inspect.getsource(UserService.fetch_avatar)
        has_new_session = 'ClientSession(' in source
        has_shared = 'self._session' in source or 'self._client' in source
        assert has_shared or not has_new_session, (
            "BUG CONFIRMED: fetch_avatar creates a new aiohttp.ClientSession\n"
            "on every call instead of reusing a shared session (loses connection pooling)."
        )
