"""
顶层测试配置。

- pytest-asyncio mode 已在 pyproject.toml 中配置为 "auto"
- asyncio_default_fixture_loop_scope 已设为 "session"
- testpaths 设为 ["tests"]，测试目录与包隔离，避免触发 nonebot 初始化
"""

import pytest
from loguru import logger as loguru_logger
from pytest_asyncio import is_async_test


@pytest.fixture(scope="session", autouse=True)
def _suppress_loguru_output():
    """移除 loguru 默认 stderr sink，抑制 nonebot logger 的控制台噪音输出。"""
    loguru_logger.remove()
    yield


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """为所有异步测试统一设置 session 级别的事件循环。"""
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
