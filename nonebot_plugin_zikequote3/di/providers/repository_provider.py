"""
Repository 层的 dishka Provider。

将全部 11 个 Repository 注册为 REQUEST 作用域依赖，
每个 Repository 接收 AsyncSession 并在请求结束时随 session 一起释放。
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.repositories import (
    GroupConfigRepository,
    GroupMemberRepository,
    GroupNicknameRepository,
    GroupRepository,
    ImageRepository,
    MappingRepository,
    MsgQueueRepository,
    QuoteRepository,
    ReviewRepository,
    UserNicknameRepository,
    UserRepository,
)


class RepositoryProvider(Provider):
    """Repository 依赖提供者，注册全部 11 个 Repository。"""

    scope = Scope.REQUEST

    @provide
    def provide_user_repo(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    @provide
    def provide_group_repo(self, session: AsyncSession) -> GroupRepository:
        return GroupRepository(session)

    @provide
    def provide_group_member_repo(self, session: AsyncSession) -> GroupMemberRepository:
        return GroupMemberRepository(session)

    @provide
    def provide_image_repo(self, session: AsyncSession) -> ImageRepository:
        return ImageRepository(session)

    @provide
    def provide_mapping_repo(self, session: AsyncSession) -> MappingRepository:
        return MappingRepository(session)

    @provide
    def provide_group_config_repo(self, session: AsyncSession) -> GroupConfigRepository:
        return GroupConfigRepository(session)

    @provide
    def provide_user_nickname_repo(self, session: AsyncSession) -> UserNicknameRepository:
        return UserNicknameRepository(session)

    @provide
    def provide_group_nickname_repo(self, session: AsyncSession) -> GroupNicknameRepository:
        return GroupNicknameRepository(session)

    @provide
    def provide_review_repo(self, session: AsyncSession) -> ReviewRepository:
        return ReviewRepository(session)

    @provide
    def provide_msg_queue_repo(self, session: AsyncSession) -> MsgQueueRepository:
        return MsgQueueRepository(session)

    @provide
    def provide_quote_repo(self, session: AsyncSession) -> QuoteRepository:
        return QuoteRepository(session)
