"""
命令参数解析辅助子包。

提供 Alconna 相关类型的统一导入以及自定义数据类型解析工具。
"""

from nonebot_plugin_alconna import Query
from arclet.alconna import Alconna, Args, AllParam
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_alconna.uniseg.segment import At

from .query_resolver import (
    NumericDisambiguation,
    QueryIntent,
    QueryResolver,
    ResolvedQuery,
    ResolveStrategy,
    STRATEGY_RANDOM_QUOTE,
    STRATEGY_RANKING,
    STRATEGY_SEARCH_QUOTE,
    STRATEGY_USER_LOOKUP,
    extract_at_qq,
    extract_text,
)
