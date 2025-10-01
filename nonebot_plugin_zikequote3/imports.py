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
import tomlkit
from typing import Optional, Union, Literal, Callable, Any, Dict, List, Tuple
import asyncio
import colorsys
import json
import random
import requests

from .interface.permission import quote_permission, is_quote_manager
from .utils.async_tools import serial_execution, async_modify_lock
from .external.html_render import full_render_html, template, full_render_markdown
from .external.msg_text import msend, mfinish

# 加载配置
from .config import Config
cfg_file = get_plugin_config(Config).config_toml
if not Path(cfg_file).is_file():
    logger.error(f"配置文件 {cfg_file} 不存在")
    raise FileNotFoundError(f"配置文件 {cfg_file} 不存在")
cfg = tomlkit.parse(Path(cfg_file).read_text(encoding="utf-8"))

# 其它信息
_plugin_root: Path = Path(__file__).parent

from .message_text import *