"""数据库隔离回归测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


@pytest.mark.parametrize("case_index", [1, 2])
async def test_each_case_starts_with_clean_database(
    case_index: int,
    async_session: AsyncSession,
) -> None:
    """参数化用例之间不应共享已提交的数据库状态。"""
    user_repo = UserRepository(async_session)
    assert await user_repo.count() == 0

    await user_repo.create_user(f"db_isolation_u{case_index}")

    assert await user_repo.count() == 1
