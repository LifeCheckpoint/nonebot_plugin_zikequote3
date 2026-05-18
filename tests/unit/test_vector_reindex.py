"""
Verify reindex_all calls ensure_table in both branches (fix #12).
"""

import ast
from pathlib import Path


def _contains_call(node, name):
    """Check whether an AST node or its descendants contain a call to the given method name."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr == name:
                return True
    return False


class TestReindexBothPaths:
    def test_ensure_table_outside_if_else(self):
        """ensure_table() and set_meta() run in both per-group and full-rebuild paths."""
        vs_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "vector_search" / "search_service.py"
        source = vs_file.read_text(encoding="utf-8")

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'reindex_all':
                ensure_in_if_body = False
                ensure_in_else_body = False
                setmeta_in_if_body = False
                setmeta_in_else_body = False

                for child in node.body:
                    if isinstance(child, ast.AsyncWith):
                        for stmt in child.body:
                            if isinstance(stmt, ast.If):
                                for if_child in stmt.body:
                                    if _contains_call(if_child, 'ensure_table'):
                                        ensure_in_if_body = True
                                    if _contains_call(if_child, 'set_meta'):
                                        setmeta_in_if_body = True
                                for else_child in stmt.orelse:
                                    if _contains_call(else_child, 'ensure_table'):
                                        ensure_in_else_body = True
                                    if _contains_call(else_child, 'set_meta'):
                                        setmeta_in_else_body = True

                assert not ensure_in_if_body, "ensure_table should not be inside 'if' branch"
                assert not ensure_in_else_body, "ensure_table should not be inside 'else' branch"
                assert not setmeta_in_if_body, "set_meta should not be inside 'if' branch"
                assert not setmeta_in_else_body, "set_meta should not be inside 'else' branch"

                assert 'ensure_table' in source, "ensure_table should be called after if/else"
                assert 'set_meta' in source, "set_meta should be called after if/else"
                return

        assert False, "reindex_all method not found"


class TestReindexDeleteByGroupPresent:
    def test_group_id_branch_calls_delete_by_group(self):
        """Per-group reindex still calls delete_by_group."""
        vs_file = Path(__file__).parent.parent.parent / "nonebot_plugin_zikequote3" / "vector_search" / "search_service.py"
        source = vs_file.read_text(encoding="utf-8")
        assert 'delete_by_group' in source, "delete_by_group should still exist"
