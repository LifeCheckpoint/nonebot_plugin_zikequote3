"""
P1 Bugs #16, #17, #18: LLM service bugs.
"""
import inspect
from pathlib import Path


class TestLLMRequestNoTimeout:
    def test_send_llm_request_has_timeout(self):
        """send_llm_request should pass timeout to the API call."""
        from nonebot_plugin_zikequote3.llm_services.client import send_llm_request, create_model
        source = inspect.getsource(send_llm_request)
        model_source = inspect.getsource(create_model)
        combined = source + model_source
        has_timeout = 'timeout' in combined.lower()
        assert has_timeout, (
            "BUG CONFIRMED: send_llm_request and create_model have no explicit timeout.\n"
            "A hanging API endpoint causes the coroutine to hang indefinitely."
        )


class TestNoTokenLimit:
    def test_filter_messages_has_token_limit(self):
        """filter_messages should cap message count or estimate token usage."""
        from nonebot_plugin_zikequote3.llm_services.llm_message_filter import LLMMessageFilter
        source = inspect.getsource(LLMMessageFilter.filter_messages)
        # Check for message truncation before LLM call (not logging slices like [:200])
        has_truncation = (
            'messages[' in source.replace('response_text[', '')   # message list slicing
            or 'MAX_MESSAGES' in source
            or 'len(messages)' in source and any(
                kw in source for kw in ('cap', 'truncat', 'max_msg')
            )
        )
        # Check for actual token estimation (not log format strings with "token")
        has_token_check = (
            'tiktoken' in source.lower()
            or 'num_tokens' in source.lower()
            or 'token_count' in source.lower()
            or 'estimate_token' in source.lower()
        )
        assert has_truncation or has_token_check, (
            "BUG CONFIRMED: filter_messages builds a prompt from all queued messages\n"
            "without any truncation or token estimation. Large queues exceed model context window."
        )


class TestNoCircuitBreaker:
    def test_filter_messages_has_circuit_breaker(self):
        """filter_messages should implement backoff/cooldown after consecutive failures."""
        from nonebot_plugin_zikequote3.llm_services.llm_message_filter import LLMMessageFilter
        source = inspect.getsource(LLMMessageFilter.filter_messages)
        has_failure_track = '_failures' in source or 'fail_count' in source or 'circuit' in source.lower()
        has_backoff = 'backoff' in source.lower() or 'cooldown' in source.lower() or 'sleep' in source.lower() or 'retry' in source.lower()
        assert has_failure_track or has_backoff, (
            "BUG CONFIRMED: filter_messages has no circuit breaker or backoff.\n"
            "If the LLM API is persistently down, every collection trigger retries\n"
            "the call and hammers the broken endpoint."
        )
