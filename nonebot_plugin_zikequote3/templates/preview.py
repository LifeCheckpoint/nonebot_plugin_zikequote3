"""
模板预览工具。

用法:
    python -m nonebot_plugin_zikequote3.templates <template_name> [--open]
    python -m nonebot_plugin_zikequote3.templates --list
    python -m nonebot_plugin_zikequote3.templates --all [--open]
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path
from typing import Optional

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUT_DIR = Path(__file__).parent / "output" / "rendered_html"


def load_fixture(template_name: str) -> dict:
    """加载模板的 fixture 数据。"""
    fixture_path = FIXTURES_DIR / f"{template_name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture 不存在: {fixture_path}")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _render_template(template_name: str, fixture_data: dict) -> str:
    """根据模板名称调用对应的 render 函数。"""
    if template_name == "card":
        from .schema.card import TemplateQuoteCardData, render_card
        return render_card(TemplateQuoteCardData(**fixture_data))

    elif template_name == "listing":
        from .schema.listing import TemplateQuoteListData, render_list
        return render_list(TemplateQuoteListData(**fixture_data))

    elif template_name == "help":
        from .schema.help import TemplateHelpData, render_help
        return render_help(TemplateHelpData(**fixture_data))

    elif template_name == "rank":
        from .schema.rank import TemplateRankingData, render_rank
        return render_rank(TemplateRankingData(**fixture_data))

    elif template_name == "user_info":
        from .schema.user_info import TemplateUserInfoData, render_user_info
        return render_user_info(TemplateUserInfoData(**fixture_data))

    elif template_name == "code_frame":
        from .schema.code_frame import TemplateCodeFrameData, render_code_frame
        return render_code_frame(TemplateCodeFrameData(**fixture_data))

    elif template_name == "migration":
        from .schema.migration import TemplateMigrationData, render_migration_diff
        return render_migration_diff(TemplateMigrationData(**fixture_data))

    elif template_name == "md":
        from .schema.md import render_markdown
        return render_markdown(fixture_data["content"])

    else:
        raise ValueError(f"未知模板: {template_name}")


def preview_template(
    template_name: str,
    *,
    open_browser: bool = False,
    output_path: Optional[Path] = None,
) -> Path:
    """预览指定模板：加载 fixture → 渲染 → 写入 HTML 文件。"""
    from .registry import ALL_SPECS

    if template_name not in ALL_SPECS:
        raise ValueError(
            f"未知模板 '{template_name}'，可用模板: {', '.join(ALL_SPECS)}"
        )

    fixture_data = load_fixture(template_name)
    html = _render_template(template_name, fixture_data)

    if output_path is None:
        output_path = OUTPUT_DIR / f"preview_{template_name}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    if open_browser:
        webbrowser.open(output_path.as_uri())

    return output_path


def main() -> None:
    """CLI 入口。"""
    from .registry import ALL_SPECS

    parser = argparse.ArgumentParser(
        description="ZikeQuote3 模板预览工具",
    )
    parser.add_argument(
        "template",
        nargs="?",
        choices=list(ALL_SPECS.keys()),
        help="要预览的模板名称",
    )
    parser.add_argument("--list", action="store_true", help="列出所有可用模板")
    parser.add_argument("--all", action="store_true", help="预览所有模板")
    parser.add_argument("--open", action="store_true", help="在浏览器中打开")

    args = parser.parse_args()

    if args.list:
        print("可用模板:")
        for name, spec in ALL_SPECS.items():
            has_fixture = (FIXTURES_DIR / f"{name}.json").exists()
            mark = "✅" if has_fixture else "❌ 缺少 fixture"
            print(f"  {name:15s} {spec.width}x{spec.height}  {mark}")
        return

    if args.all:
        print("预览所有模板:")
        for name in ALL_SPECS:
            try:
                path = preview_template(name, open_browser=args.open)
                print(f"  ✅ {name}: {path}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        return

    if args.template:
        path = preview_template(args.template, open_browser=args.open)
        print(f"预览已生成: {path}")
    else:
        parser.print_help()
