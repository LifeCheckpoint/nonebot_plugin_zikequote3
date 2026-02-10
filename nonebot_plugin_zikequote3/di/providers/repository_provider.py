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
        """
        提供用户仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 用户仓库实例
        :rtype: UserRepository
        """
        return UserRepository(session)

    @provide
    def provide_group_repo(self, session: AsyncSession) -> GroupRepository:
        """
        提供群组仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 群组仓库实例
        :rtype: GroupRepository
        """
        return GroupRepository(session)

    @provide
    def provide_group_member_repo(self, session: AsyncSession) -> GroupMemberRepository:
        """
        提供群成员仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 群成员仓库实例
        :rtype: GroupMemberRepository
        """
        return GroupMemberRepository(session)

    @provide
    def provide_image_repo(self, session: AsyncSession) -> ImageRepository:
        """
        提供图片仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 图片仓库实例
        :rtype: ImageRepository
        """
        return ImageRepository(session)

    @provide
    def provide_mapping_repo(self, session: AsyncSession) -> MappingRepository:
        """
        提供消息-语录映射仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 映射仓库实例
        :rtype: MappingRepository
        """
        return MappingRepository(session)

    @provide
    def provide_group_config_repo(self, session: AsyncSession) -> GroupConfigRepository:
        """
        提供群配置仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 群配置仓库实例
        :rtype: GroupConfigRepository
        """
        return GroupConfigRepository(session)

    @provide
    def provide_user_nickname_repo(self, session: AsyncSession) -> UserNicknameRepository:
        """
        提供用户昵称仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 用户昵称仓库实例
        :rtype: UserNicknameRepository
        """
        return UserNicknameRepository(session)

    @provide
    def provide_group_nickname_repo(self, session: AsyncSession) -> GroupNicknameRepository:
        """
        提供群昵称仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 群昵称仓库实例
        :rtype: GroupNicknameRepository
        """
        return GroupNicknameRepository(session)

    @provide
    def provide_review_repo(self, session: AsyncSession) -> ReviewRepository:
        """
        提供审核仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 审核仓库实例
        :rtype: ReviewRepository
        """
        return ReviewRepository(session)

    @provide
    def provide_msg_queue_repo(self, session: AsyncSession) -> MsgQueueRepository:
        """
        提供消息队列仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 消息队列仓库实例
        :rtype: MsgQueueRepository
        """
        return MsgQueueRepository(session)

    @provide
    def provide_quote_repo(self, session: AsyncSession) -> QuoteRepository:
        """
        提供语录仓库实例。

        :param session: 异步数据库会话
        :type session: AsyncSession
        :returns: 语录仓库实例
        :rtype: QuoteRepository
        """
        return QuoteRepository(session)
