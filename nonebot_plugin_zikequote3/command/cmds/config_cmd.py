"""
配置命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。

注意：
- 查看配置预览通过 HtmlRenderServiceBase 渲染 code_frame 模板为图片。
- 修改配置使用 ConfigService.parse_config_param 替代旧的 validation_service。
- 批量修改和重置配置在旧版本中也是 TODO 状态，新版本保持一致。
"""

from __future__ import annotations

from nonebot import logger

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment as MsgSeg
from nonebot.adapters import Message
from nonebot.exception import FinishedException
from nonebot.params import CommandArg

from ..command_definition import (
    matcher_get_current_config,
    matcher_modify_config,
    matcher_batch_modify_config,
    matcher_reset_config,
)
from ...di import Inject, inject
from ...services import ConfigService
from ...services.html_render_service import HtmlRenderServiceBase
from ...templates.registry import CODE_FRAME
from ...templates.schema.code_frame import TemplateCodeFrameData, render_code_frame
from ._error_handlers import command_error_handler

# ===================================================================
# region 查看当前配置
# ===================================================================

@matcher_get_current_config.handle()
@inject
async def handle_get_current_config(
    event: GroupMessageEvent,
    config_svc: ConfigService = Inject(ConfigService),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """
    处理查看当前配置命令。

    生成当前群组配置预览，优先渲染为图片，失败时降级为纯文本。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    """
    group_id = str(event.group_id)

    async with command_error_handler(
        matcher_get_current_config, "生成配置预览"
    ):
        toml_str = await config_svc.get_group_toml(group_id)
        if toml_str is None:
            await matcher_get_current_config.finish(
                "当前群组尚未配置自定义设置，使用默认配置~"
            )

        # 尝试渲染为图片
        try:
            html = render_code_frame(TemplateCodeFrameData(
                title=f"群组 {group_id} 配置",
                subtitle="当前群组自定义配置预览",
                language="language-toml",
                code=toml_str,
            ))
            img = await html_render_svc.render(
                html, width=CODE_FRAME.width, height=CODE_FRAME.height,
            )
            await matcher_get_current_config.finish(MsgSeg.image(img))
        except FinishedException:
            raise
        except Exception as e:
            logger.warning("配置预览图片渲染失败，降级为纯文本: %s", e)
            await matcher_get_current_config.finish(
                f"当前群组配置：\n{toml_str}"
            )

# endregion

# ===================================================================
# region 修改配置
# ===================================================================

@matcher_modify_config.handle()
@inject
async def handle_modify_config(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    config_svc: ConfigService = Inject(ConfigService),
) -> None:
    """
    处理修改配置命令。

    解析用户输入的配置键值对，更新当前群组的单项配置。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param arg: 命令参数消息体
    :type arg: Message
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    """
    args = arg.extract_plain_text().strip().split(" ", 2)
    group_id = str(event.group_id)

    async with command_error_handler(matcher_modify_config, "修改配置"):
        # 参数检查
        if len(args) < 2:
            raise ValueError("参数过少，至少需要两个参数👻~")

        # 解析参数
        try:
            schema_str, new_value = config_svc.parse_config_param(args)
        except Exception as e:
            raise ValueError(f"输入的参数，好奇怪喵X_X: {e}")

        await config_svc.modify_single_value(group_id, schema_str, new_value)
        await matcher_modify_config.finish("配置修改成功~")

# endregion

# ===================================================================
# region 批量修改配置
# ===================================================================

@matcher_batch_modify_config.handle()
async def handle_batch_modify_config(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
) -> None:
    """
    处理批量修改配置命令（暂未实现）。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param arg: 命令参数消息体
    :type arg: Message
    """
    # TODO: 旧版本中此功能也是 TODO 状态，保持一致
    args = arg.extract_plain_text().strip()
    await matcher_batch_modify_config.finish("批量修改配置功能暂未实现~")

# endregion

# ===================================================================
# region 重置配置
# ===================================================================

@matcher_reset_config.handle()
async def handle_reset_config(event: GroupMessageEvent) -> None:
    """
    处理重置当前群组配置命令（暂未实现）。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    """
    # TODO: 旧版本中此功能也是 TODO 状态，保持一致
    await matcher_reset_config.finish("重置配置功能暂未实现~")

# endregion
