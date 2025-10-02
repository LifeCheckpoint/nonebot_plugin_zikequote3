"""
调整设置相关命令
"""

from ..imports import *
from ..imports import _module_html_templates_root, _module_render_cache_root, _cfg_toml, _default_cfg_toml
from .comand_definition import *

@matcher_get_quote_setting.handle()
async def f_get_quote_setting(event: GroupME):
    """生成当前配置预览"""
    try:
        is_default = _cfg_toml.get(event.group_id, None) is None
        data = {
            "title": "语录配置预览",
            "subtitle": f"群聊 {event.group_id}" + ("（默认配置）" if is_default else ""),
            "language": "language-toml",
            "code": tomlkit.dumps(_cfg_toml.get(event.group_id, _default_cfg_toml))
        }
        image_data = await full_render_html(_module_html_templates_root / "CodeFrame.html", _module_render_cache_root, data=data)
        send_msg = await matcher_get_quote_setting.send(MsgSeg.image(image_data))
    except Exception as e:
        logger.error(f"生成配置预览失败: {e}")
        await matcher_get_quote_setting.finish(f"生成配置预览失败啦O.O，服务器说：{e}")