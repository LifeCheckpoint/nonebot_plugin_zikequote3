"""
集成测试 conftest —— nonebug + dishka fixture 骨架。

此文件将在后续子任务中添加以下内容：
- dishka AsyncContainer fixture（用于依赖注入测试）
- 集成测试专用的数据库 fixture（可能使用临时文件而非内存）

nonebot 初始化逻辑从顶层 conftest.py 移至此处，仅集成测试需要。
"""

import pytest
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    """nonebot 初始化 fixture（集成测试需要）。"""
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)

    # 加载插件
    nonebot.load_from_toml("pyproject.toml")
