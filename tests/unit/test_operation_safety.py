"""
P1 Bugs #22, #23, #24, #25: HTML capture, DB, Command bugs.
"""
import re
from pathlib import Path


class TestScreenshotTempFileLeak:
    def test_screenshot_cleans_temp_files_on_error(self):
        """_html_img_render should clean temp files in except block, not only happy path."""
        ss_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "html_capture" / "screen_shot.py"
        source = ss_file.read_text(encoding="utf-8")

        # Find each except block and check only its body (lines with deeper indent
        # than the except keyword itself) for cleanup calls.
        lines = source.split('\n')
        all_except_bodies_have_cleanup = True
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('except'):
                except_indent = len(line) - len(line.lstrip())
                # Scan subsequent lines that are deeper-indented (the except body)
                body_has_cleanup = False
                for j in range(i + 1, min(i + 20, len(lines))):
                    next_line = lines[j]
                    if next_line.strip() == '':
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= except_indent:
                        break  # Back to outer scope, except body ended
                    if 'unlink' in next_line or 'clean' in next_line.lower():
                        body_has_cleanup = True
                        break
                if not body_has_cleanup:
                    all_except_bodies_have_cleanup = False
                    break

        assert all_except_bodies_have_cleanup, (
            "BUG CONFIRMED: _html_img_render cleans temp files only on the happy path.\n"
            "The screenshot except block (line 64-66) re-raises without deleting\n"
            "temp_html or temp_image. temp_html and temp_image are leaked on error."
        )


class TestAlembicDowngradeDataLoss:
    def test_initial_downgrade_is_safe(self):
        """Initial migration downgrade should NOT drop all tables unconditionally."""
        mig_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "database" / "alembic" / "versions" / "9a62ce7e5cff_initial_schema.py"
        source = mig_file.read_text(encoding="utf-8")
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'downgrade':
                downgrade_source = ast.get_source_segment(source, node)
                # Count op.drop_table calls — 11 tables dropped one by one
                drop_count = downgrade_source.count('op.drop_table')
                has_many_drops = drop_count > 5
                has_safety = any(kw in downgrade_source.lower() for kw in ('confirm', 'backup', 'warning', 'raise', 'input'))
                assert not (has_many_drops and not has_safety), (
                    "BUG CONFIRMED: downgrade() drops {} tables unconditionally\n"
                    "with no safety guard, backup, or confirmation. Accidental execution\n"
                    "causes irreversible data loss.".format(drop_count)
                )
                return
        raise AssertionError("downgrade function not found")


class TestFuzzySearchZipTruncation:
    def test_fuzzy_search_aligns_scores_with_boxes(self):
        """zip(quote_boxes, scores) should verify equal lengths, not silently truncate."""
        src_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "command" / "cmds" / "search_quote_cmd.py"
        source = src_file.read_text(encoding="utf-8")

        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_do_fuzzy_search':
                func_source = ast.get_source_segment(source, node)
                has_zip = 'zip(' in func_source
                # Check for specific length-equality guard before zip
                has_length_guard = any(re.search(pat, func_source) for pat in [
                    r'len\(quote_boxes\)\s*==\s*len\(scores\)',
                    r'len\(scores\)\s*==\s*len\(quote_boxes\)',
                    r'assert.*len.*quote_boxes.*len.*scores',
                    r'zip_longest',
                ])
                assert not (has_zip and not has_length_guard), (
                    "BUG CONFIRMED: _do_fuzzy_search uses zip(quote_boxes, scores) without\n"
                    "verifying equal lengths. If transform_quotes_to_template_boxes drops items,\n"
                    "scores silently misalign with wrong boxes."
                )
                return
        raise AssertionError("_do_fuzzy_search function not found")


class TestSyncFileReadInAsync:
    def test_to_data_uri_uses_async_read(self):
        """_to_data_uri or transform_quotes_to_template_boxes should not do sync file I/O."""
        dh_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "command" / "cmds" / "_display_helpers.py"
        source = dh_file.read_text(encoding="utf-8")
        has_read_bytes = 'read_bytes()' in source
        has_async_read = 'aiofiles' in source or 'run_in_executor' in source
        assert not (has_read_bytes and not has_async_read), (
            "BUG CONFIRMED: _to_data_uri/transform_quotes_to_template_boxes uses\n"
            "synchronous read_bytes() in an async handler, blocking the event loop."
        )
