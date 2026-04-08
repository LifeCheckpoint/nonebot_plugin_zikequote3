"""
Service 层的 dishka Provider。

注册全部 9 个 Service 类到 REQUEST 作用域。
dishka 自动解析服务间的依赖链（如 QuoteWriteService 依赖 UserService）。
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from ...config import ConfigSchema
from ...vector_search.search_service import VectorSearchService
from ...database.repositories.group_config_repository import GroupConfigRepository
from ...database.repositories.group_member_repository import GroupMemberRepository
from ...database.repositories.group_nickname_repository import GroupNicknameRepository
from ...database.repositories.group_repository import GroupRepository
from ...database.repositories.image_repository import ImageRepository
from ...database.repositories.mapping_repository import MappingRepository
from ...database.repositories.msg_queue_repository import MsgQueueRepository
from ...database.repositories.quote_repository import QuoteRepository
from ...database.repositories.review_repository import ReviewRepository
from ...database.repositories.user_nickname_repository import UserNicknameRepository
from ...database.repositories.user_repository import UserRepository
from ...services.config_service import ConfigService
from ...services.group_service import GroupService
from ...services.migration_service import MigrationService
from ...services.quote_collection_service import (
    CollectionLockManager,
    QuoteCollectionService,
    MessageFilter,
)
from ...llm_services.llm_message_filter import LLMMessageFilter
from ...services.quote_read_service import QuoteReadService
from ...services.quote_write_service import QuoteWriteService
from ...services.review_service import ReviewService
from ...services.statistics_service import StatisticsService
from ...services.user_service import UserService


class ServiceProvider(Provider):
    """
    Service 依赖提供者，注册全部 9 个 Service。

    依赖链（无循环）：
    - UserService          ← Repositories only
    - GroupService         ← Repositories only
    - ReviewService        ← Repositories only
    - StatisticsService    ← Repositories only
    - ConfigService        ← Repositories only
    - MigrationService     ← Repositories only
    - QuoteWriteService    ← Repositories + UserService
    - QuoteReadService     ← Repositories + UserService
    - QuoteCollectionService ← Repositories + QuoteWriteService + UserService + GroupService
    """

    scope = Scope.REQUEST

    def __init__(self, default_config: ConfigSchema | None = None) -> None:
        super().__init__()
        self._default_config = default_config

    # ---- 无服务间依赖的 Service ---- #

    @provide
    def provide_user_service(
        self,
        user_repo: UserRepository,
        user_nickname_repo: UserNicknameRepository,
        group_nickname_repo: GroupNicknameRepository,
        group_member_repo: GroupMemberRepository,
    ) -> UserService:
        """
        提供用户服务实例。

        :param user_repo: 用户仓库
        :type user_repo: UserRepository
        :param user_nickname_repo: 用户昵称仓库
        :type user_nickname_repo: UserNicknameRepository
        :param group_nickname_repo: 群昵称仓库
        :type group_nickname_repo: GroupNicknameRepository
        :param group_member_repo: 群成员仓库
        :type group_member_repo: GroupMemberRepository
        :returns: 用户服务实例
        :rtype: UserService
        """
        return UserService(
            user_repo=user_repo,
            user_nickname_repo=user_nickname_repo,
            group_nickname_repo=group_nickname_repo,
            group_member_repo=group_member_repo,
        )

    @provide
    def provide_group_service(
        self,
        group_repo: GroupRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
    ) -> GroupService:
        """
        提供群组服务实例。

        :param group_repo: 群组仓库
        :type group_repo: GroupRepository
        :param group_member_repo: 群成员仓库
        :type group_member_repo: GroupMemberRepository
        :param group_nickname_repo: 群昵称仓库
        :type group_nickname_repo: GroupNicknameRepository
        :returns: 群组服务实例
        :rtype: GroupService
        """
        return GroupService(
            group_repo=group_repo,
            group_member_repo=group_member_repo,
            group_nickname_repo=group_nickname_repo,
        )

    @provide
    def provide_review_service(
        self,
        review_repo: ReviewRepository,
        quote_repo: QuoteRepository,
        user_service: UserService,
    ) -> ReviewService:
        """
        提供审核服务实例。

        :param review_repo: 审核仓库
        :type review_repo: ReviewRepository
        :param quote_repo: 语录仓库
        :type quote_repo: QuoteRepository
        :returns: 审核服务实例
        :rtype: ReviewService
        """
        return ReviewService(
            review_repo=review_repo,
            quote_repo=quote_repo,
            user_service=user_service,
        )

    @provide
    def provide_statistics_service(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
    ) -> StatisticsService:
        """
        提供统计服务实例。

        :param quote_repo: 语录仓库
        :type quote_repo: QuoteRepository
        :param group_member_repo: 群成员仓库
        :type group_member_repo: GroupMemberRepository
        :returns: 统计服务实例
        :rtype: StatisticsService
        """
        return StatisticsService(
            quote_repo=quote_repo,
            group_member_repo=group_member_repo,
        )

    @provide
    def provide_config_service(
        self,
        group_config_repo: GroupConfigRepository,
        group_repo: GroupRepository,
    ) -> ConfigService:
        """
        提供配置服务实例。

        :param group_config_repo: 群配置仓库
        :type group_config_repo: GroupConfigRepository
        :param group_repo: 群组仓库
        :type group_repo: GroupRepository
        :returns: 配置服务实例
        :rtype: ConfigService
        """
        return ConfigService(
            group_config_repo=group_config_repo,
            group_repo=group_repo,
            default_config=self._default_config,
        )

    @provide
    def provide_migration_service(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
        review_repo: ReviewRepository,
        mapping_repo: MappingRepository,
    ) -> MigrationService:
        """
        提供迁移服务实例。

        :param quote_repo: 语录仓库
        :type quote_repo: QuoteRepository
        :param group_member_repo: 群成员仓库
        :type group_member_repo: GroupMemberRepository
        :param group_nickname_repo: 群昵称仓库
        :type group_nickname_repo: GroupNicknameRepository
        :param review_repo: 评论仓库
        :type review_repo: ReviewRepository
        :param mapping_repo: 消息映射仓库
        :type mapping_repo: MappingRepository
        :returns: 迁移服务实例
        :rtype: MigrationService
        """
        return MigrationService(
            quote_repo=quote_repo,
            group_member_repo=group_member_repo,
            group_nickname_repo=group_nickname_repo,
            review_repo=review_repo,
            mapping_repo=mapping_repo,
        )

    # ---- 依赖其他 Service 的 Service ---- #

    @provide
    def provide_quote_write_service(
        self,
        quote_repo: QuoteRepository,
        image_repo: ImageRepository,
        mapping_repo: MappingRepository,
        user_service: UserService,
        config_service: ConfigService,
        group_repo: GroupRepository,
        vector_search_svc: VectorSearchService,
    ) -> QuoteWriteService:
        """
        提供语录写入服务实例。

        :param quote_repo: 语录仓库
        :type quote_repo: QuoteRepository
        :param image_repo: 图片仓库
        :type image_repo: ImageRepository
        :param mapping_repo: 消息-语录映射仓库
        :type mapping_repo: MappingRepository
        :param user_service: 用户服务
        :type user_service: UserService
        :param config_service: 配置服务
        :type config_service: ConfigService
        :param group_repo: 群组仓库（用于 ensure_group_exists 兜底保护）
        :type group_repo: GroupRepository
        :param vector_search_svc: 向量搜索服务（基础设施不可用时为 None）
        :type vector_search_svc: VectorSearchService
        :returns: 语录写入服务实例
        :rtype: QuoteWriteService
        """
        return QuoteWriteService(
            quote_repo=quote_repo,
            image_repo=image_repo,
            mapping_repo=mapping_repo,
            user_service=user_service,
            config_service=config_service,
            group_repo=group_repo,
            vector_search_svc=vector_search_svc,
        )

    @provide
    def provide_quote_read_service(
        self,
        quote_repo: QuoteRepository,
        review_repo: ReviewRepository,
        image_repo: ImageRepository,
        user_service: UserService,
    ) -> QuoteReadService:
        """
        提供语录读取服务实例。

        :param quote_repo: 语录仓库
        :type quote_repo: QuoteRepository
        :param review_repo: 审核仓库
        :type review_repo: ReviewRepository
        :param image_repo: 图片仓库
        :type image_repo: ImageRepository
        :param user_service: 用户服务
        :type user_service: UserService
        :returns: 语录读取服务实例
        :rtype: QuoteReadService
        """
        return QuoteReadService(
            quote_repo=quote_repo,
            review_repo=review_repo,
            image_repo=image_repo,
            user_service=user_service,
        )

    @provide
    def provide_llm_message_filter(
        self,
        config_service: ConfigService,
    ) -> LLMMessageFilter:
        """
        提供 LLM 消息筛选器实例。

        :param config_service: 配置服务
        :type config_service: ConfigService
        :returns: LLM 消息筛选器实例
        :rtype: LlmMessageFilter
        """
        return LLMMessageFilter(config_service=config_service)

    @provide
    def provide_quote_collection_service(
        self,
        msg_queue_repo: MsgQueueRepository,
        quote_write_service: QuoteWriteService,
        user_service: UserService,
        group_service: GroupService,
        review_service: ReviewService,
        lock_manager: CollectionLockManager,
        message_filter: LLMMessageFilter,
    ) -> QuoteCollectionService:
        """
        提供语录收集服务实例。

        :param msg_queue_repo: 消息队列仓库
        :type msg_queue_repo: MsgQueueRepository
        :param quote_write_service: 语录写入服务
        :type quote_write_service: QuoteWriteService
        :param user_service: 用户服务
        :type user_service: UserService
        :param group_service: 群组服务
        :type group_service: GroupService
        :param message_filter: LLM 消息筛选器
        :type message_filter: LlmMessageFilter
        :returns: 语录收集服务实例
        :rtype: QuoteCollectionService
        """
        return QuoteCollectionService(
            msg_queue_repo=msg_queue_repo,
            quote_write_service=quote_write_service,
            user_service=user_service,
            group_service=group_service,
            review_service=review_service,
            lock_manager=lock_manager,
            message_filter=message_filter,
        )
