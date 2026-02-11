"""
命令使用帮助模板渲染方法。

提供命令帮助文档的数据模型与 HTML 渲染方法。
"""
from typing import List
from pydantic import BaseModel

from ..registry import HELP, render_with_spec


class HelpCommandItem(BaseModel):
    """
    单个命令的帮助信息。

    :param name: 命令名，如 "/语录列表"
    :type name: str
    :param aliases: 别名列表
    :type aliases: List[str]
    :param description: 简要描述
    :type description: str
    :param usage: 使用格式
    :type usage: str
    :param examples: 使用示例
    :type examples: List[str]
    :param permission: 权限要求
    :type permission: str
    :param query_support: 是否支持统一查询
    :type query_support: bool
    """

    name: str
    aliases: List[str] = []
    description: str
    usage: str
    examples: List[str] = []
    permission: str = "所有人"
    query_support: bool = False


class HelpCategoryData(BaseModel):
    """
    命令分类。

    :param name: 分类名
    :type name: str
    :param icon: emoji 图标
    :type icon: str
    :param commands: 命令列表
    :type commands: List[HelpCommandItem]
    """

    name: str
    icon: str
    commands: List[HelpCommandItem]


class TemplateHelpData(BaseModel):
    """
    帮助文档模板数据。

    :param title: 标题
    :type title: str
    :param version: 版本号
    :type version: str
    :param categories: 命令分类列表
    :type categories: List[HelpCategoryData]
    :param query_note: 统一查询方式说明文本
    :type query_note: str
    """

    title: str = "语录插件使用帮助"
    version: str = ""
    categories: List[HelpCategoryData] = []
    query_note: str = ""


def render_help(data: TemplateHelpData) -> str:
    """
    渲染命令帮助文档 HTML。

    :param data: 帮助文档渲染数据
    :type data: TemplateHelpData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    return render_with_spec(HELP, **data.model_dump())


__all__ = [
    "HelpCommandItem",
    "HelpCategoryData",
    "TemplateHelpData",
    "render_help",
]
