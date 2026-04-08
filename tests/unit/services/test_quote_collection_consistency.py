"""QuoteCollectionService 一致性回归测试。"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_zikequote3.database.repositories.group_member_repository import (
    GroupMemberRepository,
)
from nonebot_plugin_zikequote3.database.repositories.group_nickname_repository import (
    GroupNicknameRepository,
)
from nonebot_plugin_zikequote3.database.repositories.group_repository import (
    GroupRepository,
)
from nonebot_plugin_zikequote3.database.repositories.image_repository import (
    ImageRepository,
)
from nonebot_plugin_zikequote3.database.repositories.mapping_repository import (
    MappingRepository,
)
from nonebot_plugin_zikequote3.database.repositories.msg_queue_repository import (
    MsgQueueRepository,
)
from nonebot_plugin_zikequote3.database.repositories.quote_repository import (
    QuoteRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_nickname_repository import (
    UserNicknameRepository,
)
from nonebot_plugin_zikequote3.database.repositories.user_repository import (
    UserRepository,
)
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.group_service import GroupService
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectionLockManager,
    QuoteCollectionService,
    SelectedQuote,
)
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService
from nonebot_plugin_zikequote3.services.review_service import ReviewService
from nonebot_plugin_zikequote3.services.user_service import UserService


pytestmark = pytest.mark.anyio


@dataclass
class _CollectionStack:
    collection_service: QuoteCollectionService
    group_service: GroupService
    quote_repo: QuoteRepository
    msg_queue_repo: MsgQueueRepository


def _build_collection_stack(
    session: AsyncSession,
    *,
    message_filter: AsyncMock,
    review_service: AsyncMock,
    lock_manager: CollectionLockManager | None = None,
) -> _CollectionStack:
    user_repo = UserRepository(session)
    user_nickname_repo = UserNicknameRepository(session)
    group_nickname_repo = GroupNicknameRepository(session)
    group_member_repo = GroupMemberRepository(session)
    group_repo = GroupRepository(session)
    quote_repo = QuoteRepository(session)
    image_repo = ImageRepository(session)
    mapping_repo = MappingRepository(session)
    msg_queue_repo = MsgQueueRepository(session)

    user_service = UserService(
        user_repo=user_repo,
        user_nickname_repo=user_nickname_repo,
        group_nickname_repo=group_nickname_repo,
        group_member_repo=group_member_repo,
    )
    group_service = GroupService(
        group_repo=group_repo,
        group_member_repo=group_member_repo,
        group_nickname_repo=group_nickname_repo,
    )
    quote_write_service = QuoteWriteService(
        quote_repo=quote_repo,
        image_repo=image_repo,
        mapping_repo=mapping_repo,
        user_service=user_service,
        config_service=AsyncMock(spec=ConfigService),
        group_repo=group_repo,
    )
    collection_service = QuoteCollectionService(
        msg_queue_repo=msg_queue_repo,
        quote_write_service=quote_write_service,
        user_service=user_service,
        group_service=group_service,
        review_service=review_service,
        lock_manager=lock_manager or CollectionLockManager(),
        message_filter=message_filter,
    )
    return _CollectionStack(
        collection_service=collection_service,
        group_service=group_service,
        quote_repo=quote_repo,
        msg_queue_repo=msg_queue_repo,
    )


class TestQuoteCollectionConsistency:
    """验证收集闭环在异常场景下的一致性。"""

    async def test_finalize_review_failure_rolls_back_quote_and_preserves_queue_for_retry(
        self,
        async_session_factory,
        init_db,
    ) -> None:
        group_id = "g_tx_1"
        user_id = "u_tx_1"
        msg_id = "m_tx_1"
        quote_id = "q_tx_1"
        content = "回滚测试语录"
        ai_comment = "AI 评论失败后应整体回滚"

        # 先在已提交请求中保留队列消息，模拟真实重试场景。
        async with async_session_factory() as seed_session:
            seed_stack = _build_collection_stack(
                seed_session,
                message_filter=AsyncMock(),
                review_service=AsyncMock(spec=ReviewService),
            )
            await seed_stack.group_service.ensure_group_exists(group_id)
            await seed_stack.collection_service.enqueue_message(
                group_id=group_id,
                msg_id=msg_id,
                user_id=user_id,
                content=content,
            )
            await seed_session.commit()

        # 第一次执行：保存语录后在评论阶段失败，整个请求回滚。
        failing_filter = AsyncMock()
        failing_filter.filter_messages.return_value = [
            SelectedQuote(msg_id=msg_id, content=content, comment=ai_comment),
        ]
        failing_review_service = AsyncMock(spec=ReviewService)
        failing_review_service.add_review.side_effect = RuntimeError("review failed")

        async with async_session_factory() as failing_session:
            failing_stack = _build_collection_stack(
                failing_session,
                message_filter=failing_filter,
                review_service=failing_review_service,
            )
            with patch(
                "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
                return_value=quote_id,
            ):
                with pytest.raises(RuntimeError, match="review failed"):
                    await failing_stack.collection_service.collect_and_finalize(group_id)
                await failing_session.rollback()

        # 回滚后：语录未落库，原队列仍保留，不会形成“已存语录 + 脏队列”窗口。
        async with async_session_factory() as verify_failed_session:
            verify_failed_stack = _build_collection_stack(
                verify_failed_session,
                message_filter=AsyncMock(),
                review_service=AsyncMock(spec=ReviewService),
            )
            assert await verify_failed_stack.quote_repo.get_quote_by_id(quote_id) is None
            remaining_msgs = await verify_failed_stack.msg_queue_repo.get_msgs_by_group(group_id)
            assert [msg.msg_id for msg in remaining_msgs] == [msg_id]
            await verify_failed_session.rollback()

        # 第二次执行：同一批队列重试成功，只会生成一条语录并清空队列。
        success_filter = AsyncMock()
        success_filter.filter_messages.return_value = [
            SelectedQuote(msg_id=msg_id, content=content, comment=ai_comment),
        ]
        success_review_service = AsyncMock(spec=ReviewService)
        success_review_service.add_review.return_value = "r_tx_1"

        async with async_session_factory() as success_session:
            success_stack = _build_collection_stack(
                success_session,
                message_filter=success_filter,
                review_service=success_review_service,
            )
            with patch(
                "nonebot_plugin_zikequote3.services.quote_write_service._generate_quote_id",
                return_value=quote_id,
            ):
                collected = await success_stack.collection_service.collect_and_finalize(group_id)
            await success_session.commit()

        assert [item.quote_id for item in collected] == [quote_id]
        success_review_service.add_review.assert_awaited_once()

        async with async_session_factory() as final_session:
            final_stack = _build_collection_stack(
                final_session,
                message_filter=AsyncMock(),
                review_service=AsyncMock(spec=ReviewService),
            )
            saved_quote = await final_stack.quote_repo.get_quote_by_id(quote_id)
            assert saved_quote is not None
            assert await final_stack.msg_queue_repo.count_msgs_by_group(group_id) == 0
            saved_quotes = await final_stack.quote_repo.get_quotes_by_group(group_id)
            assert [quote.quote_id for quote in saved_quotes] == [quote_id]
            await final_session.rollback()
