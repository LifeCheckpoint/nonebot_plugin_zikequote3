"""
调整设置相关命令
"""

from ast import literal_eval
from .comand_definition import *
from ..imports import *
from ..imports import _module_html_templates_root, _module_render_cache_root, _cfg_toml, _default_cfg_toml

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
    
    await matcher_get_quote_setting.finish(MsgSeg.image(image_data))

@matcher_modify_quote_setting.handle()
async def f_modify_quote_setting(event: GroupME, arg: Message = CommandArg()):
    """修改当前配置"""
    args = arg.extract_plain_text().strip().split(" ", 2)

    if len(args) < 2:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error="参数不足，请提供配置项模式和新的配置值~")
        return
    
    try:
        schema_str = args[0].strip()
        new_value = literal_eval(args[1].strip())
    except Exception as e:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error=f"输入的参数不合法哦~（{e}）")
        return
    
    try:
        from ..config import modify_group_config
        modify_group_config(event.group_id, schema_str, new_value, reload=True)
    except Exception as e:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error=str(e))
        return
    
    await matcher_modify_quote_setting.finish("配置修改成功~")