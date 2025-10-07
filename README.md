<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/lifecheckpoint/nonebot_plugin_zikequote3/blob/v0.4a1/docs/zikequote3_logo.png" width="180" height="180" alt="ZikeQuote3PluginLogo"></a>
  <br>
</div>

<div align="center">

# ZikeQuote3

✨ _一个 LLM 介入的群聊语录插件_ ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/LifeCheckpoint/nonebot_plugin_zikequote3.svg" alt="license">
</a><!--
<a href="https://pypi.python.org/pypi/nonebot-plugin-zikequote3">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-zikequote3.svg" alt="pypi">
</a>
--><a href="https://www.python.org">
    <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="python">
</a>
<a href="https://nonebot.dev">
    <img src="https://img.shields.io/badge/nonebot-2.0.0+-red.svg" alt="nonebot">
</a>

</div>

## 📖 介绍

ZikeQuote3 基于 NoneBot2 开发，便于群聊语录自动收集与管理，支持通过 LLM 自动收集群聊消息作为语录、手动管理语录、以及多种方式查看等功能。

## 🗒️ 功能

### 🤖 智能收集

- **自动收集**: 持续监听群聊消息，达到消息量阈值**自动触发**筛选。
- **LLM 集成**: LLM **自动分析**消息历史，根据指导提取**群友语录**并生成简短评论。

### 👨‍💻 手动管理

- **手动管理**: 支持通过命令增删查改。
- **语录评论**: 对已有语录**添加评论**，丰富内容。

### 🎨 展示查询

- **随机语录**: 支持**不同算法**模式下的随机语录推荐，同时允许多种**筛选推荐**，支持图像和文字。
- **语录搜索**: 可**搜索罗列**筛选语录。
- **语录排行**: 统计成员语录数量，生成**图片排行榜**。
- **语录列表**: 展示查看用户**语录列表**。

### 📊 插件配置

- **群粒度控制**: 支持精细到群粒度的语录插件配置。
- **动态更新**: 支持热调整配置与热重载配置，灵活方便。

### ⚙️ 权限控制

- **群际精确权限控制**: 通过**权限组**管理方式分配语录功能权限，全面精确。

## 🔧 安装

1. 确保您已经安装了 NoneBot2，然后安装插件本体
    <details close>
    <summary>手动安装</summary>
    下载该仓库后，进入命令行并使用

        poetry install

    以安装 `pyproject.toml` 中的依赖
    </details>

    <details close>
    <summary>使用 nb-cli 安装</summary>
    在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

        nb plugin install nonebot-plugin-zikequote3

    </details>

    <details>
    <summary>使用包管理器安装</summary>
    在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

    <details close>
    <summary>pip</summary>

        pip install nonebot-plugin-zikequote3
    </details>
    <details>
    <summary>pdm</summary>

        pdm add nonebot-plugin-zikequote3
    </details>
    <details>
    <summary>poetry</summary>

        poetry add nonebot-plugin-zikequote3
    </details>
    <details>
    <summary>conda</summary>

        conda install nonebot-plugin-zikequote3
    </details>

    打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

        ```toml
        plugins = ["nonebot-plugin-zikequote3"]
        ```

2. **确保系统安装 Node.js** 并安装截图 npm 依赖
    <details close>
    <summary>安装截图依赖</summary>
    可通过如下方式检查：

        ```bash
        npm --version
        ```

    可运行脚本安装截图 npm 依赖：

        ```bash
        cd your/bot/nonebot_plugin_zikequote3
        python utils/install_frontend.py
        ```

    或者手动安装：

        ```bash
        cd your/bot/nonebot_plugin_zikequote3/html_capture
        npm install
        ```
    </details>

3. 创建文件 `llm_services/api_key` 配置 LLM API Key，可修改 `llm_services/client.py` 使用自定义客户端、模型与自定义参数

4. (可选) 创建文件 `utils/sentry_dsn` 可配置 Sentry 异常报错捕获平台的 dsn

## ⚙ 配置

插件的配置项位于 `config.toml` 文件中，部分设置支持动态修改

## 🎉 使用

插件主要命令：

- `/语录rank [数字]`: 查看语录排行榜，可指定显示前几名。
- `(reply) /加语录`: 添加语录。
- `(reply) /删语录 或 /删语录 语录ID`: 删除语录（需要管理员权限）。
- `(reply) /评 评价内容`: 评论语录。
- `/删评 评论ID`: 删除自己的评论。
- `/语录 [关键词]`: 随机获取一条语录，可按关键词搜索。
- `/语录卡 [关键词]`: 生成语录卡片图片，可按关键词搜索。
- `/语录列表 [用户]`: 查看某个用户的语录列表。
- `/查语录 关键词`: 搜索包含指定关键词的语录。

## 🖼️ 更新日志

`docs/CHANGELOG.md`

## 🤺 隐私告知与考量

本插件涉及用户聊天记录的收集和分析。部署者是数据控制者，有责任遵守当地法律法规，并尊重群成员的隐私。建议部署者在使用前向群成员进行充分告知。
