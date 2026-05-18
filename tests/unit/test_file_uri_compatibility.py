"""
Verify file paths use .as_uri() for cross-platform compatibility (fix #15).
"""

from pathlib import Path


class TestScreenShotFileUri:
    def test_uses_as_uri_not_string_concat(self):
        """screen_shot.py uses .as_uri() instead of 'file://' + str()."""
        ss_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "html_capture" / "screen_shot.py"
        source = ss_file.read_text(encoding="utf-8")
        assert '.as_uri()' in source, "Should use .as_uri() for file paths"
        assert 'page.goto' in source, "page.goto call should use .as_uri()"

    def test_as_uri_produces_valid_file_uri(self):
        """as_uri() produces a valid file:/// URI on all platforms."""
        test_path = Path("C:/Users/test/file.html")
        uri = test_path.as_uri()
        assert uri.startswith("file:///"), f"Expected file:/// prefix, got: {uri}"


class TestRankResourcePaths:
    def test_rank_py_uses_as_uri(self):
        """rank.py uses .as_uri() for resource paths passed to template."""
        rank_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "templates" / "schema" / "rank.py"
        source = rank_file.read_text(encoding="utf-8")
        assert '.as_uri()' in source, "Resource paths should use .as_uri()"
