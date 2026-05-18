"""
P1 Bugs #19, #20, #21: Utility function bugs.
"""
import inspect


class TestHitokotoBroadExcept:
    def test_get_hitokoto_handles_cancelled(self):
        """get_hitokoto should re-raise CancelledError, not swallow it."""
        from nonebot_plugin_zikequote3.utils.hitokoto import get_hitokoto
        source = inspect.getsource(get_hitokoto)
        lines = source.split('\n')
        has_cancelled_check = False
        for line in lines:
            if 'CancelledError' in line or 'cancelled' in line.lower():
                has_cancelled_check = True
        assert has_cancelled_check, (
            "BUG CONFIRMED: get_hitokoto catches all Exception including CancelledError\n"
            "and silently returns (None, None). Should re-raise CancelledError explicitly."
        )

    def test_get_hitokoto_logs_errors(self):
        """get_hitokoto should log errors before returning None."""
        from nonebot_plugin_zikequote3.utils.hitokoto import get_hitokoto
        source = inspect.getsource(get_hitokoto)
        has_logging = 'logger' in source
        assert has_logging, (
            "BUG CONFIRMED: get_hitokoto catches exceptions silently with no logging.\n"
            "Timeouts and other errors produce no diagnostic output."
        )


class TestJsonCodeBlockRegex:
    def test_code_block_regex_handles_newline_separated_markers(self):
        """Should handle ```json\n{...}\n``` not just ``````json{...}``````."""
        from pathlib import Path
        jp_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "utils" / "json_parser.py"
        source = jp_file.read_text(encoding="utf-8")
        # BUG: only checks startswith/endswith with exact prefix
        handles_partial_prefix = 'startswith' in source and 'endswith' in source
        assert not handles_partial_prefix, (
            "BUG CONFIRMED: llm_json_parse_model only checks startswith/endswith for\n"
            "exact marker pairs. Doesn't handle ```json\\n...\\n``` pattern where\n"
            "newlines separate the fence from content."
        )


class TestCommentStripRegex:
    def test_comment_strip_handles_literal_values(self):
        """Comment-strip should handle true, false, null, and string literals."""
        from pathlib import Path
        jp_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "utils" / "json_parser.py"
        source = jp_file.read_text(encoding="utf-8")
        regex_line = None
        for line in source.split('\n'):
            if '(?<=' in line and '//' in line:
                regex_line = line.strip()
                break
        if regex_line:
            has_string_match = '"' in regex_line.replace('(?<=', '').split(']')[0]
            has_keywords = 'true' in regex_line.lower() or 'false' in regex_line.lower() or 'null' in regex_line.lower()
            assert has_string_match and has_keywords, (
                f"BUG CONFIRMED: Comment strip regex lacks string/keyword matching.\n"
                f"Current lookbehind: {regex_line}\n"
                f"Missing: true, false, null, and string values after comments."
            )
        else:
            raise AssertionError("Could not find comment-strip regex")
