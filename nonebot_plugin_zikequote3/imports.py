from dataclasses import asdict
from datetime import datetime
from nonebot import on_command, on_message, get_plugin_config, require, get_driver, logger
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupME, MessageSegment as MsgSeg, Bot
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ArgPlainText
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Union, Literal, Callable, Any, Dict, List, Tuple, Sequence
import asyncio
import click
import colorsys
import random
import requests
import sentry_sdk
import tomlkit
import typer


# 插件目录配置
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store
from .paths import PluginPath


# 载入全局数据库对象
from .database.connection_manager import ConnectionManager
db = ConnectionManager(PluginPath.data_db_path)
db.initialize_db() # 初始化，保证完整性


# 载入图像存储管理器
from .database.image_store import ImageStore
qimg_store = ImageStore(PluginPath.data_image_root)


# HTML 截图工具
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import (
    get_new_page,
    md_to_pic,
    template_to_pic,
    text_to_pic,
)
from .html_capture import html_img_render


# 异常上报与日志工具
from .utils.error_report import service_exception, service_exception_a, event_exception_a, event_exception, event_exception_failmsg_a

# 载入命令解析工具
require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import on_alconna, Match


# 响应等待工具
require("nonebot_plugin_waiter")
import nonebot_plugin_waiter as waiter


# 权限配置插件载入与权限服务创建
require("nonebot_plugin_access_control_api")
from nonebot_plugin_access_control_api.service import create_plugin_service
from .services.permission_management.permission_node_definition import PermissionServiceNodes
perm_nodes = PermissionServiceNodes(create_plugin_service("zikequote3"))


# Token 生成器
from .utils.token_generate import TokenManager
token_manager = TokenManager()


# 加载 toml 配置并注入 BaseModel
from .config import reload_config, ConfigPath
_default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()
# 允许热更新配置
def notify_reload_config():
    global _default_cfg_toml, default_cfg, _cfg_toml, cfg
    _default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()


# 配置 sentry
from .utils.sentry_init import init_sentry
init_sentry(sentry_dsn_path=default_cfg.sentry.dsn_path)


# 加载消息导入
from . import msgtexts