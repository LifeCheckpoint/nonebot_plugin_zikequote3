# nonebot-plugin-zikequote3 审计修复设计文档

## 背景

上游审计已经确认该项目存在 10 个需要处理的问题，且修复方向已经统一为“方案 B：中度重构，优先统一契约与生命周期模型”。本设计文档只整理已经批准的事实与实施边界，供后续实现与回归验证使用。

本次设计覆盖的问题与链路，主要涉及长交互迁移命令、数据库会话生命周期、权限约束、配置解析、重复收集策略、向量检索可选能力、历史库兼容性，以及测试基座的隔离与断言收紧。对应的审计背景可参见 [`docs/audit-report.md`](docs/audit-report.md)。

## 目标与非目标

### 目标

- 本设计以 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 为中心，重新划定长交互命令的阶段边界、事务边界与一致性契约。
- 本设计统一 [`inject()`](nonebot_plugin_zikequote3/di/inject.py:109)、[`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 与迁移命令链路之间的生命周期关系，避免请求级依赖跨越人工确认窗口。
- 本设计收紧删除权限、配置读取、重复收集与向量依赖的契约表达，让命令层、服务层与 DI 装配层对同一事实保持一致。
- 本设计在不引入破坏性迁移的前提下，提升历史数据库识别能力，并为后续修改提供稳定的测试基座与分层回归策略。

### 非目标

- 本设计不推翻当前全局 DI 框架，也不把所有请求级依赖统一改成新的生命周期模型。
- 本设计不改变现有命令入口名称与主要交互流程；对外可见变化仅限于把原本隐含的错误状态显式暴露出来。
- 本设计不引入新的业务能力、迁移入口或额外的管理员操作流程。
- 本设计不包含任何未获批准的新方案，也不扩展审计范围之外的重构目标。

## 约束

- 后续实现只能修改与本设计直接相关的既有链路，重点路径包括 [`group_migration.py`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34)、[`migration_service.py`](nonebot_plugin_zikequote3/services/migration_service.py:164)、[`config_service.py`](nonebot_plugin_zikequote3/services/config_service.py:323)、[`quote_write_service.py`](nonebot_plugin_zikequote3/services/quote_write_service.py:242) 与 [`review_service.py`](nonebot_plugin_zikequote3/services/review_service.py:134)。
- 数据库兼容方案必须维持 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:120) 的既有自动升级主路径，不能引入新的破坏性迁移要求。
- 设计必须保持与当前命令接口兼容，尤其不能改变 [`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127)、[`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164) 以及群迁移命令的外部入口形态。
- 所有修改都需要以测试基座收紧与关键契约测试先行为前提，避免在脆弱测试环境上直接推进主逻辑改动。

## 现状问题摘要

### 长交互迁移链路存在生命周期与一致性错位

[`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 当前会在一次长交互中先生成迁移预览，再等待用户确认，最后执行真正写入。与此同时，[`inject()`](nonebot_plugin_zikequote3/di/inject.py:109) 与 [`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 采用的 REQUEST 生命周期会覆盖整个处理过程，导致数据库会话与事务可能跨越最长 60 秒的等待窗口。

[`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 还会在执行阶段重新从数据库推导迁移计划，而不是消费确认时展示给用户的同一份结果。这样一来，用户确认的对象集合与最终写入的对象集合可能不一致。

### 权限、配置与收集链路的契约表达不统一

删除语录与删除评论的命令入口，当前仍然依赖粗粒度权限路由，服务层缺少基于操作者上下文与资源归属的二次校验。对应问题集中体现在 [`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127)、[`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164)、[`delete_quote()`](nonebot_plugin_zikequote3/services/quote_write_service.py:242) 与 [`delete_review()`](nonebot_plugin_zikequote3/services/review_service.py:134)。

配置修改与配置读取两条链路，也存在“输入模型、解析模型与诊断结果”三者不一致的问题。[`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96) 会提前截断带空格的合法值，[`get_parsed_config()`](nonebot_plugin_zikequote3/services/config_service.py:323) 则会在坏配置出现时静默回退，削弱诊断信号。

收集闭环与向量检索依赖也存在类似问题。[`handle_collecting_listener()`](nonebot_plugin_zikequote3/command/cmds/collecting_listener_cmd.py:29) 与 [`handle_update_quote_force()`](nonebot_plugin_zikequote3/command/cmds/update_quote_force_cmd.py:22) 没有把是否允许重复的配置显式传入 [`collect_and_finalize()`](nonebot_plugin_zikequote3/services/quote_collection_service.py:373)；[`VectorProvider`](nonebot_plugin_zikequote3/di/providers/vector_provider.py:23) 相关能力则在 DI 层声明为具体服务，却在运行时可能返回空值，导致契约与真实状态脱节。

### 数据库兼容与测试基座不足以支撑后续收敛

[`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38) 当前对 SQLite 的文件库与内存库没有作足够清晰的连接策略区分，文件型库仍可能复用单物理连接，从而放大事务边界问题。

[`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 对未版本化数据库的历史形态识别过严，无法兼容 [`docs/legacy/v1_to_v2.sql`](docs/legacy/v1_to_v2.sql:1) 所产生的官方旧库形态。

[`tests/unit/conftest.py`](tests/unit/conftest.py:100) 代表的测试基座还存在数据库状态跨用例泄漏的问题，而 [`test_get_quotes_by_author()`](tests/unit/repositories/test_quote_repository.py:164) 一类宽松断言又难以及时暴露污染与漂移。

## 总体设计

### 设计原则

- 设计以“中度重构，优先统一契约与生命周期模型”为唯一方案，不扩大到全局架构重写。
- 设计优先处理高风险链路上的事实错位问题，包括用户确认与执行对象不一致、事务边界跨等待窗口、服务声明与真实依赖可用性不一致。
- 设计尽量维持外部接口稳定，把必要变化控制在错误显式化、约束显式化与阶段边界显式化三个方面。

### 核心思路

整体收敛点放在长交互命令链路，而不是先推翻整个 DI 框架。具体来说，[`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 会被拆成“预览阶段 / 用户确认等待 / 执行阶段”三个显式阶段。

预览阶段只负责构造确认所需数据，不把数据库会话带入等待阶段。用户确认等待期间不持有数据库会话，也不延续 REQUEST 生命周期下的事务。执行阶段在确认后重新进入独立事务，并且只消费预览阶段产出的显式迁移快照。

与此配套，[`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 的职责从“执行前重新推导用户意图”调整为“消费显式迁移快照并做一致性校验”。如果确认后底层数据已经变化，执行阶段会中止并提示用户重新预览，从而避免出现“确认 A、执行 B”的情况。

数据库、权限、配置、可选依赖与测试基座的改动，全部围绕这一原则展开：每一条链路都需要让声明的契约与实际行为保持一致，并让生命周期边界尽量短、尽量清晰、尽量可验证。

## 分领域设计

### 整体架构、事务边界与群迁移契约

#### 长交互迁移流程拆分为三个显式阶段

[`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 将被拆分为预览阶段、用户确认等待阶段与执行阶段。

- 预览阶段负责读取源群与目标群状态、计算迁移范围、生成确认所需的展示内容，并产出一份显式迁移快照。
- 用户确认等待阶段只持有与确认流程相关的轻量数据，不再持有数据库会话，也不保留跨等待窗口的事务上下文。
- 执行阶段在用户确认后重新进入独立事务，并以预览阶段产出的迁移快照作为唯一输入依据。

这种拆分不会改变当前命令入口与主要交互形态，但会收紧内部生命周期模型，使数据库访问集中在短事务窗口中。

#### REQUEST 生命周期不再跨越 60 秒等待窗口

[`inject()`](nonebot_plugin_zikequote3/di/inject.py:109) 与 [`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 的现有 REQUEST 生命周期不再跨越确认等待阶段。优先做法不是重写 DI 框架，而是让 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 只在各阶段内部解析和使用依赖。

这个调整意味着依赖解析会从“整条长交互只解析一次”转向“每个短阶段单独解析并单独释放”。数据库会话只存在于预览阶段和执行阶段的短生命周期内，等待阶段不再占用连接与事务。

#### 迁移执行改为消费显式快照并执行一致性校验

[`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 将不再根据执行时的数据库状态重新推导迁移计划，而是消费预览阶段产出的显式迁移快照，并在写入前检查快照与当前数据库状态是否仍然一致。

一致性校验的结论只有两类：

- 如果关键对象集合仍与预览阶段一致，执行阶段继续完成迁移。
- 如果确认后底层数据已经漂移，执行阶段立即中止，并明确提示用户重新预览。

这个契约调整把原本隐含的检查时与使用时不一致问题显式化，但不改变命令的外部用途。

#### SQLite 连接策略与短事务模型配套收敛

[`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38) 对 SQLite 的策略会配合迁移链路一并收敛。文件型数据库不再复用单物理连接，以免多请求共享同一连接后放大事务边界与锁竞争问题。

这个变化与群迁移命令的短事务改造相互配套。命令层收紧阶段边界之后，数据库层也需要提供更清晰的连接边界，才能让新的生命周期模型真正成立。

#### 对外兼容性保持稳定

命令入口与大体交互保持不变。用户可感知的主要变化只有一项：确认后如果底层数据发生漂移，系统会明确要求重新预览，而不是继续执行不再匹配确认内容的写入。这项变化属于把错误显式化，不属于新增功能。

### 权限、配置、可选依赖与收集契约

#### 删除权限采用命令入口与服务层双重约束

[`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127) 与 [`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164) 将按照 self 与 others 的差异细分权限路由。命令入口会继续承担第一层权限分流职责。

与此同时，[`delete_quote()`](nonebot_plugin_zikequote3/services/quote_write_service.py:242) 与 [`delete_review()`](nonebot_plugin_zikequote3/services/review_service.py:134) 将新增操作者上下文与资源归属校验。这样一来，即使调用绕过命令入口，服务层仍能拒绝越权删除。

双重约束的重点不在于增加复杂度，而在于让权限模型真正覆盖所有入口，而不是只依赖命令路由的单点防线。

#### 配置链路改为显式诊断与兼容读取

[`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96) 不再先按空格截断值，而是先把键名与原始值分离，再交给 [`parse_config_param()`](nonebot_plugin_zikequote3/services/config_service.py:397) 解析。这样可以保留带空格的合法字符串值，使命令输入模型与服务解析模型保持一致。

读取侧的 [`get_parsed_config()`](nonebot_plugin_zikequote3/services/config_service.py:323) 不再静默吞掉坏配置，而是返回带诊断信息的结果。对现有调用方，系统保留兼容访问入口，以减少一次性改动面。

启动期的 [`fix_config_integrity()`](nonebot_plugin_zikequote3/services/config_service.py:425) 将真正把损坏配置修正为可用状态，而不是只记录 warning 后跳过。这样可以让“读取兼容”与“启动修复”形成闭环。

#### 重复收集策略从隐式默认改为显式决策

[`handle_collecting_listener()`](nonebot_plugin_zikequote3/command/cmds/collecting_listener_cmd.py:29) 与 [`handle_update_quote_force()`](nonebot_plugin_zikequote3/command/cmds/update_quote_force_cmd.py:22) 必须把配置解析结果显式传入 [`collect_and_finalize()`](nonebot_plugin_zikequote3/services/quote_collection_service.py:373)。

对应的服务签名不再继续依赖危险默认值。这样可以确保“配置默认不允许重复”这一事实，能够完整进入自动收集与强制更新两条链路，而不是在服务调用边界被隐式覆盖。

#### 向量检索能力采用稳定的可选契约

[`VectorProvider`](nonebot_plugin_zikequote3/di/providers/vector_provider.py:23) 当前以“声明返回具体服务，实际却可能返回空值”的方式破坏了 DI 契约。中度重构下，系统将引入一个稳定的可选能力契约，用来统一表达“能力可用”与“能力不可用但类型仍稳定”这两种状态。

[`create_container()`](nonebot_plugin_zikequote3/di/container.py:23)、[`provide_quote_write_service()`](nonebot_plugin_zikequote3/di/providers/service_provider.py:221)、[`handle_fuzzy_search_quote()`](nonebot_plugin_zikequote3/command/cmds/fuzzy_search_quote_cmd.py:63) 与 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 都将基于同一抽象工作，而不再在不同位置重复手工判空。

这个设计只收敛契约表达，不新增向量功能，也不改变向量能力缺失时对外表现为不可用的事实。

### 数据库历史兼容、测试基座与回归验证策略

#### 历史数据库兼容保持在现有迁移主路径内

历史库兼容方案不引入破坏性迁移。[`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 将从“严格表集合全等”调整为“允许识别官方旧脚本生成的受支持历史形态”。

这个调整需要把 [`docs/legacy/v1_to_v2.sql`](docs/legacy/v1_to_v2.sql:1) 产生的缺失表场景纳入兼容判定。数据库一旦被识别为受支持的历史形态，升级流程仍然走 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:120) 的既有主路径，对外保持自动化。

#### 测试基座收紧数据库生命周期与断言精度

[`tests/unit/conftest.py`](tests/unit/conftest.py:100) 所代表的单元测试基座将不再让 session 级共享数据库状态跨用例泄漏。后续实现需要把数据库生命周期与事务隔离收紧到更细粒度，使每个测试用例拥有更独立的状态边界。

同时，像 [`test_get_quotes_by_author()`](tests/unit/repositories/test_quote_repository.py:164) 这类“至少一条即可”的宽松断言，也需要改为能够识别污染与集合漂移的精确断言。只有在测试结果可重复、可定位时，后续主逻辑收敛才有可靠基础。

#### 回归验证按三层组织

回归验证将按三层组织：

- 第一层覆盖高风险契约，重点验证 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 与 [`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 的预览、确认与执行一致性。
- 第二层覆盖基础设施边界，重点验证 [`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38) 的 SQLite 行为，以及 [`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 对历史库的识别结果。
- 第三层覆盖业务回归，重点验证删除权限、配置解析、重复语录策略，以及向量能力缺失时的行为是否仍符合统一契约。

这种分层策略的目标，是先稳住最容易造成破坏性后果的高风险契约，再逐层验证基础设施与业务行为。

## 实施顺序

后续实施按以下顺序推进：

1. 先收紧 [`tests/unit/conftest.py`](tests/unit/conftest.py:100) 代表的测试基座，并补齐关键契约测试，让迁移链路与基础设施边界具备可靠回归支撑。
2. 随后处理群迁移与事务边界问题，重点落在 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34)、[`inject()`](nonebot_plugin_zikequote3/di/inject.py:109)、[`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 与 [`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 的契约收敛上。
3. 然后处理数据库历史兼容问题，重点落在 [`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38)、[`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 与 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:120) 的边界调整上。
4. 在迁移链路与数据库边界稳定后，再依次处理权限与收集契约问题，包括 [`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127)、[`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164)、[`delete_quote()`](nonebot_plugin_zikequote3/services/quote_write_service.py:242)、[`delete_review()`](nonebot_plugin_zikequote3/services/review_service.py:134) 与 [`collect_and_finalize()`](nonebot_plugin_zikequote3/services/quote_collection_service.py:373)。
5. 最后处理配置与向量依赖契约问题，重点落在 [`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96)、[`parse_config_param()`](nonebot_plugin_zikequote3/services/config_service.py:397)、[`get_parsed_config()`](nonebot_plugin_zikequote3/services/config_service.py:323)、[`fix_config_integrity()`](nonebot_plugin_zikequote3/services/config_service.py:425) 与 [`VectorProvider`](nonebot_plugin_zikequote3/di/providers/vector_provider.py:23) 的统一表达上。

## 测试策略

### 关键契约测试

- 需要围绕 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34) 与 [`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 建立成组测试，验证预览阶段生成的快照可以被执行阶段消费，且确认后的数据漂移会触发中止与重新预览提示。
- 需要验证 [`inject()`](nonebot_plugin_zikequote3/di/inject.py:109) 与 [`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 不再让数据库会话跨越等待阶段存在。

### 基础设施边界测试

- 需要验证 [`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38) 在文件型 SQLite 下不再复用单物理连接，同时保留符合既有预期的 SQLite 支持行为。
- 需要验证 [`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 可以识别由 [`docs/legacy/v1_to_v2.sql`](docs/legacy/v1_to_v2.sql:1) 形成的受支持历史形态，并继续通过 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:120) 完成升级。

### 业务回归测试

- 需要验证 [`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127) 与 [`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164) 的路由约束，与 [`delete_quote()`](nonebot_plugin_zikequote3/services/quote_write_service.py:242) 和 [`delete_review()`](nonebot_plugin_zikequote3/services/review_service.py:134) 的服务层归属校验可以共同阻断越权删除。
- 需要验证 [`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96)、[`parse_config_param()`](nonebot_plugin_zikequote3/services/config_service.py:397)、[`get_parsed_config()`](nonebot_plugin_zikequote3/services/config_service.py:323) 与 [`fix_config_integrity()`](nonebot_plugin_zikequote3/services/config_service.py:425) 形成完整的配置输入、诊断与修复闭环。
- 需要验证 [`handle_collecting_listener()`](nonebot_plugin_zikequote3/command/cmds/collecting_listener_cmd.py:29)、[`handle_update_quote_force()`](nonebot_plugin_zikequote3/command/cmds/update_quote_force_cmd.py:22) 与 [`collect_and_finalize()`](nonebot_plugin_zikequote3/services/quote_collection_service.py:373) 在“是否允许重复”这一配置上的行为完全一致。
- 需要验证 [`create_container()`](nonebot_plugin_zikequote3/di/container.py:23)、[`provide_quote_write_service()`](nonebot_plugin_zikequote3/di/providers/service_provider.py:221)、[`handle_fuzzy_search_quote()`](nonebot_plugin_zikequote3/command/cmds/fuzzy_search_quote_cmd.py:63) 与 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 在向量能力缺失时仍保持类型稳定与行为可预期。

## 风险与兼容性

- 群迁移链路的主要兼容性风险在于，部分用户会在确认后遇到“需要重新预览”的新提示。但这个变化源于一致性校验被显式化，属于风险暴露更清晰，而不是流程能力变弱。
- SQLite 连接策略调整后，请求之间的连接共享方式会改变，因此需要依赖基础设施层测试确认事务边界与并发行为符合预期。
- 配置读取改为显式诊断后，部分原本被默认值掩盖的坏配置会更早暴露。为避免影响可用性，[`fix_config_integrity()`](nonebot_plugin_zikequote3/services/config_service.py:425) 需要与兼容读取入口配合落地。
- 权限模型增加服务层校验后，任何绕过命令入口的旧调用路径都必须显式传入操作者上下文，否则删除链路将无法继续沿用旧的隐式假设。
- 向量能力改为稳定的可选契约后，上层调用的分支判断方式会变化，但能力可用与不可用的对外语义保持不变。
- 历史数据库识别扩展后，需要严格控制兼容范围，只覆盖已经确认的官方旧脚本历史形态，避免把未知结构误判为受支持数据库。

## 待实现清单

- 需要按三阶段模型重构 [`handle_group_migration()`](nonebot_plugin_zikequote3/command/cmds/group_migration.py:34)，并同步调整 [`execute_migration()`](nonebot_plugin_zikequote3/services/migration_service.py:164) 的输入契约与一致性校验逻辑。
- 需要收紧 [`inject()`](nonebot_plugin_zikequote3/di/inject.py:109) 与 [`provide_session()`](nonebot_plugin_zikequote3/di/providers/database_provider.py:57) 在群迁移链路中的使用方式，确保等待阶段不再持有数据库会话。
- 需要调整 [`create_async_engine_factory()`](nonebot_plugin_zikequote3/database/sa/engine.py:38) 的 SQLite 文件库连接策略，并补齐相应测试。
- 需要重构 [`matcher_remove_quote`](nonebot_plugin_zikequote3/command/command_definition.py:127)、[`matcher_remove_quote_comment`](nonebot_plugin_zikequote3/command/command_definition.py:164)、[`delete_quote()`](nonebot_plugin_zikequote3/services/quote_write_service.py:242) 与 [`delete_review()`](nonebot_plugin_zikequote3/services/review_service.py:134) 的权限契约。
- 需要调整 [`handle_modify_config()`](nonebot_plugin_zikequote3/command/cmds/config_cmd.py:96)、[`parse_config_param()`](nonebot_plugin_zikequote3/services/config_service.py:397)、[`get_parsed_config()`](nonebot_plugin_zikequote3/services/config_service.py:323) 与 [`fix_config_integrity()`](nonebot_plugin_zikequote3/services/config_service.py:425) 的配置链路。
- 需要让 [`handle_collecting_listener()`](nonebot_plugin_zikequote3/command/cmds/collecting_listener_cmd.py:29)、[`handle_update_quote_force()`](nonebot_plugin_zikequote3/command/cmds/update_quote_force_cmd.py:22) 与 [`collect_and_finalize()`](nonebot_plugin_zikequote3/services/quote_collection_service.py:373) 围绕重复收集策略形成显式决策闭环。
- 需要为 [`VectorProvider`](nonebot_plugin_zikequote3/di/providers/vector_provider.py:23) 相关链路建立稳定的可选能力契约，并统一 [`create_container()`](nonebot_plugin_zikequote3/di/container.py:23)、[`provide_quote_write_service()`](nonebot_plugin_zikequote3/di/providers/service_provider.py:221)、[`handle_fuzzy_search_quote()`](nonebot_plugin_zikequote3/command/cmds/fuzzy_search_quote_cmd.py:63) 与 [`handle_rebuild_index()`](nonebot_plugin_zikequote3/command/cmds/rebuild_index_cmd.py:56) 的使用方式。
- 需要扩展 [`_detect_database_state()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:87) 对官方历史库形态的兼容识别，并维持 [`migrate_database_to_head()`](nonebot_plugin_zikequote3/database/alembic_runtime.py:120) 作为唯一升级主路径。
- 需要收紧 [`tests/unit/conftest.py`](tests/unit/conftest.py:100) 的数据库生命周期隔离，并收紧 [`test_get_quotes_by_author()`](tests/unit/repositories/test_quote_repository.py:164) 等测试的断言精度。
