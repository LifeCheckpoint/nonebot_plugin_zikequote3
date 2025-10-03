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
from typing import Optional, Union, Literal, Callable, Any, Dict, List, Tuple
import asyncio
import colorsys
import nonebot_plugin_localstore as store
import random
import requests
import tomlkit

# 插件根目录
_plugin_root = Path(__file__).parent
_module_database_root = _plugin_root / "database"
_module_html_templates_root = _plugin_root / "templates"
_module_render_cache_root = _module_html_templates_root / "temp_output"


# 载入全局数据库对象
from .database.connection_manager import ConnectionManager
db_path = store.get_data_dir("ZikeQuote3") / "zikequote3.db"
db = ConnectionManager(db_path)
db.initialize_db() # 初始化，保证完整性


# 载入外部工具
from .utils.async_tools import serial_execution, async_modify_lock
from .html_capture import html_img_render, parse_md2html


# 加载 toml 配置并注入 BaseModel
from .config import reload_config, ConfigPath
_default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()
# 允许热更新配置
def notify_reload_config():
    global _default_cfg_toml, default_cfg, _cfg_toml, cfg
    _default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()


# 加载消息导入
from . import msgtexts