from ...imports import *
from ...imports import _cfg_toml, _default_cfg_toml

def s_get_quote_setting(group_id: int) -> dict:
    """获取群组配置"""
    is_default = _cfg_toml.get(group_id, None) is None
    data = {
        "title": "语录配置预览",
        "subtitle": f"群聊 {group_id}" + ("（默认配置）" if is_default else ""),
        "language": "language-toml",
        "code": tomlkit.dumps(_cfg_toml.get(group_id, _default_cfg_toml))
    }

    return data
