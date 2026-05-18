"""
一言（Hitokoto）API 工具。

提供从一言 API 获取随机名言的功能。
"""

import httpx
from typing import Optional, Tuple

_DEFAULT_HITOKOTO_URL = "https://v1.hitokoto.cn"


async def get_hitokoto(
    hitokoto_url: str = _DEFAULT_HITOKOTO_URL,
) -> Tuple[Optional[str], Optional[str]]:
    hitokoto_url = hitokoto_url.strip()
    if not hitokoto_url:
        return None, None

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(hitokoto_url)
            response.raise_for_status()
            data = response.json()
            return data.get("hitokoto"), data.get("from_who")
    except Exception:
        return None, None