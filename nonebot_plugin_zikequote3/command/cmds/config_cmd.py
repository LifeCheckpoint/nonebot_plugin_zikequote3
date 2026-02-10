"""
配置命令处理器（dishka DI 版本）。

替代旧的 config_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

注意：
- 查看配置预览通过 HtmlRenderServiceBase 渲染 code_frame 模板为图片。
- 修改配置使用 ConfigService.parse_config_param 替代旧的 validation_service。
- 批量修改和重置配置在旧版本中也是 TODO 状态，新版本保持一致。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment as MsgSeg
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition import (
    matcher_get_current_config,
    matcher_modify_config,
    matcher_batch_modify_config,
    matcher_reset_config,
    matcher_reload_config,
)
from ...di import get_container
from ...services import ConfigService
from ...services.html_render_service import HtmlRenderServiceBase
from ...templates.schema.code_frame import TemplateCodeFrameData, render_code_frame
from ._error_handlers import command_error_handler

logger = logging.getLogger(__name__)


# ===================================================================
# region 查看当前配置
# ===================================================================

@matcher_get_current_config.handle()
async def handle_get_current_config(event: GroupMessageEvent) -> None:
    """生成当前配置预览，优先渲染为图片，失败时降级为纯文本。"""
    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        config_svc = await request_scope.get(ConfigService)
        html_render_svc = await request_scope.get(HtmlRenderServiceBase)

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
                    html, width=800, height=600,
                )
                await matcher_get_current_config.finish(MsgSeg.image(img))
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
async def handle_modify_config(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
) -> None:
    """修改当前配置。"""
    args = arg.extract_plain_text().strip().split(" ", 2)
    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        config_svc = await request_scope.get(ConfigService)

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
    """批量修改当前配置。"""
    # TODO: 旧版本中此功能也是 TODO 状态，保持一致
    args = arg.extract_plain_text().strip()
    await matcher_batch_modify_config.finish("批量修改配置功能暂未实现~")

# endregion


# ===================================================================
# region 重置配置
# ===================================================================

@matcher_reset_config.handle()
async def handle_reset_config(event: GroupMessageEvent) -> None:
    """重置当前群组配置。"""
    # TODO: 旧版本中此功能也是 TODO 状态，保持一致
    await matcher_reset_config.finish("重置配置功能暂未实现~")

# endregion


# ===================================================================
# region 重载配置
# ===================================================================

@matcher_reload_config.handle()
async def handle_reload_config(event: GroupMessageEvent) -> None:
    """重载当前群组配置。

    新架构中配置通过 ConfigService 从数据库按需读取，
    不再依赖旧的全局缓存重载机制。此命令仅作确认用途。
    """
    await matcher_reload_config.finish(
        "新版本配置已改为实时从数据库读取，无需手动重载~"
    )

# endregion
