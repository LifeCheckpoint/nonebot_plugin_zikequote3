"""模板规格注册表 — 声明式管理所有模板的元数据和渲染参数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from . import read_resource_file, render_template


@dataclass(frozen=True)
class TemplateSpec:
    """模板规格声明。"""

    name: str
    template: str
    css_files: Sequence[str] = ()
    js_files: Sequence[str] = ()
    width: int = 1000
    height: int = 800
    wait: int = 200


# ── 注册表 ──────────────────────────────────────────────

CARD = TemplateSpec(
    name="card",
    template="htmls/card.html.jinja2",
    css_files=("css/card.css",),
    width=300,
    height=120,
)

LISTING = TemplateSpec(
    name="listing",
    template="htmls/listing.html.jinja2",
    css_files=("css/listing.css",),
    width=1520,
    height=200,
)

HELP = TemplateSpec(
    name="help",
    template="htmls/help.html.jinja2",
    css_files=("css/help.css",),
    width=800,
    height=800,
)

RANK = TemplateSpec(
    name="rank",
    template="htmls/rank.html.jinja2",
    css_files=("css/rank.css",),
    width=1920,
    height=1080,
    wait=3000,
)

USER_INFO = TemplateSpec(
    name="user_info",
    template="htmls/user_info.html.jinja2",
    css_files=("css/user_info.css",),
    width=450,
    height=100,
)

CODE_FRAME = TemplateSpec(
    name="code_frame",
    template="htmls/code_frame.html.jinja2",
    css_files=("css/codeframe.css",),
    width=800,
    height=600,
)

MIGRATION = TemplateSpec(
    name="migration",
    template="htmls/migration.html.jinja2",
    css_files=("css/migration.css",),
    width=600,
    height=800,
)

MD = TemplateSpec(
    name="md",
    template="htmls/md.html.jinja2",
    css_files=("css/md.css",),
    width=800,
    height=800,
)

# 所有规格的集合，方便遍历
ALL_SPECS: dict[str, TemplateSpec] = {
    s.name: s
    for s in (CARD, LISTING, HELP, RANK, USER_INFO, CODE_FRAME, MIGRATION, MD)
}


# ── 统一渲染入口 ────────────────────────────────────────

def render_with_spec(spec: TemplateSpec, **kwargs: object) -> str:
    """根据 TemplateSpec 渲染模板，自动注入 base_css / inline_css / inline_js。"""
    base_css = read_resource_file("css/base.css")
    inline_css_parts = [read_resource_file(f) for f in spec.css_files]
    inline_css = "\n".join(inline_css_parts)
    inline_js_parts = [read_resource_file(f) for f in spec.js_files]
    inline_js = "\n".join(inline_js_parts) if inline_js_parts else ""
    return render_template(
        spec.template,
        base_css=base_css,
        inline_css=inline_css,
        inline_js=inline_js,
        **kwargs,
    )
