<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/LifeCheckpoint/nonebot_plugin_zikequote3/blob/main/docs/zikequote3_logo.png" width="180" height="180" alt="ZikeQuote3PluginLogo"></a>
  <br>
</div>

<div align="center">

# ZikeQuote3

✨ _LLM 介入，功能丰富的群聊语录自动收集与管理插件_ ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/LifeCheckpoint/nonebot_plugin_zikequote3.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-zikequote3">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-zikequote3.svg" alt="pypi">
</a>
<a href="https://www.python.org">
    <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="python">
</a>
<a href="https://nonebot.dev">
    <img src="https://img.shields.io/badge/nonebot-2.0.0+-red.svg" alt="nonebot">
</a>

</div>

## ✨ 功能特性

- **🤖 智能收集** — 持续监听群聊消息，达到阈值后由 LLM 自动分析并提取语录，附带简短评论
- **✏️ 手动管理** — 通过命令增删语录、添加/删除评论、附加/移除图片
- **🎨 多样展示** — 随机语录（文字/卡片/图片）、关键词搜索、用户语录列表
- **📊 统计排行** — 语录排行榜、用户语录统计信息、近 15 天走势
- **⚙️ 灵活配置** — 群粒度配置、热更新、基于 `nonebot-plugin-access-control` 的权限控制
- **🔒 隐私保护** — 内置隐私政策查看、个人停用功能（即将启用）

## 📦 安装

### 环境要求

| 依赖 | 版本要求 |
|------|---------|
| Python | >= 3.12 |
| NoneBot2 | >= 2.0.0 |
| 适配器 | OneBot V11 |

### 安装方式

使用 nb-cli（推荐）：

```bash
nb plugin install nonebot-plugin-zikequote3
```

或使用包管理器：

```bash
pip install nonebot-plugin-zikequote3
# 或
uv add nonebot-plugin-zikequote3
# 或
poetry add nonebot-plugin-zikequote3
```

> 如果不使用 nb-cli 安装，需要在 `pyproject.toml` 的 `[tool.nonebot]` 中添加：
> ```toml
> plugins = ["nonebot_plugin_zikequote3"]
> ```

### 安装后配置

1. **配置 LLM API Key**：创建文件 `llm_services/api_key`（相对插件根目录），写入你的 API Key。可在 `config.toml` 的 `[llm]` 部分修改端点、模型等参数。

2. **权限控制（推荐）**：安装 `nonebot-plugin-access-control` 并配置权限，详见其 [文档](https://github.com/bot-ssttkkl/nonebot-plugin-access-control)。

3. **截图渲染**：插件依赖 `nonebot-plugin-htmlrender`（Playwright）。如遇到"找不到浏览器"错误，可在 `.env` 中设置：
   ```
   htmlrender_browser_channel=msedge
   ```

4. **Sentry（可选）**：创建文件 `utils/sentry_dsn` 写入 DSN 即可启用错误追踪。

## 🔧 配置

### .env 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `config_toml` | `str` | 插件目录下的 `config.toml` | TOML 配置文件路径 |

### 群组配置（config.toml）

插件的主要配置位于 `config.toml` 文件中，支持群粒度覆盖。可通过 `/修改语录配置` 命令在线修改群组配置。

#### `[collecting]` 语录收集

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_auto_collect` | `bool` | `true` | 启用自动收集（需配置 LLM） |
| `pickup_interval` | `int` | `80` | 自动收集触发的消息数量阈值 |
| `msg_max_length` | `int` | `35` | 最大可被处理的消息长度 |
| `at_least_selections` | `int` | `0` | LLM 筛选结果个数下限 |
| `at_most_selections` | `int` | `3` | LLM 筛选结果个数上限 |
| `enable_duplicate` | `bool` | `false` | 允许群内个人重复语录 |
| `enable_image_collection` | `bool` | `true` | 允许图片语录收集 |
| `img_max_sidelength` | `int` | `3840` | 图片最大边长（px），超出裁剪 |
| `img_max_size_mb` | `float` | `5` | 图片最大体积（MB） |
| `update_personal_info_probability` | `float` | `0.05` | 收到消息时更新个人信息的概率 |

#### `[fetching]` 语录抽取

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `algorithm` | `str` | `"IFW --lambda 1.0"` | 语录推荐算法命令（IFW / LogIFW 等） |

#### `[showcase]` 语录展示

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_rank_user_num` | `int` | `40` | 排行榜最大用户数 |
| `quote_num_per_page` | `int` | `20` | 每页展示语录数 |
| `max_quotes_in_list` | `int` | `50` | 语录列表最大条数 |
| `comment_show_method` | `str` | `"noai"` | 评论展示方式：`no` / `noai` / `all` |
| `hitokoto_url` | `str` | `"https://v1.hitokoto.cn"` | Hitokoto API 地址 |
| `render_device_factor` | `float` | `2.0` | 图片渲染设备像素比 |
| `quote_content_max_length` | `int` | `500` | 列表中单条语录最大显示字符数，`0` 不限制 |

#### `[comment]` 评论

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_comment_without_prefix` | `bool` | `true` | 允许直接回复语录消息进行评论（无需 `/评语录` 前缀） |

#### `[llm]` LLM 服务

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `base_url` | `str` | `"https://openrouter.ai/api/v1"` | LLM API 端点 |
| `api_key_path` | `str` | `"llm_services/api_key"` | API Key 文件路径 |
| `model` | `str` | `"deepseek/deepseek-v3.2-exp"` | 使用的模型 |
| `temperature` | `float` | `0.2` | 生成温度 |
| `max_retries` | `int` | `3` | 请求失败重试次数 |

#### `[sentry]` 错误追踪

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dsn_path` | `str` | `"utils/sentry_dsn"` | Sentry DSN 文件路径，留空不启用 |

## 📖 命令列表

> 🔍 标有「统一查询」的命令支持多种查询方式：@某人、QQ号、昵称片段、关键词、语录ID。无参数时部分命令默认查询自己。

### 📖 语录查询与浏览

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/语录` | `随机语录` `名人名言` `群友语录` | `/语录 [查询内容]` | 随机抽取一条语录 🔍 |
| `/语录卡` | `语录卡片` `语录card` | `/语录卡 [查询内容]` | 以卡片形式展示随机语录 🔍 |
| `/语录图` | `语录原图` `语录图片` | `/语录图 [查询内容]` | 随机获取含图片的语录原图 🔍 |
| `/查语录` | `搜索语录` `搜语录` `找语录` | `/查语录 [关键词] [@某人] [-r] [-ni] [-m 数量]` | 按关键词搜索语录，支持正则 🔍 |
| `/语录列表` | `语录list` `列语录` `个人语录` | `/语录列表 [页码/范围] [用户]` | 查看用户的语录列表 🔍 |

### ✏️ 语录收集与管理

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/加语录` | `添加语录` `新增语录` | 回复消息 + `/加语录` | 将回复的消息添加为语录 |
| `/加语录图` | `加语录图片` `语录加图` | 回复消息 + `/加语录图` + 图片 | 为已有语录附加图片 |
| `/删语录` | `删除语录` | `/删语录 [语录ID]` 或 回复语录 + `/删语录` | 删除一条语录 |
| `/删语录图` | `删语录图片` `移除语录图` | 回复消息 + `/删语录图` | 移除语录附带的图片 |
| `/评语录` | `评论语录` `评价语录` | 回复语录 + `/评语录 评论内容` | 添加语录评论 |
| `/删评论` | `删除评论` `删语评` | `/删评论 评论ID` | 删除一条评论 |

### 📊 用户与统计

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/语录用户信息` | `语录用户` `语录作者` `作者信息` | `/语录用户信息 [用户]` | 查看用户语录统计信息 🔍 |
| `/语录排行` | `语录排行榜` `语录统计` `语录rank` | `/语录排行 [显示人数]` | 查看群语录排行榜和近 15 天走势 |

### 🔄 语录更新

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/语录强制更新` | `更新语录` `刷新语录` | `/语录强制更新` | 手动触发 LLM 语录收集流程 |

### ⚙️ 配置管理

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/查看语录配置` | `当前语录设置` `查看语录设置` | `/查看语录配置` | 查看当前群组的插件配置 |
| `/修改语录配置` | `修改语录设置` `设置语录配置` | `/修改语录配置 配置项 新值` | 修改当前群组的单项配置 |

### 📌 其他

| 命令 | 别名 | 格式 | 说明 |
|------|------|------|------|
| `/语录隐私政策` | `语录隐私` `语录政策` | `/语录隐私政策` | 查看隐私政策 |
| `/迁移群语录` | `迁移所有群语录` `移动群语录` | `/迁移群语录 源群号 目标群号 [选项]` | 将语录从一个群迁移到另一个群 |
| `/停用语录` | `停用zikequote3` | `/停用语录` | 停用个人语录功能（即将启用） |

## 🏗️ 架构概览

```
Command 层（命令解析与交互）
    ↓
Service 层（业务逻辑）
    ↓
Repository 层（数据访问抽象）
    ↓
ORM 层（SQLAlchemy 2.0 async + aiosqlite）
```

核心技术栈：

| 组件 | 技术 | 说明 |
|------|------|------|
| 依赖注入 | [dishka](https://github.com/reagento/dishka) | AsyncContainer 管理所有依赖生命周期 |
| 数据库 | SQLAlchemy 2.0 async + aiosqlite | 异步 ORM，SQLite 存储 |
| 数据库迁移 | Alembic | 数据库 schema 版本管理 |
| 模板渲染 | Jinja2 + nonebot-plugin-htmlrender | HTML 模板 → Playwright 截图 |
| 命令框架 | nonebot-plugin-alconna | 命令解析与参数处理 |
| 权限控制 | nonebot-plugin-access-control-api | 精细化权限节点树 |

### 权限节点树

插件定义了完整的权限节点树，可通过 `nonebot-plugin-access-control` 进行精细控制：

```
nonebot_plugin_zikequote3
├── be_collected          # 被收集权限
│   ├── llm               # LLM 自动收集
│   └── manual            # 手动添加
├── get                   # 获取语录
│   ├── text / card / image
├── search                # 搜索语录
├── ranking               # 排行榜
├── listing               # 语录列表
│   ├── self / get_user / others
├── review                # 评论
│   ├── add
│   └── delete (self / others)
├── quote                 # 语录管理
│   ├── add (text / image)
│   ├── delete (self / others)
│   ├── attach_image / remove_image
├── settings              # 配置管理
│   ├── get
│   ├── modify (group / global)
│   └── reset (group / global)
├── force_refresh         # 强制更新
├── group_migration       # 群迁移
└── others                # 其他
```

## 🛠️ 开发

### 开发环境搭建

```bash
git clone https://github.com/LifeCheckpoint/nonebot_plugin_zikequote3.git
cd nonebot_plugin_zikequote3
pip install -e ".[dev]"
```

### 项目结构

```
nonebot_plugin_zikequote3/
├── __init__.py              # 插件入口，生命周期管理
├── config.py                # 配置模型定义
├── config.toml              # 默认配置文件
├── paths.py                 # 路径常量
├── command/                 # 命令层：命令定义与处理
│   ├── cmds/                # 各命令实现
│   └── parse_helper/        # 参数解析工具
├── services/                # 服务层：业务逻辑
│   └── permission_management/  # 权限节点定义
├── database/                # 数据层
│   ├── models/              # 领域模型
│   ├── repositories/        # 仓储层
│   └── sa/                  # SQLAlchemy ORM 模型与引擎
├── di/                      # 依赖注入
│   └── providers/           # dishka Provider 定义
├── templates/               # Jinja2 模板与数据模型
├── html_capture/            # Playwright 截图
├── llm_services/            # LLM 客户端
├── exceptions/              # 异常定义
├── msgtexts/                # 消息文本模板
└── utils/                   # 工具函数
```

### 测试

```bash
pytest
```

测试配置已在 `pyproject.toml` 中定义，默认启用覆盖率报告：

```bash
# 等价于
pytest --cov=nonebot_plugin_zikequote3 --cov-report=term-missing --cov-report=html
```

测试目录结构：`tests/unit/`（单元测试）和 `tests/integration/`（集成测试），覆盖命令、仓储、服务三层。

## 🤺 隐私告知

本插件涉及用户聊天记录的收集和分析。部署者是数据控制者，有责任遵守当地法律法规，并尊重群成员的隐私。建议部署者在使用前向群成员进行充分告知。

## 📄 许可证

本项目基于 [MIT](./LICENSE) 许可证开源。
