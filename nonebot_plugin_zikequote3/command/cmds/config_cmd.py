from ..command_definition import *
from ...imports import *

@matcher_get_current_config.handle()
async def f_get_current_config(event: GroupME):
    """生成当前配置预览"""
    from ...services.config_management.setting_service import s_get_setting_html

    async with event_exception_failmsg_a(matcher_get_current_config, "生成配置预览"):
        html = s_get_setting_html(event.group_id)
        image_data = await html_img_render(html, width=800, height=200)
        await matcher_get_current_config.finish(MsgSeg.image(image_data))


@matcher_modify_config.handle()
async def f_modify_config(event: GroupME, arg: Message = CommandArg()):
    """修改当前配置"""
    from ...services.config_management.validation_service import s_validate_parse_param
    from ...config import modify_group_config

    args = arg.extract_plain_text().strip().split(" ", 2)

    async with event_exception_failmsg_a(matcher_modify_config, "修改配置"):
        # 参数检查
        if len(args) < 2:
            raise ValueError("参数过少，至少需要两个参数👻~")
        
        # 解析参数
        try:
            schema_str, new_value = s_validate_parse_param(args)
        except Exception as e:
            raise ValueError(f"输入的参数，好奇怪喵X_X: {e}")
        
        # 执行修改
        modify_group_config(event.group_id, schema_str, new_value, reload=True)
        
        await matcher_modify_config.finish("配置修改成功~")


@matcher_batch_modify_config.handle()
async def f_batch_modify_config(event: GroupME, arg: Message = CommandArg()):
    """批量修改当前配置"""
    args = arg.extract_plain_text().strip()
    # TODO 确认逻辑


@matcher_reset_config.handle()
async def f_reset_config(event: GroupME):
    """重置当前群组配置"""
    # TODO 确认逻辑


@matcher_reload_config.handle()
async def f_reload_config(event: GroupME):
    """重载当前群组配置"""
    from ...imports import notify_reload_config

    async with event_exception_failmsg_a(matcher_reload_config, "重载配置"):
        notify_reload_config()
    
    await matcher_reload_config.finish("配置重载成功~")
