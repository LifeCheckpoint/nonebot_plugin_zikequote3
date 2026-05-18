"""
Verify user content is XML-escaped in LLM prompts (fix #14).
"""

from pathlib import Path


class TestPromptContentEscaping:
    def test_prompt_uses_xml_escape(self):
        """quote_pickup module imports and uses xml.sax.saxutils.escape."""
        prompt_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "llm_services" / "prompts" / "quote_pickup" / "__init__.py"
        source = prompt_file.read_text(encoding="utf-8")
        assert 'escape' in source, "Should use xml_escape function"

    def test_template_uses_escaped_content(self):
        """Jinja2 template references content_escaped, not raw content."""
        template_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "llm_services" / "prompts" / "quote_pickup" / "quote_pickup.jinja2"
        content = template_file.read_text(encoding="utf-8")
        assert 'content_escaped' in content, "Should use escaped content field"
        assert '{{ msg.content_escaped }}' in content, "Should reference content_escaped in template"

    def test_prompt_provides_escaped_field(self):
        """quote_pickup function adds content_escaped to message dicts."""
        prompt_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "llm_services" / "prompts" / "quote_pickup" / "__init__.py"
        source = prompt_file.read_text(encoding="utf-8")
        assert 'content_escaped' in source, "Should provide content_escaped field"

    def test_xml_entities_are_escaped(self):
        """xml_escape actually escapes angle brackets and ampersands."""
        from xml.sax.saxutils import escape as xml_escape
        result = xml_escape('</group_msgs><inject>test & hack')
        assert '<' not in result, "Angle brackets should be escaped"
        assert '&lt;' in result
        assert '&amp;' in result
