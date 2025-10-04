from .imports import *

__plugin_meta__ = PluginMetadata(
    name="ZikeQuote3",
    description="LLM 介入，功能丰富的群聊语录自动收集与管理插件，支持自动收集、后台管理、生成排行榜、展示等功能",
    usage="""
ZikeQuote3 基于 NoneBot 开发，便于群聊语录自动收集与管理，支持通过 LLM 自动收集群聊消息作为语录、手动管理语录、以及多种方式查看等功能。
    """,
    type="application",
    homepage="https://github.com/LifeCheckpoint/nonebot_plugin_zikequote3",
    config=ConfigPath,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "LifeCheckpoint",
        "version": "0.4.0alpha1",
    },
)

from .command import *