"""
配置命令处理器（dishka DI 版本）。

替代旧的 config_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

注意：
- 查看配置预览依赖 HTML 截图（html_img_render），保留对旧模块的引用。
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
from ...utils.error_report import event_exception_failmsg_a

logger = logging.getLogger(__name__)


# ===================================================================
# region 查看当前配置
# ===================================================================

@matcher_get_current_config.handle()
async def handle_get_current_config(event: GroupMessageEvent) -> None:
    """生成当前配置预览。"""
    # TODO: 旧版本使用 s_get_setting_html + html_img_render 生成配置预览图片。
    # 该功能依赖未重构的 HTML 截图模块（html_img_render）和旧的
    # setting_service.s_get_setting_html。新版本暂时使用文本方式展示配置。
    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        config_svc = await request_scope.get(ConfigService)

        async with event_exception_failmsg_a(
            matcher_get_current_config, "生成配置预览"
        ):
            toml_str = await config_svc.get_group_toml(group_id)
            if toml_str is None:
                await matcher_get_current_config.finish(
                    "当前群组尚未配置自定义设置，使用默认配置~"
                )
            else:
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

        async with event_exception_failmsg_a(matcher_modify_config, "修改配置"):
            # 参数检查
            if len(args) < 2:
                raise ValueError("参数过少，至少需要两个参数👻~")

            # 解析参数
            try:
                schema_str, new_value = config_svc.parse_config_param(args)
            except Exception as e:
                raise ValueError(f"输入的参数，好奇怪喵X_X: {e}")

            # TODO: ConfigService 目前没有 modify_single_value 方法，
            # 旧版本使用 config.modify_group_config(group_id, schema_str, new_value)。
            # 需要后续在 ConfigService 中补充按 schema_path 修改单个配置值的方法。
            # 暂时使用旧模块的方式处理。
            from ...config import modify_group_config
            modify_group_config(event.group_id, schema_str, new_value, reload=True)

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
    """重载当前群组配置。"""
    # TODO: 旧版本使用 imports.notify_reload_config() 热更新全局配置。
    # 该功能依赖旧的全局配置加载机制，暂时保留对旧模块的引用。
    async with event_exception_failmsg_a(matcher_reload_config, "重载配置"):
        from ...imports import notify_reload_config
        notify_reload_config()

    await matcher_reload_config.finish("配置重载成功~")

# endregion
