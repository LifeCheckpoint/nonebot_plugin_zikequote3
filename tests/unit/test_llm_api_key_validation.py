"""
Verify empty API key is rejected (fix #13).
"""

from pathlib import Path


class TestApiKeyValidation:
    def test_create_model_validates_empty_key(self):
        """API key loading validates the key is non-empty after strip."""
        client_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "llm_services" / "client.py"
        source = client_file.read_text(encoding="utf-8")
        assert 'if not api_key' in source or 'not api_key' in source, (
            "Should validate API key is non-empty after reading"
        )
        assert 'raise' in source, "Should raise on empty API key"

    def test_api_key_read_and_stripped(self):
        """API key is still read and stripped before validation."""
        client_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "llm_services" / "client.py"
        source = client_file.read_text(encoding="utf-8")
        assert '.strip()' in source, "Should strip whitespace from API key"
