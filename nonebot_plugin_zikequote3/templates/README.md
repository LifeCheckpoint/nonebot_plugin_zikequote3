# 模板渲染系统

## 概述

本模板系统基于 Jinja2 构建，为 ZikeQuote3 插件提供类型安全的 HTML 渲染能力。核心设计理念：

- **声明式注册**：每个模板通过 [`TemplateSpec`](registry.py:12) 声明元数据（尺寸、资源文件），统一管理
- **基础模板继承**：所有常规模板继承 [`base.html.jinja2`](src/htmls/base.html.jinja2)，共享 HTML 骨架和 CSS Reset
- **数据模型驱动**：每个模板配套 Pydantic 模型，确保渲染数据的类型安全
- **CSS 变量系统**：通过 [`base.css`](src/assets/css/base.css) 定义设计令牌，保持视觉一致性
- **预览工具链**：支持离线预览，无需启动 NoneBot 即可调试模板

## 目录结构

```
templates/
├── __init__.py          # 模板引擎核心：Jinja2 环境、render_template()、read_resource_file()
├── __main__.py          # 预览工具 CLI 入口
├── registry.py          # TemplateSpec 注册表 + render_with_spec() 统一渲染入口
├── preview.py           # 预览工具实现
├── schema/              # Pydantic 数据模型 + render_xxx() 渲染函数
│   ├── card.py
│   ├── code_frame.py
│   ├── help.py
│   ├── listing.py
│   ├── md.py
│   ├── migration.py
│   ├── rank.py          # ⚠ 独立渲染，不使用 render_with_spec()
│   └── user_info.py
├── fixtures/            # 预览用 JSON 测试数据
│   ├── card.json
│   ├── code_frame.json
│   └── ...
├── src/
│   ├── htmls/           # Jinja2 模板文件
│   │   ├── base.html.jinja2   # 基础骨架模板
│   │   ├── card.html.jinja2
│   │   └── ...
│   └── assets/
│       ├── css/         # 样式文件
│       │   ├── base.css       # 公共样式 + CSS 变量
│       │   ├── card.css
│       │   └── ...
│       └── js/          # JavaScript 文件（rank 模板使用）
└── output/              # 预览输出目录（git ignored）
```

## 核心概念

### TemplateSpec 注册表

[`TemplateSpec`](registry.py:12) 是一个 frozen dataclass，声明模板的所有元数据：

```python
@dataclass(frozen=True)
class TemplateSpec:
    name: str                        # 模板名称标识
    template: str                    # Jinja2 模板路径（相对于 src/）
    css_files: Sequence[str] = ()    # CSS 文件列表（相对于 src/assets/）
    js_files: Sequence[str] = ()     # JS 文件列表
    width: int = 1000                # 渲染视口宽度
    height: int = 800                # 渲染视口高度
    wait: int = 200                  # 截图前等待时间（ms）
```

所有模板规格在 [`registry.py`](registry.py) 中注册，并汇总到 [`ALL_SPECS`](registry.py:92) 字典中。

### render_with_spec() 统一渲染入口

[`render_with_spec()`](registry.py:100) 是常规模板的统一渲染函数，自动完成：

1. 读取 `base.css` 作为公共样式
2. 读取 spec 声明的 CSS/JS 文件并内联
3. 调用 `render_template()` 渲染 Jinja2 模板

```python
from nonebot_plugin_zikequote3.templates.registry import CARD, render_with_spec

html = render_with_spec(CARD, quote_id="1", author_name="张三", quote="Hello")
```

### 基础模板继承

[`base.html.jinja2`](src/htmls/base.html.jinja2) 提供 HTML 骨架：

```jinja2
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}ZikeQuote3{% endblock %}</title>
  <style>{{ base_css | safe }}</style>
  {% block head_extra %}{% endblock %}
</head>
<body>
  {% block body %}{% endblock %}
</body>
</html>
```

子模板通过 `{% extends "htmls/base.html.jinja2" %}` 继承，只需填充 `head_extra`（注入 CSS）和 `body` 块。

### CSS 变量系统（设计令牌）

[`base.css`](src/assets/css/base.css) 定义了全局设计令牌，所有模板样式应优先使用这些变量：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `--font-main` | `'SF Pro Display', 'Helvetica Neue', ...` | 主字体栈 |
| `--font-mono` | `'SF Mono', 'Monaco', ...` | 等宽字体栈 |
| `--bg-page` | `#F6F7F9` | 页面背景色 |
| `--bg-card` | `#ffffff` | 卡片背景色 |
| `--bg-sidebar` | `#1a1a1a` | 侧边栏背景色 |
| `--text-primary` | `#212121` | 主文本色 |
| `--text-secondary` | `#666666` | 次要文本色 |
| `--text-muted` | `#7D8492` | 弱化文本色 |
| `--accent-blue` | `#007aff` | 强调色（蓝） |
| `--border-light` | `rgba(0, 0, 0, 0.06)` | 浅色边框 |
| `--shadow-card` | `0 2px 16px rgba(0, 0, 0, 0.06)` | 卡片阴影 |
| `--radius-card` | `10px` | 卡片圆角 |
| `--radius-lg` | `22px` | 大圆角 |

## 如何新增模板

以新增一个名为 `example` 的模板为例：

### 1. 创建 Pydantic 数据模型

在 `schema/example.py` 中定义数据模型和渲染函数：

```python
"""示例模板。"""
from pydantic import BaseModel
from ..registry import EXAMPLE, render_with_spec


class TemplateExampleData(BaseModel):
    """示例模板数据。"""
    title: str
    content: str


def render_example(data: TemplateExampleData) -> str:
    """渲染示例模板。"""
    return render_with_spec(EXAMPLE, **data.model_dump())
```

### 2. 创建 Jinja2 模板

在 `src/htmls/example.html.jinja2` 中编写模板，继承 base：

```jinja2
{% extends "htmls/base.html.jinja2" %}

{% block head_extra %}
<style>{{ inline_css | safe }}</style>
{% endblock %}

{% block body %}
<div class="example-container">
  <h1>{{ title }}</h1>
  <p>{{ content }}</p>
</div>
{% endblock %}
```

### 3. 创建 CSS 样式

在 `src/assets/css/example.css` 中编写样式，使用 CSS 变量：

```css
.example-container {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  color: var(--text-primary);
  padding: 24px;
}
```

### 4. 在 registry.py 中注册

```python
EXAMPLE = TemplateSpec(
    name="example",
    template="htmls/example.html.jinja2",
    css_files=("css/example.css",),
    width=800,
    height=600,
)

# 并将 EXAMPLE 加入 ALL_SPECS 的构造元组中
```

### 5. 创建 fixture 数据

在 `fixtures/example.json` 中提供预览用测试数据：

```json
{
  "title": "示例标题",
  "content": "这是一段示例内容。"
}
```

### 6. 注册到预览工具

在 [`preview.py`](preview.py:30) 的 `_render_template()` 中添加分支：

```python
elif template_name == "example":
    from .schema.example import TemplateExampleData, render_example
    return render_example(TemplateExampleData(**fixture_data))
```

### 7. 导出模块

在 [`__init__.py`](__init__.py:68) 中添加导入和 `__all__` 条目。

## 预览工具

预览工具支持在不启动 NoneBot 的情况下渲染模板到 HTML 文件，方便开发调试。

### 运行方式

```bash
# 推荐：直接运行脚本（无需 NoneBot 环境）
python nonebot_plugin_zikequote3/templates/__main__.py <模板名> [--open]

# 模块运行
python -m nonebot_plugin_zikequote3.templates <模板名> [--open]
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `<template>` | 要预览的模板名称 |
| `--list` | 列出所有可用模板及 fixture 状态 |
| `--all` | 预览所有模板 |
| `--open` | 渲染后在浏览器中打开 |

### 示例

```bash
# 列出所有模板
python -m nonebot_plugin_zikequote3.templates --list

# 预览 card 模板并在浏览器打开
python -m nonebot_plugin_zikequote3.templates card --open

# 预览所有模板
python -m nonebot_plugin_zikequote3.templates --all
```

输出文件保存在 `output/rendered_html/preview_<name>.html`。

## 特殊模板：rank

[`rank`](schema/rank.py) 模板因以下原因保持独立渲染，不使用 `render_with_spec()` / `base.html.jinja2`：

- 依赖外部 JS 库（ECharts、color-thief），通过 `file://` 协议引用本地文件
- 需要较长的截图等待时间（`wait=3000`）以等待图表渲染完成
- 模板结构与其他模板差异较大（全屏仪表盘布局）
- CSS/JS 通过 `get_resource_path()` 获取绝对路径，而非内联注入

其 render 函数直接调用 [`render_template()`](__init__.py:19) 而非 `render_with_spec()`。
