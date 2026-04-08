"""
一言（Hitokoto）API 工具。

提供从一言 API 获取随机名言的功能。
"""

from nonebot import logger
from typing import Optional, Tuple

import requests

# 默认一言 API 地址，与 config.ShowcaseConfig.hitokoto_url 保持一致
_DEFAULT_HITOKOTO_URL = "https://v1.hitokoto.cn"

def get_hitokoto(
    hitokoto_url: str = _DEFAULT_HITOKOTO_URL,
) -> Tuple[Optional[str], Optional[str]]:
    """
    从指定链接获取名人名言，返回名言和名言作者。

    :param hitokoto_url: 一言 API 地址，默认使用 ``https://v1.hitokoto.cn``
    :type hitokoto_url: str
    :returns: ``(名言内容, 名言作者)`` 元组，请求失败时返回 ``(None, None)``
    :rtype: Tuple[Optional[str], Optional[str]]
    """
    hitokoto_url = hitokoto_url.strip()
    if not hitokoto_url:
        return None, None

    try:
        response = requests.get(hitokoto_url, timeout=3)
        response.raise_for_status()
        data = response.json()
        hitokoto_content = data.get("hitokoto", None)
        from_who = data.get("from_who", None)
        return hitokoto_content, from_who
    except Exception as e:
        logger.error(f"获取名人名言时发生错误: {e}")
        return None, None