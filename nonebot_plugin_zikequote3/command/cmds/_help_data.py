"""
帮助命令的默认数据构建。

包含所有命令定义数据，属于业务逻辑层而非模板关注点。
"""

from __future__ import annotations

from ...templates.schema.help import (
    HelpCategoryData,
    HelpCommandItem,
    TemplateHelpData,
)


def build_default_help_data() -> TemplateHelpData:
    """
    构建默认的帮助文档数据（基于源码中的命令定义）。

    :returns: 填充了所有命令信息的帮助文档数据
    :rtype: TemplateHelpData
    """
    return TemplateHelpData(
        title="语录插件使用帮助",
        query_note=(
            "🔍 标有「统一查询」的命令支持多种查询方式："
            "@某人、QQ号、昵称片段、关键词、语录ID。"
            "无参数时部分命令默认查询自己。"
        ),
        categories=[
            HelpCategoryData(
                name="语录查询与浏览",
                icon="📖",
                commands=[
                    HelpCommandItem(
                        name="/语录",
                        aliases=["随机语录", "名人名言", "群友语录"],
                        description="随机抽取一条语录，支持按用户、关键词或语录ID筛选",
                        usage="/语录 [查询内容]",
                        examples=[
                            "/语录 → 随机一条",
                            "/语录 @某人 → 该用户的随机语录",
                            "/语录 42 → 语录ID为42的语录",
                            "/语录 摸鱼 → 含「摸鱼」的随机语录",
                        ],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/语录卡",
                        aliases=["语录卡片", "语录card"],
                        description="以卡片形式展示随机语录",
                        usage="/语录卡 [查询内容]",
                        examples=["/语录卡 @某人"],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/语录图",
                        aliases=["语录原图", "语录图片"],
                        description="随机获取一条含图片的语录原图",
                        usage="/语录图 [查询内容]",
                        examples=["/语录图 @某人"],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/查语录",
                        aliases=["搜索语录", "搜语录", "找语录"],
                        description="按关键词搜索语录，支持正则、模糊语义搜索等高级选项",
                        usage="/查语录 [关键词] [@某人] [-qq QQ号] [-m 最大条数] [-ni 不含图片] [-r 正则模式] [-f 模糊搜索] [-s 相似度] [-n 返回条数]",
                        examples=[
                            "/查语录 摸鱼 → 搜索含「摸鱼」的语录",
                            "/查语录 摸鱼 @某人 → 筛选该用户",
                            "/查语录 -r ^你好.* → 正则搜索",
                            "/查语录 摸鱼 -ni -m 10 → 排除图片，最多10条",
                            "/查语录 -f 开心的事 → 模糊语义搜索",
                            "/查语录 -f 开心的事 -s 0.5 -n 3 → 相似度≥0.5，返回前3条",
                        ],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/模糊查语录",
                        aliases=["查模糊语录"],
                        description="基于语义相似度的模糊搜索，需配置 Embedding 服务",
                        usage="/模糊查语录 [关键词] [@某人] [-qq QQ号] [-ni 不含图片] [-s 相似度] [-n 返回条数]",
                        examples=[
                            "/模糊查语录 开心的事 → 语义搜索相关语录",
                            "/模糊查语录 想吃火锅 -s 0.5 → 相似度≥0.5",
                            "/模糊查语录 3 周末去哪玩 → 返回前3条结果",
                            "/模糊查语录 0.6 有趣的对话 → 相似度≥0.6",
                        ],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/语录列表",
                        aliases=["语录list", "列语录", "个人语录"],
                        description="查看用户的语录列表，支持查询范围",
                        usage="/语录列表 [页码/范围] [用户]",
                        examples=[
                            "/语录列表 → 自己的语录",
                            "/语录列表 @某人 → 该用户的语录",
                            "/语录列表 2 → 第2条开始",
                            "/语录列表 2-5 → 第2到5条",
                        ],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/最近语录",
                        aliases=[],
                        description="浏览当前群最近新增的语录，只支持数量参数",
                        usage="/最近语录 [数量]",
                        examples=[
                            "/最近语录 → 默认展示最近 3 条",
                            "/最近语录 6 → 展示最近 6 条",
                            "/最近语录 20 → 实际展示最近 10 条",
                        ],
                        query_support=False,
                    ),
                ],
            ),
            HelpCategoryData(
                name="语录收集与管理",
                icon="✏️",
                commands=[
                    HelpCommandItem(
                        name="/加语录",
                        aliases=["添加语录", "新增语录"],
                        description="回复一条消息将其添加为语录（支持文字和图片）",
                        usage="回复消息 + /加语录",
                        examples=["[回复某条消息] /加语录"],
                    ),
                    HelpCommandItem(
                        name="/加语录图",
                        aliases=["加语录图片", "语录加图"],
                        description="为已有语录附加图片",
                        usage="回复消息 + /加语录图 + 图片",
                    ),
                    HelpCommandItem(
                        name="/删语录",
                        aliases=["删除语录"],
                        description="删除一条语录，可回复语录消息或指定ID",
                        usage="/删语录 [语录ID] 或 回复语录消息 + /删语录",
                        examples=[
                            "/删语录 42",
                            "[回复语录消息] /删语录",
                        ],
                    ),
                    HelpCommandItem(
                        name="/语录去重",
                        aliases=[],
                        description="清理当前群重复的纯文本语录，默认作用于全群，可用 --user_only 仅处理自己的语录",
                        usage="/语录去重 [--user_only]",
                        examples=[
                            "/语录去重",
                            "/语录去重 --user_only",
                        ],
                        permission="默认需要删除他人语录权限；使用 --user_only 时需要删除自己语录权限",
                    ),
                    HelpCommandItem(
                        name="/删语录图",
                        aliases=["删语录图片", "移除语录图"],
                        description="移除语录附带的图片",
                        usage="回复消息 + /删语录图",
                    ),
                    HelpCommandItem(
                        name="/评语录",
                        aliases=["评论语录", "评价语录"],
                        description="回复语录消息添加评论（也可直接回复语录消息输入评论）",
                        usage="回复语录消息 + /评语录 评论内容",
                        examples=["[回复语录消息] /评语录 说得好"],
                    ),
                    HelpCommandItem(
                        name="/删评论",
                        aliases=["删除评论", "删语评"],
                        description="删除一条语录评论",
                        usage="/删评论 评论ID",
                        examples=["/删评论 abc123"],
                    ),
                ],
            ),
            HelpCategoryData(
                name="用户与统计",
                icon="📊",
                commands=[
                    HelpCommandItem(
                        name="/语录用户信息",
                        aliases=["语录用户", "语录作者", "作者信息"],
                        description="查看用户的语录统计信息",
                        usage="/语录用户信息 [用户]",
                        examples=[
                            "/语录用户信息 → 自己的信息",
                            "/语录用户信息 @某人",
                        ],
                        query_support=True,
                    ),
                    HelpCommandItem(
                        name="/语录排行",
                        aliases=["语录排行榜", "语录统计", "语录rank"],
                        description="查看群语录排行榜和近15天走势",
                        usage="/语录排行 [显示人数]",
                        examples=[
                            "/语录排行 → 默认排行",
                            "/语录排行 10 → 显示前10名",
                        ],
                    ),
                ],
            ),
            HelpCategoryData(
                name="语录更新",
                icon="🔄",
                commands=[
                    HelpCommandItem(
                        name="/语录强制更新",
                        aliases=["更新语录", "刷新语录"],
                        description="手动触发 LLM 语录收集流程",
                        usage="/语录强制更新",
                        permission="权限节点控制",
                    ),
                ],
            ),
            HelpCategoryData(
                name="配置管理",
                icon="⚙️",
                commands=[
                    HelpCommandItem(
                        name="/查看语录配置",
                        aliases=["当前语录设置", "查看语录设置"],
                        description="查看当前群组的插件配置",
                        usage="/查看语录配置",
                        permission="权限节点控制",
                    ),
                    HelpCommandItem(
                        name="/修改语录配置",
                        aliases=["修改语录设置", "设置语录配置"],
                        description="修改当前群组的单项配置",
                        usage="/修改语录配置 配置项 新值",
                        examples=["/修改语录配置 showcase.max_rank_user_num 20"],
                        permission="权限节点控制",
                    ),
                ],
            ),
            HelpCategoryData(
                name="其他",
                icon="📌",
                commands=[
                    HelpCommandItem(
                        name="/语录隐私政策",
                        aliases=["语录隐私", "语录政策"],
                        description="查看语录插件的隐私政策",
                        usage="/语录隐私政策",
                    ),
                    HelpCommandItem(
                        name="/迁移群语录",
                        aliases=["迁移所有群语录", "移动群语录"],
                        description="将语录从一个群迁移到另一个群",
                        usage="/迁移群语录 源群号 目标群号 [选项]",
                        examples=[
                            "/迁移群语录 123456 789012",
                            "/迁移群语录 123456 789012 -o -d",
                        ],
                        permission="权限节点控制",
                    ),
                    HelpCommandItem(
                        name="/重建语录索引",
                        aliases=["语录重建索引", "重建索引"],
                        description="重建当前群的模糊搜索向量索引，模型切换后需执行",
                        usage="/重建语录索引 [--all 所有群]",
                        examples=[
                            "/重建语录索引 → 重建当前群的索引",
                            "/重建语录索引 --all → 重建所有群的索引",
                        ],
                        permission="权限节点控制",
                    ),
                ],
            ),
        ],
    )
