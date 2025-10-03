"""
语录设置调整相关命令
"""

from ..comand_definition import *
from ...imports import *

@matcher_get_quote_setting.handle()
async def f_get_quote_setting(event: GroupME):
    """生成当前配置预览"""
    from ...services.settings.get_quote_setting import s_get_quote_setting
    from ...imports import _module_html_templates_root, _module_render_cache_root

    try:
        data = s_get_quote_setting(event.group_id)
        image_data = await full_render_html(_module_html_templates_root / "CodeFrame.html", _module_render_cache_root, data=data)
    except Exception as e:
        logger.error(f"生成配置预览失败: {e}")
        await matcher_get_quote_setting.finish(f"生成配置预览失败啦O.O，服务器说：{e}")
    
    await matcher_get_quote_setting.finish(MsgSeg.image(image_data))

@matcher_modify_quote_setting.handle()
async def f_modify_quote_setting(event: GroupME, arg: Message = CommandArg()):
    """修改当前配置"""
    from ...services.settings.modify_quote_setting import s_validate_parse_param
    from ...config import modify_group_config

    args = arg.extract_plain_text().strip().split(" ", 2)

    if len(args) < 2:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error="参数不足，请提供配置项模式和新的配置值~")
        return
    
    try:
        schema_str, new_value = s_validate_parse_param(args)
    except Exception as e:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error=f"输入的参数不合法哦~（{e}）")
        return
    
    try:
        modify_group_config(event.group_id, schema_str, new_value, reload=True)
    except Exception as e:
        await mfinish(matcher_modify_quote_setting, msg_quote_setting_update_failed, error=str(e))
        return
    
    await matcher_modify_quote_setting.finish("配置修改成功~")

@matcher_batch_modify_quote_setting.handle()
async def f_batch_modify_quote_setting(event: GroupME, arg: Message = CommandArg()):
    """批量修改当前配置"""
    args = arg.extract_plain_text().strip()

    # TODO 确认逻辑

@matcher_reset_quote_setting.handle()
async def f_reset_quote_setting(event: GroupME):
    """重置当前群组配置"""
    # TODO 确认逻辑

@matcher_reload_quote_setting.handle()
async def f_reload_quote_setting(event: GroupME):
    """重载当前群组配置"""
    from ...imports import notify_reload_config

    try:
        notify_reload_config()
    except Exception as e:
        await mfinish(matcher_reload_quote_setting, msg_quote_setting_reload_failed, error=str(e))
        return
    
    await matcher_reload_quote_setting.finish("配置重载成功~")
