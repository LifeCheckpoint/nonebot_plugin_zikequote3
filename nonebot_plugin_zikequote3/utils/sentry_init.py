"""
Sentry 初始化工具。

提供从文件读取 DSN 并初始化 Sentry SDK 的功能。
"""

from pathlib import Path
from typing import Optional

from nonebot import logger

from ..paths import PluginPath


def init_sentry(sentry_dsn_path: Optional[str] = None) -> None:
    """
    从指定路径读取 Sentry DSN 并初始化 Sentry SDK。

    支持相对路径（相对于插件根目录）和绝对路径。
    路径为空、文件不存在或内容为空时跳过初始化并记录日志。

    :param sentry_dsn_path: Sentry DSN 文件路径，为 ``None`` 时跳过初始化
    :type sentry_dsn_path: Optional[str]
    """
    import sentry_sdk

    dsn_path_to_parse = Path(sentry_dsn_path) if sentry_dsn_path else None
    if dsn_path_to_parse and not dsn_path_to_parse.is_absolute():
        dsn_path = PluginPath.plugin_root / dsn_path_to_parse
    elif dsn_path_to_parse is not None:
        dsn_path = dsn_path_to_parse
    else:
        dsn_path = None

    if dsn_path is None:
        logger.warning("Sentry DSN: (not set for empty path)")
        return
    
    if not dsn_path.is_file():
        logger.error(f"Sentry DSN: (not set, file {dsn_path} does not exist)")
        return
    
    try:
        dsn_str = dsn_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to read Sentry DSN from {dsn_path}: {e}")
        return
    
    if not dsn_str or dsn_str == "":
        logger.warning("Sentry DSN: (not set for empty content)")
        return

    logger.info(f"Sentry DSN: {dsn_str[:8] + '...' }")
    sentry_sdk.init(dsn=dsn_str, traces_sample_rate=1.0)
