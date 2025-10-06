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
from typing import Optional, Union, Literal, Callable, Any, Dict, List, Tuple
import asyncio
import colorsys
import nonebot_plugin_localstore as store
import random
import requests
import sentry_sdk
import tomlkit
import typer

# 插件根目录
_plugin_root = Path(__file__).parent
module_database_root = _plugin_root / "database"
module_html_capture_root = _plugin_root / "html_capture"
module_render_html_root = _plugin_root / "templates" / "output" / "rendered_html"
module_render_image_root = _plugin_root / "templates" / "output" / "rendered_image"
module_templates_root = _plugin_root / "templates"

data_db_path = store.get_data_dir("ZikeQuote3") / "zikequote3.db"
data_image_root = store.get_data_dir("ZikeQuote3") / "quote_images"


# 载入全局数据库对象
from .database.connection_manager import ConnectionManager
db = ConnectionManager(data_db_path)
db.initialize_db() # 初始化，保证完整性


# 载入图像存储管理器
from .database.image_store import ImageStore
qimg_store = ImageStore(data_image_root)


# HTML 截图工具
from .html_capture import html_img_render, parse_md2html


# 异常上报与日志工具
from .utils.error_report import exception_report, exception_finish_failure


# 加载 toml 配置并注入 BaseModel
from .config import reload_config, ConfigPath
_default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()
# 允许热更新配置
def notify_reload_config():
    global _default_cfg_toml, default_cfg, _cfg_toml, cfg
    _default_cfg_toml, default_cfg, _cfg_toml, cfg = reload_config()


# 配置 sentry
dsn_path = Path(default_cfg.sentry.dsn_path)
dsn_str = (
    dsn_path if dsn_path.is_absolute() else (_plugin_root / dsn_path)
).read_text(encoding="utf-8").strip()
sentry_sdk.init(dsn=dsn_str if dsn_str else None, send_default_pii=True)


# 加载消息导入
from . import msgtexts