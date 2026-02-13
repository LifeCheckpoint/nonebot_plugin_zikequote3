"""
GroupService —— 群组领域服务。

合并原模块：
- ``group_basic_service.py``        群组存在性检查
- ``group_info_service.py``         群组信息更新
- ``group_relationship_service.py`` 群成员关系管理

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

from nonebot import logger
from typing import Optional, Sequence

from ..database.models.group_members import GroupMember
from ..database.models.group_nicknames import GroupNickname
from ..database.models.groups import Group
from ..database.repositories.group_member_repository import GroupMemberRepository
from ..database.repositories.group_nickname_repository import GroupNicknameRepository
from ..database.repositories.group_repository import GroupRepository
from ..exceptions import ResourceNotFoundError

class GroupService:
    """
    群组领域服务，通过构造函数注入 Repository 依赖。

    :param group_repo: 群组仓储实例
    :type group_repo: GroupRepository
    :param group_member_repo: 群成员仓储实例
    :type group_member_repo: GroupMemberRepository
    :param group_nickname_repo: 群名片仓储实例
    :type group_nickname_repo: GroupNicknameRepository
    """

    def __init__(
        self,
        group_repo: GroupRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
    ) -> None:
        self._group_repo = group_repo
        self._group_member_repo = group_member_repo
        self._group_nickname_repo = group_nickname_repo

    # ------------------------------------------------------------------ #
    #  群组基础操作
    # ------------------------------------------------------------------ #

    async def get_or_create_group(self, group_id: str, name: str) -> Group:
        """
        获取群组，不存在则创建。

        :param group_id: 群组 ID
        :type group_id: str
        :param name: 群组名称
        :type name: str
        :returns: 群组对象
        :rtype: Group
        """
        return await self._group_repo.update_or_create_group(group_id, name)

    async def get_group(self, group_id: str) -> Optional[Group]:
        """
        获取群组信息，不存在返回 ``None``。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 群组对象，不存在返回 ``None``
        :rtype: Optional[Group]
        """
        return await self._group_repo.get_group_by_id(group_id)

    async def group_exists(self, group_id: str) -> bool:
        """
        检查群组是否存在。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 是否存在
        :rtype: bool
        """
        return await self._group_repo.group_exists(group_id)

    async def update_group_name(self, group_id: str, name: str) -> None:
        """
        更新群组名称。

        如果群组不存在则自动创建。

        :param group_id: 群组 ID
        :type group_id: str
        :param name: 新的群组名称
        :type name: str
        """
        await self._group_repo.update_or_create_group(group_id, name)
        logger.info("群 %s 名称已更新为 %s", group_id, name)

    # ------------------------------------------------------------------ #
    #  群成员关系管理（原 group_relationship_service）
    # ------------------------------------------------------------------ #

    async def ensure_member(self, group_id: str, qq_id: str) -> GroupMember:
        """
        确保用户是群成员，不存在则创建映射。

        注意：本方法 **不会** 自动创建群组记录。
        调用方应先确保群组已存在（通过 :meth:`get_or_create_group`）。

        :param group_id: 群组 ID
        :type group_id: str
        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 群成员对象
        :rtype: GroupMember
        """
        return await self._group_member_repo.update_or_create_member(group_id, qq_id)

    async def is_member(self, group_id: str, qq_id: str) -> bool:
        """
        检查用户是否为群成员。

        :param group_id: 群组 ID
        :type group_id: str
        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 是否为群成员
        :rtype: bool
        """
        return await self._group_member_repo.group_member_exists(group_id, qq_id)

    async def get_group_members(self, group_id: str) -> Sequence[GroupMember]:
        """
        获取群成员列表。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 群成员列表
        :rtype: Sequence[GroupMember]
        """
        return await self._group_member_repo.get_members_by_group(group_id)

    async def get_user_groups(self, qq_id: str) -> Sequence[GroupMember]:
        """
        获取用户加入的所有群组关系。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 群组关系列表
        :rtype: Sequence[GroupMember]
        """
        return await self._group_member_repo.get_groups_by_user(qq_id)

    async def count_members(self, group_id: str) -> int:
        """
        统计群成员数量。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 成员数量
        :rtype: int
        """
        return await self._group_member_repo.count_members_by_group(group_id)

    async def remove_member(self, group_id: str, qq_id: str) -> bool:
        """
        移除群成员关系。

        :param group_id: 群组 ID
        :type group_id: str
        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :returns: 是否成功移除
        :rtype: bool
        """
        return await self._group_member_repo.delete_group_member(group_id, qq_id)

    # ------------------------------------------------------------------ #
    #  群名片查询
    # ------------------------------------------------------------------ #

    async def get_group_nicknames(self, group_id: str) -> Sequence[GroupNickname]:
        """
        获取群组中所有名片记录。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 群名片记录列表
        :rtype: Sequence[GroupNickname]
        """
        return await self._group_nickname_repo.get_nicknames_by_group(group_id)

    async def get_group_nickname_stats(self, group_id: str) -> dict:
        """
        获取群组名片统计信息。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 名片统计信息字典
        :rtype: dict
        """
        return await self._group_nickname_repo.get_group_nickname_statistics(group_id)
