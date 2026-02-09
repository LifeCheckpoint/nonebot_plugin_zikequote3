"""
Service 层的 dishka Provider。

注册全部 9 个 Service 类到 REQUEST 作用域。
dishka 自动解析服务间的依赖链（如 QuoteWriteService 依赖 UserService）。
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

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
from ...services.quote_collection_service import QuoteCollectionService
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

    # ---- 无服务间依赖的 Service ---- #

    @provide
    def provide_user_service(
        self,
        user_repo: UserRepository,
        user_nickname_repo: UserNicknameRepository,
        group_nickname_repo: GroupNicknameRepository,
        group_member_repo: GroupMemberRepository,
    ) -> UserService:
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
    ) -> ReviewService:
        return ReviewService(
            review_repo=review_repo,
            quote_repo=quote_repo,
        )

    @provide
    def provide_statistics_service(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
    ) -> StatisticsService:
        return StatisticsService(
            quote_repo=quote_repo,
            group_member_repo=group_member_repo,
        )

    @provide
    def provide_config_service(
        self,
        group_config_repo: GroupConfigRepository,
    ) -> ConfigService:
        return ConfigService(
            group_config_repo=group_config_repo,
        )

    @provide
    def provide_migration_service(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
    ) -> MigrationService:
        return MigrationService(
            quote_repo=quote_repo,
            group_member_repo=group_member_repo,
            group_nickname_repo=group_nickname_repo,
        )

    # ---- 依赖其他 Service 的 Service ---- #

    @provide
    def provide_quote_write_service(
        self,
        quote_repo: QuoteRepository,
        image_repo: ImageRepository,
        mapping_repo: MappingRepository,
        user_service: UserService,
    ) -> QuoteWriteService:
        return QuoteWriteService(
            quote_repo=quote_repo,
            image_repo=image_repo,
            mapping_repo=mapping_repo,
            user_service=user_service,
        )

    @provide
    def provide_quote_read_service(
        self,
        quote_repo: QuoteRepository,
        review_repo: ReviewRepository,
        image_repo: ImageRepository,
        user_service: UserService,
    ) -> QuoteReadService:
        return QuoteReadService(
            quote_repo=quote_repo,
            review_repo=review_repo,
            image_repo=image_repo,
            user_service=user_service,
        )

    @provide
    def provide_quote_collection_service(
        self,
        msg_queue_repo: MsgQueueRepository,
        quote_write_service: QuoteWriteService,
        user_service: UserService,
        group_service: GroupService,
    ) -> QuoteCollectionService:
        return QuoteCollectionService(
            msg_queue_repo=msg_queue_repo,
            quote_write_service=quote_write_service,
            user_service=user_service,
            group_service=group_service,
            # message_filter 为可选依赖，此处不注入
        )
