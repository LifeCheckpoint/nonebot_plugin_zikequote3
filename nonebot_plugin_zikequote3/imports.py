from dataclasses import asdict
from datetime import datetime
from nonebot import on_command, on_message, get_plugin_config, require, get_driver, logger
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupME, MessageSegment as MsgSeg, Bot
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ArgPlainText
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
import nonebot_plugin_localstore as store
from pathlib import Path
import tomlkit
from typing import Optional, Union, Literal, Callable, Any, Dict, List, Tuple
import asyncio
import colorsys
import json
import random
import requests

# 插件根目录
_plugin_root = Path(__file__).parent
_module_database_root = _plugin_root / "database"
_module_html_templates_root = _plugin_root / "templates"

# 载入全局数据库对象
from .database.connection_manager import ConnectionManager
db_path = store.get_data_dir("ZikeQuote3") / "zikequote3.db"
db = ConnectionManager(db_path)
db.initialize_db() # 初始化，保证完整性

from .utils.async_tools import serial_execution, async_modify_lock
from .external.html_render import full_render_html, template, full_render_markdown
from .external.msg_text import msend, mfinish

# 加载 toml 配置并注入 BaseModel
from .config import ConfigPath, load_config_from_toml
cfg_file = get_plugin_config(ConfigPath).config_toml
if not Path(cfg_file).is_file():
    logger.error(f"配置文件 {cfg_file} 不存在")
    raise FileNotFoundError(f"配置文件 {cfg_file} 不存在")
_cfg_toml = tomlkit.parse(Path(cfg_file).read_text(encoding="utf-8"))
cfg = load_config_from_toml(_cfg_toml)

# 加载消息导入
from .message_text import *