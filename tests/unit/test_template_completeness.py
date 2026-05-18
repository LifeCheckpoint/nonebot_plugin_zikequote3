"""
Verify api_request_error.jinja2 template exists (fix #16).
"""

from pathlib import Path


class TestApiRequestErrorTemplate:
    def test_template_file_exists(self):
        """api_request_error.jinja2 template file exists."""
        template_path = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "msgtexts" / "quote_read" / "api_request_error.jinja2"
        assert template_path.exists(), f"Template file missing: {template_path}"

    def test_template_not_empty(self):
        """Template file has content."""
        template_path = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "msgtexts" / "quote_read" / "api_request_error.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "Template should not be empty"
        assert 'error' in content, "Template should reference error variable"

    def test_api_request_error_returns_string(self):
        """api_request_error() returns a rendered string (no TemplateNotFound)."""
        from nonebot_plugin_zikequote3.msgtexts.quote_read import api_request_error
        try:
            result = api_request_error("测试错误消息")
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            assert False, f"api_request_error() should not raise: {e}"
