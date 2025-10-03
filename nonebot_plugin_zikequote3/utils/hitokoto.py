from ..imports import *

def get_hitokoto() -> Tuple[Optional[str], Optional[str]]:
    """
    从指定链接获取名人名言，返回名言和名言作者。

    错误返回 (None, None)
    """
    try:
        response = requests.get(default_cfg.showcase.hitokoto_url, timeout=3)
        response.raise_for_status()
        data = response.json()
        hitokoto_content = data.get("hitokoto", None)
        from_who = data.get("from_who", None)
        return hitokoto_content, from_who
    except Exception as e:
        logger.error(f"获取名人名言时发生错误: {e}")
        return None, None