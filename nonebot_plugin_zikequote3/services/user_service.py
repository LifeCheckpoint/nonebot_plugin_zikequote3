"""
UserService —— 用户领域服务。

合并原模块：
- ``user_service.py``          用户基础操作 / 搜索
- ``personal_info_service.py`` 昵称 & 群名片缓存同步
- ``avatar_service.py``        头像获取
- ``user_parser_service.py``   纯数据查询部分（Event 解析留在命令层）

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

import aiohttp
from aiohttp import ClientTimeout

from ..database.models.group_members import GroupMember
from ..database.models.group_nicknames import GroupNickname
from ..database.models.user_nicknames import UserNickname
from ..database.models.users import User
from ..database.repositories.group_member_repository import GroupMemberRepository
from ..database.repositories.group_nickname_repository import GroupNicknameRepository
from ..database.repositories.user_nickname_repository import UserNicknameRepository
from ..database.repositories.user_repository import UserRepository
from ..exceptions import UserNotFoundError

logger = logging.getLogger(__name__)


class UserService:
    """
    用户领域服务，通过构造函数注入 Repository 依赖。

    :param user_repo: 用户仓储实例
    :type user_repo: UserRepository
    :param user_nickname_repo: 用户昵称仓储实例
    :type user_nickname_repo: UserNicknameRepository
    :param group_nickname_repo: 群昵称仓储实例
    :type group_nickname_repo: GroupNicknameRepository
    :param group_member_repo: 群成员仓储实例
    :type group_member_repo: GroupMemberRepository
    """

    def __init__(
        self,
        user_repo: UserRepository,
        user_nickname_repo: UserNicknameRepository,
        group_nickname_repo: GroupNicknameRepository,
        group_member_repo: GroupMemberRepository,
    ) -> None:
        self._user_repo = user_repo
        self._user_nickname_repo = user_nickname_repo
        self._group_nickname_repo = group_nickname_repo
        self._group_member_repo = group_member_repo

    # ------------------------------------------------------------------ #
    #  用户基础操作
    # ------------------------------------------------------------------ #

    async def get_or_create_user(self, qq_id: str) -> User:
        """
        获取用户，不存在则创建。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 用户对象
        :rtype: User
        """
        user = await self._user_repo.get_by_qq_id(qq_id)
        if user is not None:
            return user
        return await self._user_repo.create_user(qq_id)

    async def get_user_info(self, qq_id: str) -> Optional[User]:
        """
        获取用户信息，不存在返回 ``None``。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 用户对象，不存在返回 ``None``
        :rtype: Optional[User]
        """
        return await self._user_repo.get_by_qq_id(qq_id)

    async def user_exists(self, qq_id: str) -> bool:
        """
        检查用户是否存在。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 用户是否存在
        :rtype: bool
        """
        return await self._user_repo.user_exists(qq_id)

    # ------------------------------------------------------------------ #
    #  昵称 / 群名片查询
    # ------------------------------------------------------------------ #

    async def get_current_nickname(self, qq_id: str) -> Optional[str]:
        """
        获取用户当前昵称，无则返回 ``None``。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 当前昵称，无则返回 ``None``
        :rtype: Optional[str]
        """
        nick = await self._user_nickname_repo.get_current_nickname(qq_id)
        return nick.name if nick else None

    async def get_current_group_card(self, qq_id: str, group_id: str) -> Optional[str]:
        """
        获取用户在指定群的当前群名片。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param group_id: 群组 ID
        :type group_id: str
        :returns: 当前群名片，无则返回 ``None``
        :rtype: Optional[str]
        """
        return await self._group_nickname_repo.get_current_group_nickname(qq_id, group_id)

    async def get_display_name(self, qq_id: str, group_id: Optional[str] = None) -> str:
        """
        获取用户显示名称。

        优先级：群名片 > 昵称 > QQ 号。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param group_id: 群组 ID，提供时优先使用群名片
        :type group_id: Optional[str]
        :returns: 显示名称
        :rtype: str
        """
        if group_id is not None:
            card = await self.get_current_group_card(qq_id, group_id)
            if card:
                return card

        nickname = await self.get_current_nickname(qq_id)
        if nickname:
            return nickname

        return qq_id

    async def get_all_nicknames(self, qq_id: str) -> Sequence[UserNickname]:
        """
        获取用户所有昵称记录。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 昵称记录列表
        :rtype: Sequence[UserNickname]
        """
        return await self._user_nickname_repo.get_all_nicknames(qq_id)

    async def get_all_group_nicknames(
        self, qq_id: str, group_id: str
    ) -> Sequence[GroupNickname]:
        """
        获取用户在指定群的所有群名片记录。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param group_id: 群组 ID
        :type group_id: str
        :returns: 群名片记录列表
        :rtype: Sequence[GroupNickname]
        """
        return await self._group_nickname_repo.get_all_group_nicknames(qq_id, group_id)

    # ------------------------------------------------------------------ #
    #  昵称 / 群名片同步（原 personal_info_service 逻辑）
    # ------------------------------------------------------------------ #

    async def sync_nickname(self, qq_id: str, nickname: str) -> None:
        """
        同步用户昵称缓存。

        如果当前昵称与传入值不同，则更新。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param nickname: 新昵称
        :type nickname: str
        """
        current = await self._user_nickname_repo.get_current_nickname(qq_id)
        current_name = current.name if current else None
        if current_name != nickname:
            await self._user_nickname_repo.set_current_nickname(qq_id, nickname)
            logger.info("用户 %s 昵称缓存已更新: %s -> %s", qq_id, current_name, nickname)

    async def sync_group_card(self, qq_id: str, group_id: str, card: str) -> None:
        """
        同步用户群名片缓存。

        如果当前群名片与传入值不同，则更新。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param group_id: 群组 ID
        :type group_id: str
        :param card: 新群名片
        :type card: str
        """
        current_card = await self._group_nickname_repo.get_current_group_nickname(
            qq_id, group_id
        )
        if current_card != card:
            await self._group_nickname_repo.set_current_group_nickname(
                qq_id, group_id, card
            )
            logger.info(
                "用户 %s 在群 %s 群名片缓存已更新: %s -> %s",
                qq_id, group_id, current_card, card,
            )

    # ------------------------------------------------------------------ #
    #  用户搜索（原 user_service.py 搜索逻辑）
    # ------------------------------------------------------------------ #

    async def search_users_by_name(
        self, name: str, group_id: Optional[str] = None, *, exact: bool = True
    ) -> list[str]:
        """
        通用搜索用户。

        搜索优先级：正在使用群名片 > 正在使用昵称 > 曾用名片 > 曾用昵称。

        :param name: 搜索关键词
        :type name: str
        :param group_id: 群组 ID，提供时启用群名片搜索
        :type group_id: Optional[str]
        :param exact: 是否精确匹配，默认 ``True``
        :type exact: bool
        :returns: 同一优先级内匹配到的 QQ 号列表
        :rtype: list[str]
        """
        pattern = name if exact else f"%{name}%"

        # 1. 正在使用的群名片
        if group_id is not None:
            results = await self._search_by_current_card(pattern, group_id)
            if results:
                return results

        # 2. 正在使用的昵称
        results = await self._search_by_current_nickname(pattern)
        if results:
            return results

        # 3. 曾用群名片
        if group_id is not None:
            results = await self._search_by_past_card(pattern, group_id)
            if results:
                return results

        # 4. 曾用昵称
        return await self._search_by_past_nickname(pattern)

    async def _search_by_current_card(self, pattern: str, group_id: str) -> list[str]:
        nicks = await self._group_nickname_repo.search_users_by_nickname_in_group(
            name_pattern=pattern, group_id=group_id,
        )
        return [n.qq_id for n in nicks if n.current_using]

    async def _search_by_current_nickname(self, pattern: str) -> list[str]:
        nicks = await self._user_nickname_repo.search_user_by_nickname(name_pattern=pattern)
        return [n.qq_id for n in nicks if n.current_using]

    async def _search_by_past_card(self, pattern: str, group_id: str) -> list[str]:
        nicks = await self._group_nickname_repo.search_users_by_nickname_in_group(
            name_pattern=pattern, group_id=group_id,
        )
        return [n.qq_id for n in nicks if not n.current_using]

    async def _search_by_past_nickname(self, pattern: str) -> list[str]:
        nicks = await self._user_nickname_repo.search_user_by_nickname(name_pattern=pattern)
        return [n.qq_id for n in nicks if not n.current_using]

    # ------------------------------------------------------------------ #
    #  用户解析辅助（纯数据查询，Event 解析留在命令层）
    # ------------------------------------------------------------------ #

    async def resolve_user(
        self,
        key: str,
        group_id: Optional[str] = None,
        *,
        exact: bool = True,
    ) -> list[str]:
        """
        根据文本 key 解析用户 QQ 号列表。

        - 纯数字 → 直接作为 QQ 号返回
        - 非数字 → 按昵称搜索

        **不处理** ``@`` 段和 Event，这些由命令层负责。

        :param key: 搜索文本（QQ 号或昵称）
        :type key: str
        :param group_id: 群组 ID，提供时启用群名片搜索
        :type group_id: Optional[str]
        :param exact: 是否精确匹配，默认 ``True``
        :type exact: bool
        :returns: 匹配到的 QQ 号列表
        :rtype: list[str]
        """
        key = key.strip()
        if not key:
            return []
        if key.isnumeric():
            return [key]
        return await self.search_users_by_name(key, group_id, exact=exact)

    # ------------------------------------------------------------------ #
    #  头像管理（原 avatar_service.py）
    # ------------------------------------------------------------------ #

    async def fetch_avatar(self, qq_id: str) -> bytes:
        """
        从 QQ 头像 CDN 获取用户头像。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 头像字节数据
        :rtype: bytes
        :raises aiohttp.ClientError: 网络请求失败时
        """
        url = f"https://q.qlogo.cn/headimg_dl?dst_uin={qq_id}&spec=640&img_type=jpg"
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def update_avatar(self, qq_id: str) -> None:
        """
        获取并持久化用户头像。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        """
        avatar_bytes = await self.fetch_avatar(qq_id)
        await self._user_repo.update_user(qq_id, avatar=avatar_bytes)

    async def get_avatar(self, qq_id: str) -> Optional[bytes]:
        """
        获取用户头像（优先数据库缓存，缓存未命中则从 CDN 拉取并保存）。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 头像字节数据，获取失败返回 ``None``
        :rtype: Optional[bytes]
        """
        user = await self._user_repo.get_by_qq_id(qq_id)
        if user and user.avatar:
            return user.avatar
        try:
            avatar_bytes = await self.fetch_avatar(qq_id)
        except Exception:
            logger.warning("获取用户 %s 头像失败", qq_id, exc_info=True)
            return None
        await self._user_repo.update_user(qq_id, avatar=avatar_bytes)
        return avatar_bytes
