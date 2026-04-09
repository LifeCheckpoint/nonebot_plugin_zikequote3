# nonebot-plugin-zikequote3 纯文本消息模板统一设计文档

## 背景与问题

项目当前已经存在两条消息渲染路径。纯文本路径由 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 提供，根目录位于 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/)；HTML 路径由 [`render_template()`](nonebot_plugin_zikequote3/templates/__init__.py:19) 提供，主模板目录位于 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/)。这说明项目并不是缺少模板能力，而是纯文本回复的收口还没有完成。

现状已经有可复用的正向样例。[`handle_random_quote()`](nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py:43) 会调用 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22) 生成纯文本语录内容，说明现有 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 机制已经能够承载命令层纯文本输出。

与此同时，仍有多条纯文本回复散落在命令文件和共享错误处理文件中。[`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30)、[`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203)、[`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96)、[`handle_search_quote()`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py:69) 与 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 都还保留了直接拼接或直接内联的字符串。结果就是同类文案分散在多个业务入口里，后续维护、排查和复用都比较费力。

另一个现实情况是，部分命令天然同时涉及图片模板与纯文本提示。比如 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 既会走迁移确认卡片的图片链路，也会处理取消、超时、Token 校验失败等纯文本提示；[`handle_search_quote()`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py:69) 和 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 也存在“主结果是图片或后台流程提示，异常与边界反馈是纯文本”的混合情况。如果在这次设计里同时重整 HTML 与纯文本模板，范围会明显扩大，边界也会变得含混。

当前问题可以归纳为三点。

- 纯文本回复仍然散落在多个命令文件内，文案维护位置不稳定。
- 已经进入 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 的模板与仍停留在命令中的字符串长期并存，造成统一管理目标迟迟没有落地。
- 命令文件同时承担业务流程、消息装配与文案管理三类职责，影响可读性，也让测试更容易依赖实现细节。

## 目标与非目标

### 目标

- 本设计只统一纯文本回复的管理方式，并把可迁移的纯文本文案收口到 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/)。
- 本设计继续沿用 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 作为纯文本模板入口，不调整现有 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 的入口机制。
- 本设计采用按业务域逐步提取的方式推进，并在各业务子目录的 [`__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 中提供小型包装函数，让命令层只依赖语义化调用，不直接依赖模板文件名。
- 本设计尽量保持现有文案内容不变，迁移时以提取、归类和统一管理为主，不顺手调整语气、措辞或交互风格。
- 本设计通过目录边界和组件职责划分，让命令层重新聚焦在流程控制，文案内容回到模板目录管理。

### 非目标

- 本设计不统一 HTML 与图片主模板，也不改造 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/) 的现有职责。
- 本设计不引入新的消息渲染服务、中间注册中心或额外抽象层，纯文本路径继续使用 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20)。
- 本设计不重写已有业务流程，不调整命令入口协议，也不改变服务层和异常分类模型。
- 本设计不做文案润色工程，不借机修正文风、表情符号或措辞细节。

## 已确认约束

- 只统一纯文本回复，现有 HTML 与图片主模板继续留在 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/)。
- 纯文本回复统一迁入 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/)，并继续沿用 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 机制，不调整现有 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 的入口方式。
- 统一方案采用“按业务域逐步提取 + 在各子目录 [`__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 中提供小型包装函数”的方式推进。
- 文案内容尽量保持现状，迁移动作以提取、搬运和统一管理为主，不顺手改语气或措辞。
- 新增业务域目录必须继续作为 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 下的一级子目录存在，因为当前根入口只按一级子目录组织模板搜索路径，设计范围内不引入更深层级目录方案。
- 新增模板文件需要保证跨业务域的文件名全局唯一，因为当前纯文本模板入口会把多个业务域目录作为并列搜索路径使用，设计范围内不修改这一解析方式。
- 每次新增业务域时，都需要同步更新 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 的导入与导出清单，因为当前入口是显式暴露业务模块，而不是自动发现模块。

## 现状基线文件

- [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 提供纯文本模板加载环境和 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 入口，是本次设计明确保留的根入口。
- [`nonebot_plugin_zikequote3/templates/__init__.py`](nonebot_plugin_zikequote3/templates/__init__.py) 提供 HTML 模板渲染入口 [`render_template()`](nonebot_plugin_zikequote3/templates/__init__.py:19)，也是本次设计明确不动的图片与 HTML 主模板链路。
- [`nonebot_plugin_zikequote3/command/cmds/_error_handlers.py`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py) 中的 [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30) 仍然直接拼接多类异常提示，是共享纯文本回复的重要现状样例。
- [`nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py`](nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py) 中的 [`handle_random_quote()`](nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py:43) 已经通过 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22) 复用纯文本模板，是后续迁移应当遵循的正向模式。
- [`nonebot_plugin_zikequote3/command/cmds/group_migration.py`](nonebot_plugin_zikequote3/command/cmds/group_migration.py) 中的 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 同时覆盖图片确认卡片和多条纯文本提示，是本次边界划分的关键样例。
- [`nonebot_plugin_zikequote3/command/cmds/config_cmd.py`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py) 中的 [`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96) 与查看配置流程仍保留多条直接返回的纯文本提示。
- [`nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py) 中的 [`handle_search_quote()`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py:69) 仍然直接返回搜索校验、向量能力与空结果相关文本。
- [`nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py) 中的 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 仍然直接返回后台重建提示与错误提示。

## 方案选择与取舍

### 保持字符串继续内联

这个方案的优点是短期内完全没有目录调整成本，但它无法解决文案分散、重复字符串难以复用、命令文件职责过重等核心问题。既然项目已经有 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 与 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 这一套可用能力，继续把纯文本留在命令里，等于放弃已有基础设施。

### 把纯文本与 HTML 或图片模板统一到同一套目录和机制

这个方案表面上最“整齐”，但它会打破已经存在的职责边界。当前 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/) 已经承担图片卡片、列表图和 HTML 资源内联等职责，而 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 只负责纯文本字符串渲染。把两者合并，既会扩大改动面，也会让本次设计从“统一纯文本管理”滑向“重构整个消息渲染体系”。这不符合已确认范围。

### 采用按业务域逐步提取 + 小型包装函数

本设计选择这个方案。原因有四点。

- 这个方案直接复用 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 与 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20)，不需要额外引入新的入口。
- 这个方案允许 [`handle_random_quote()`](nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py:43) 这种已经完成模板化的路径继续保持不动，也允许其他命令按业务域逐步迁入，不要求一次性全量搬迁。
- 这个方案可以让命令层调用语义化的小包装函数，例如 [`success()`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py:10) 或 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22)，从而把“模板文件名与参数细节”隐藏在业务域内部。
- 这个方案能够把主要变更限定在纯文本组织层，不触碰 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/) 的 HTML 与图片主模板链路。

这个方案也有代价。迁移期间，模板化文本与旧的内联文本会短暂并存；新增业务域时需要维护入口导入；模板文件名还需要额外规避冲突。但这些代价都比重构两套渲染体系更可控。

## 架构边界

### 输出通道边界

纯文本统一的适用范围只覆盖最终以普通字符串形式返回给命令发送接口的回复。这类回复包括普通成功提示、失败提示、参数校验提示、空结果提示、取消提示和后台任务结果提示。

HTML 与图片主模板继续留在 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/)。像配置预览、搜索结果列表图、迁移确认卡片这类依赖 HTML 结构、资源内联或截图服务的输出，仍然由 [`nonebot_plugin_zikequote3/templates/__init__.py`](nonebot_plugin_zikequote3/templates/__init__.py) 所代表的链路负责。

混合链路沿用“双通道并存”的边界。以 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 为例，迁移确认卡片图片继续留在 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/)；取消、超时、Token 校验失败以及图片渲染失败后的纯文本回退，则进入 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 管理。

### 组件职责边界

[`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 继续承担纯文本模板环境与公共入口职责，不新增额外的渲染服务。

各业务域目录下的 [`__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 只负责提供小型包装函数。包装函数只做两件事：第一件事是暴露稳定的业务语义函数名；第二件事是把调用参数传给 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20)。包装函数不承担业务查询、异常分类、日志记录或消息发送职责。

命令处理器继续负责判断当前应当走纯文本回复还是图片回复。也就是说，命令层仍然保留输出通道选择权，但不再长期持有具体文案内容。

### 命名与层级边界

新增模板文件应当遵循“按业务域放置、按全局唯一命名”的规则。业务域负责划分目录，模板文件名负责避免冲突，两者缺一不可。

当前根入口要求业务域目录维持一级结构，因此本设计不引入更深的模板嵌套层级。新增目录如果需要出现，也应当直接放在 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 下。

## 目录与组件组织

目录组织以“保留现状、逐步扩展”为原则推进。

- [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 继续作为纯文本模板总入口，负责模板环境初始化、业务域模块导入与对外暴露。
- [`nonebot_plugin_zikequote3/msgtexts/general/__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 继续承载跨业务复用的通用文案包装函数，例如 [`success()`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py:10)。共享错误文案和通用成功或失败提示，优先在这一层收口，避免为了少量共通提示拆出过细目录。
- [`nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py) 继续承载语录读取场景的文案包装函数，例如 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22)。这部分现有结构已经可用，不需要先做重命名或重新分层。
- 其他尚未模板化的纯文本回复，按照业务域逐步迁入新的一级目录。新增目录是否出现，以当前内联文本是否已经形成稳定业务主题为判断标准，而不是先做一轮目录大拆分。
- 每个业务域目录内部都应当保持“模板文件 + 小型包装函数”的组织关系。命令层调用包装函数，包装函数再调用 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20)。
- 新增业务域后，需要同步更新 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 的导入与导出清单，确保外部调用路径保持一致。

组件组织上，建议优先遵循两条规则。

- 如果一类纯文本已经在现有业务域中有自然归属，就优先复用已有目录，而不是先新建目录。
- 如果一类纯文本同时出现在多个命令里，并且语义稳定、参数结构固定，就优先抽成包装函数，而不是只搬模板文件不做函数收口。

## 迁移策略与优先级

迁移采用“小步落地、逐域收口、原文搬运”的策略推进。

### 第一优先级

第一批优先处理共享且复用价值最高的纯文本回复。这里重点包括 [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30) 这类共享异常提示，以及其他跨命令复用概率较高的通用成功与失败文案。这样做可以先把最分散、最容易重复出现的一层收口。

### 第二优先级

第二批处理边界清晰、纯文本占比高、与 HTML 主模板耦合较弱的命令。[`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96)、[`handle_search_quote()`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py:69) 与 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 属于这类对象。它们的图片主输出或后台流程可以保持不动，纯文本提示先迁走，收益明显，风险也较低。

### 第三优先级

第三批处理混合链路较重的命令。[`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 既包含图片确认卡片，又包含多条纯文本边界提示，还涉及图片渲染失败后的文本回退。这类命令适合在前两批模式稳定之后再迁移，以免一开始就把输出边界搅在一起。

### 基线保留项

[`handle_random_quote()`](nonebot_plugin_zikequote3/command/cmds/random_quote_cmd.py:43) 已经使用 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22) 作为纯文本模板入口，因此它更适合作为迁移基线和调用风格参照，而不是这次迁移的优先改动对象。

### 迁移执行原则

- 每次迁移只处理一个业务域或一组紧密相关命令，避免一次提交跨越太多场景。
- 每次迁移都先确认原始文案，再把同一句话原样落入模板文件，最后才替换命令层调用点。
- 每次迁移完成后，都应当删除对应命令中的重复字符串，避免模板与内联文本长期双份维护。

## 数据流

### 纯文本回复链路

纯文本回复统一后的数据流分为五步。

1. 命令处理器根据业务结果决定需要发送一条纯文本回复。
2. 命令处理器调用所属业务域 [`__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 中的小型包装函数，例如 [`success()`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py:10) 或 [`send_quote()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:22)。
3. 包装函数把模板文件名与渲染参数交给 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20)。
4. 纯文本模板入口从 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 下对应业务域加载模板并渲染出字符串。
5. 命令处理器把渲染结果发送给用户。

### HTML 与图片链路

HTML 与图片主模板链路保持现状，数据流也不改动。

1. 命令处理器继续构造图片或 HTML 所需的数据对象。
2. 命令处理器继续调用 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/) 内的模板链路完成渲染。
3. 如果主模板渲染失败，且该场景约定了纯文本回退，那么回退文案再从 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 中取得。
4. 如果主模板渲染成功，命令处理器继续按原方式发送图片结果。

这个数据流说明了一点：纯文本统一并不会替代图片模板链路，而是与之并行存在，并在需要时承担兜底文本输出。

## 错误处理策略

[`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30) 当前已经把异常类型和用户可见错误提示分开组织，但提示内容仍然直接写在函数内部。统一方案落地后，这部分“用户可见文本”应当迁入共享业务域模板中，而异常分类、日志记录和上报行为保持不变。

错误处理遵循三条策略。

- 业务含义稳定且跨命令复用的错误提示，应当优先进入共享业务域统一管理。
- 只在单个命令内部有意义的错误提示，仍然归属该命令所在业务域，不强行拉到全局共享层。
- 未知异常的日志记录与上报流程保持原状，统一动作只覆盖最终回给用户的纯文本内容。

这意味着统一动作只处理“错误文本从哪里来”，不处理“错误如何分类、如何记录、是否结束流程”这些行为问题。

## 测试策略

测试策略围绕“文案不变、入口不变、边界不变”三个目标展开。

### 文案回归测试

每次迁移后，都需要验证模板输出与原始字符串保持一致。重点不是测试模板技术本身，而是确认同样的输入参数仍然得到同样的用户可见文本。

### 命令回归测试

已有命令测试需要继续验证输出通道没有变化。原本返回纯文本的场景，迁移后仍然返回纯文本；原本返回图片的场景，迁移后仍然返回图片。像 [`handle_search_quote()`](nonebot_plugin_zikequote3/command/cmds/search_quote_cmd.py:69)、[`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 与 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 这类混合链路，尤其需要验证主输出与回退输出没有串位。

### 入口契约测试

需要补充针对 [`nonebot_plugin_zikequote3/msgtexts/__init__.py`](nonebot_plugin_zikequote3/msgtexts/__init__.py) 的契约测试，确保新增业务域在导入后能够被外部稳定访问，并且 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 仍然是唯一的纯文本模板入口。

### 目录规则测试

需要增加对模板文件命名规则的检查，确保不同业务域之间不会出现同名模板文件。考虑到当前入口会把多个一级目录作为并列搜索路径，这条检查属于必要的回归保护。

### 模板清单核对

需要在迁移前后核对包装函数与模板文件是否一一对应。当前 [`api_request_error()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:10) 已经暴露出“包装函数存在，但模板文件清单未同步可见”的风险，这类问题如果不先核对清单，后续迁移时很容易把缺口继续带下去。

## 风险与不处理项

### 风险

- 当前纯文本模板入口采用并列搜索路径，新增模板时如果文件名重复，就可能出现解析命中不明确的问题。
- 当前纯文本模板目录按一级业务域组织，后续如果有人继续向下嵌套子目录，就会超出既有入口能够稳定承载的范围。
- 迁移期间，新模板与旧内联字符串会短暂并存，如果一次提交跨越过多命令，就容易出现遗漏删除、双份维护或调用路径不一致的问题。
- [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:203) 这类混合链路存在“图片主模板文案”和“纯文本回退文案”双份表达的现实风险，后续如果编辑不同步，可能出现同一业务场景下两套提示不一致。
- [`api_request_error()`](nonebot_plugin_zikequote3/msgtexts/quote_read/__init__.py:10) 暴露出的模板清单缺口说明，统一动作在开始搬运前需要先做现有资产核对，否则容易把历史不一致带入新结构。

### 不处理项

- 本设计不迁移任何 HTML 或图片主模板，相关内容继续留在 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/)。
- 本设计不改变 [`render_template()`](nonebot_plugin_zikequote3/msgtexts/__init__.py:20) 的签名、模板环境初始化方式或根入口位置。
- 本设计不新增消息模板服务层，也不把命令层统一改造成新的发送抽象。
- 本设计不借机重写现有文案，不整理表情、语气词或提示风格。
- 本设计不处理纯文本统一范围之外的结构性重构，例如服务层重命名、异常体系重组或命令协议调整。

## 结论

本次设计选择在现有 [`nonebot_plugin_zikequote3/msgtexts/`](nonebot_plugin_zikequote3/msgtexts/) 机制上继续推进纯文本统一，保留 [`nonebot_plugin_zikequote3/templates/`](nonebot_plugin_zikequote3/templates/) 作为 HTML 与图片主模板边界，采用“按业务域逐步提取 + 在各业务子目录 [`__init__.py`](nonebot_plugin_zikequote3/msgtexts/general/__init__.py) 中提供小型包装函数”的方式落地。

这样做可以在不改变主渲染架构的前提下，逐步把纯文本文案从命令文件中剥离出来，形成稳定、可复用、可测试的统一管理结构，并把本次变更严格限制在已确认范围内。
