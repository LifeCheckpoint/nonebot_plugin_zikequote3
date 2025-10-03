<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# ZikeQuote3

_✨ 一个 LLM 介入的群聊语录插件 ✨_

</div>

## 📖 介绍

ZikeQuote3 基于 NoneBot2 开发，便于群聊语录自动收集与管理，支持通过 LLM 自动收集群聊消息作为语录、手动管理语录、以及多种方式查看等功能。

## 🗒️ 功能

- **自动收集**: 监听群聊消息，当消息数量达到配置阈值时，自动触发 LLM 对消息历史进行筛选和提取，将符合条件的消收集为语录。
- **手动管理**: 支持通过命令手动添加、删除和评论语录。
- **语录排行**: 统计群组成员的语录数量，生成排行榜，并以图片形式展示。
- **随机语录**: 随机获取一条语录，支持按关键词过滤，并根据语录的展示次数进行权重调整。
- **语录卡片**: 将单条语录生成卡片图片，方便分享。
- **语录列表**: 查看某个用户（默认为命令发送者）的语录列表，支持分页，并生成图片展示。
- **语录搜索**: 搜索包含指定关键词的语录，并生成图片展示。
- **语录评论**: 对已有语录添加评论。
- **LLM 集成**: 利用 LLM 对消息历史进行智能分析，自动提取 1~3 条高质量语录并生成评论。
- **权限控制**: 支持基于群组 ID 的白名单或黑名单权限控制。

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

2. **确保系统安装 Node.js**，首次进入插件**默认自动安装前端依赖**，或者手动安装截图相关后端及其依赖：
    ```bash
    cd your/bot/plugins/external/html_render/
    npm install
    ```
3. 创建文件 `utils/api_key` 配置 LLM API Key，可自行修改 `utils/llm_solo.py` 使用自定义客户端、模型与参数

## ⚙ 配置

插件的配置项位于 `config.toml` 文件中，部分设置支持动态修改

## 🎉 使用

插件主要命令：

- `/语录rank [数字]`: 查看语录排行榜，可指定显示前几名。
- `(reply) /加语录`: 添加语录。
- `/删语录 语录ID 或 回复消息 /删语录`: 删除语录（需要管理员权限）。
- `(reply) /评 评价内容`: 评论语录。
- `/删评 评论ID`: 删除自己的评论。
- `/语录 [关键词]`: 随机获取一条语录，可按关键词搜索。
- `/语录卡 [关键词]`: 生成语录卡片图片，可按关键词搜索。
- `/语录列表 [用户]`: 查看某个用户的语录列表。
- `/查语录 关键词`: 搜索包含指定关键词的语录。


## 🖼️ 更新日志

### V0.4.0.alpha1 BREAKING CHANGES

1. ▶️ 数据后端更换为 SQLite，**不再**保留 JSON 等各类临时数据。可通过 `utils/data_migration/quote_migration` 进行数据迁移。更换后，支持自动数据备份，数据的统一性和稳定性也大幅提升
2. ▶️ 配置文件更换为 TOML，支持群际自定义配置、动态修改与热更新
3. ▶️ 新增了跨群个人语录调用功能
4. ▶️ 新增了命令解析功能，为常用命令提供标志
5. ▶️ 优化 LLM 配置体验，删减冗余配置依赖
6. ▶️ 优化语录推荐算法，允许权重调整法与多样性过滤法进行
7. ▶️ 新增语录图片储存，允许手动添加图片到语录数据库~
8. ▶️ 回复模板标准化，也拓展啦~

### V0.3.2

1. 更新了自动依赖安装
2. LLM 相关检查更加健全
3. 更新了项目包结构
4. 新增配置项验证

### V0.3.1

1. 修复了初始版本重构引发的大部分 BUG
2. 添加了语录评论删除功能
3. 添加了设置项显示（管理员）
4. 细化了权限控制功能
5. 规范了配置文件
6. 命令现在被集中管理

## 🚧 实现

- **数据存储**:
    - 语录数据和聊天历史记录均以 JSON 格式存储在本地文件系统中，每个群组对应一个独立的文件（位于插件数据目录下的 `history` 和 `quotes` 子目录）。

- **自动收集机制**:
    - 如果相关配置 `cfg.enable_auto_collect` 被启用，插件将捕获群聊消息，并将消息暂存。
    - 当暂存的消息数量达到配置的阈值 `cfg.pickup_interval`，触发自动收集流程 `interface/message_handle.py`。
    - 消息历史被发送给集成 LLM，LLM 根据预设的 Prompt `prompts/quote_pickup.txt` 对消息进行分析，提取潜在的语录并生成评论。
    - 提取出的语录和评论会被添加到语录库中。

- **语录处理**:
    - 语录收集通过 `external/json_data_manager/chat_history_data.py` 收集历史信息实现
    - 语录的添加、删除和评论等操作通过直接操作群聊对应 JSON 数据文件。
    - 随机语录的选取采用了基于展示次数的简单权重算法 `interface/quote_handle.py::calculate_weight`。

- **HTML 渲染**:
    - 插件利用 `external/html_render/` 渲染图片。
    - 渲染通过 Python 调用 Node.js 脚本 `external/html_render/screenshot.js`，使用 Puppeteer 库来控制无头浏览器加载本地 HTML 模板文件 `templates/` 目录，并进行截图。

- **消息文本管理**:
    - 插件的消息回复文本通过 `external/msg_text/msg.py` 进行管理。
    - 支持带有概率的文本片段字典和固定文本混合。