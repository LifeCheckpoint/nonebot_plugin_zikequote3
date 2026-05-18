"""
P1 Bug #3: Division by zero in IFW/LogIFW weights with a_=0 and uniform show times.
P1 Bug #4: Whitespace-only review content stored without rejection.
P1 Bug #7: Whitespace-only messages enqueued without rejection.
P1 Bug #9: Bare except Exception swallows CancelledError in migration.
P1 Bug #10: Bare except Exception swallows CancelledError in get_avatar.
"""

import inspect as _inspect
import math
import pytest


# ========================================================================= #
#  Bug #3: Division by zero in IFW/LogIFW weights
# ========================================================================= #

class TestWeightedRandomDivByZero:
    """_calc_ifw_weights / _calc_logifw_weights: no guard against a_=0 with uniform times."""

    def test_ifw_guard_missing_when_all_same_show_time(self):
        """When a_=0 and all quotes have identical total_show_time, denominator is 0."""
        from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService

        source = _inspect.getsource(QuoteReadService._calc_ifw_weights)
        has_epsilon = 'epsilon' in source
        has_a_guard_line = any(
            line.strip().startswith('if ') and 'a_' in line and (
                '<= 0' in line or '< 0' in line or '== 0' in line or 'a_ >' in line
            )
            for line in source.split('\n')
        )
        has_guard = has_epsilon or has_a_guard_line
        assert has_guard, (
            "BUG CONFIRMED: _calc_ifw_weights has no guard against a_=0.\n"
            "When all quotes have identical total_show_time and a_=0,\n"
            "the denominator (total_show_time - min_c + a_) = 0 → ZeroDivisionError."
        )

    def test_logifw_guard_missing_when_all_same_show_time(self):
        """When a_=0, log_a_=1 and all quotes have identical total_show_time, denominator is 0."""
        from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
        source = _inspect.getsource(QuoteReadService._calc_logifw_weights)
        has_epsilon = 'epsilon' in source
        has_a_guard_line = any(
            line.strip().startswith('if ') and (
                ('a_' in line and ('<= 0' in line or '< 0' in line or '== 0' in line))
                or ('log_a_' in line)
            )
            for line in source.split('\n')
        )
        has_guard = has_epsilon or has_a_guard_line
        assert has_guard, (
            "BUG CONFIRMED: _calc_logifw_weights has no guard against a_=0/log_a_=1.\n"
            "When all quotes have identical total_show_time: math.log(0) or division by zero."
        )

    def test_ifw_denominator_calculated_correctly_with_real_values(self):
        """After fix: no ZeroDivisionError when a_=0 and uniform show times — epsilon guard works."""
        from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService

        class FakeQuote:
            def __init__(self, qid, st):
                self.quote_id = qid
                self.total_show_time = st

        quotes = [
            FakeQuote('q1', 5.0),
            FakeQuote('q2', 5.0),
        ]
        weights = QuoteReadService._calc_ifw_weights(quotes, a_=0.0, lambda_=1.0)
        assert len(weights) == 2
        assert all(w > 0 for w in weights.values())
        assert math.isclose(sum(weights.values()), 1.0)

    def test_logifw_denominator_zero_with_real_values(self):
        """Verify true ValueError (log domain) or ZeroDivisionError with mock-like values."""
        from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService

        class FakeQuote:
            def __init__(self, qid, st):
                self.quote_id = qid
                self.total_show_time = st

        quotes = [
            FakeQuote('q1', 5.0),
            FakeQuote('q2', 5.0),
        ]
        # a_=0, log_a_=1 → math.log(0) from (5 - 5 + 1)=1, then denom = 0 + 0 = 0
        with pytest.raises(ZeroDivisionError):
            QuoteReadService._calc_logifw_weights(quotes, a_=0.0, log_a_=1.0, lambda_=1.0)


# ========================================================================= #
#  Bug #4: Whitespace-only review content stored
# ========================================================================= #

class TestWhitespaceReviewContent:
    """add_review strips content but never rejects empty result."""

    def test_add_review_never_rejects_empty_string(self):
        """content.strip() is applied, but if result is '' it is still stored."""
        source = _inspect.getsource(
            __import__(
                'nonebot_plugin_zikequote3.services.review_service',
                fromlist=['ReviewService'],
            ).ReviewService.add_review,
        )
        has_strip = 'strip()' in source
        # Check for any guard that would reject an empty/whitespace string before calling create_review
        lines = [l.strip() for l in source.split('\n')]
        has_reject = False
        for i, line in enumerate(lines):
            # Patterns that indicate validation before storage:
            if 'if not content' in line and 'raise' in lines[min(i + 1, len(lines) - 1)]:
                has_reject = True
            if 'ValidationException' in source and 'content' in source:
                has_reject = True
            if 'raise' in line and ('empty' in line.lower() or 'blank' in line.lower() or 'whitespace' in line.lower()):
                has_reject = True
        assert has_reject, (
            "BUG CONFIRMED: add_review calls content.strip() but never checks if the\n"
            "result is empty. Whitespace-only strings like '   ' are stored as ''."
        )


# ========================================================================= #
#  Bug #7: Whitespace-only messages enqueued
# ========================================================================= #

class TestWhitespaceMessageEnqueue:
    """enqueue_message strips content but never rejects empty result."""

    def test_enqueue_message_never_rejects_empty_string(self):
        """content.strip() is applied, but whitespace-only messages still enter the queue."""
        source = _inspect.getsource(
            __import__(
                'nonebot_plugin_zikequote3.services.quote_collection_service',
                fromlist=['QuoteCollectionService'],
            ).QuoteCollectionService.enqueue_message,
        )
        has_strip = 'strip()' in source
        lines = [l.strip() for l in source.split('\n')]
        has_reject = False
        for i, line in enumerate(lines):
            if 'if not content' in line:
                has_reject = True
            if 'raise' in line and ('empty' in line.lower() or 'blank' in line.lower() or 'whitespace' in line.lower()):
                has_reject = True
        assert has_reject, (
            "BUG CONFIRMED: enqueue_message calls content.strip() but never checks if the\n"
            "result is empty. Whitespace-only messages enter the queue and waste LLM tokens."
        )


# ========================================================================= #
#  Bug #9: Bare except Exception swallows CancelledError in migration
# ========================================================================= #

class TestMigrationCancelledErrorSwallowed:
    """_migrate_user_infos has bare except Exception that catches CancelledError (Python 3.9+)."""

    def test_migrate_user_infos_has_broad_except(self):
        """Check that except Exception is used without re-raising CancelledError."""
        source = _inspect.getsource(
            __import__(
                'nonebot_plugin_zikequote3.services.migration_service',
                fromlist=['MigrationService'],
            ).MigrationService._migrate_user_infos,
        )
        lines = source.split('\n')
        has_except_exception = False
        has_cancelled_aware = False
        for line in lines:
            if 'except Exception' in line:
                has_except_exception = True
            if 'CancelledError' in line or 'cancelled' in line.lower():
                has_cancelled_aware = True
            if 'except asyncio.CancelledError' in line:
                has_cancelled_aware = True
        if has_except_exception and not has_cancelled_aware:
            pass  # Bug confirmed
        assert not (has_except_exception and not has_cancelled_aware), (
            "BUG CONFIRMED: _migrate_user_infos uses 'except Exception as exc:'\n"
            "which catches asyncio.CancelledError (since Python 3.9). The CancelledError\n"
            "is re-wrapped as OperationError, preventing clean task cancellation."
        )


# ========================================================================= #
#  Bug #10: Bare except Exception swallows CancelledError in get_avatar
# ========================================================================= #

class TestGetAvatarCancelledErrorSwallowed:
    """get_avatar has bare except Exception that catches CancelledError (Python 3.9+)."""

    def test_get_avatar_has_broad_except(self):
        """Check that except Exception is used without re-raising CancelledError."""
        source = _inspect.getsource(
            __import__(
                'nonebot_plugin_zikequote3.services.user_service',
                fromlist=['UserService'],
            ).UserService.get_avatar,
        )
        lines = source.split('\n')
        has_except_exception = False
        has_cancelled_aware = False
        for line in lines:
            if 'except Exception' in line:
                has_except_exception = True
            if 'CancelledError' in line or 'cancelled' in line.lower():
                has_cancelled_aware = True
        if has_except_exception and not has_cancelled_aware:
            pass  # Bug confirmed
        assert not (has_except_exception and not has_cancelled_aware), (
            "BUG CONFIRMED: get_avatar uses 'except Exception:' which catches\n"
            "asyncio.CancelledError (since Python 3.9). The cancellation is silenced\n"
            "with a warning log and None return, preventing clean task cancellation."
        )
