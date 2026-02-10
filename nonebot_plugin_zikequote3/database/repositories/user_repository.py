"""
UserRepository —— 用户数据仓储。

覆盖原 ``UserDAO`` 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select, update

from ..models.users import User, UserCreate
from ..sa.models.user import UserModel
from .base import BaseRepository


class UserRepository(BaseRepository[UserModel, UserCreate, User]):
    """
    用户 Repository，封装用户表的数据访问操作。

    :param session: 异步数据库会话
    :type session: AsyncSession
    """

    model_class = UserModel

    # ---- 便捷创建 ----

    async def create_user(self, qq_id: str, avatar: Optional[bytes] = None) -> User:
        """
        创建新用户并返回 DTO。

        :param qq_id: QQ 号
        :type qq_id: str
        :param avatar: 头像二进制数据，默认为 ``None``
        :type avatar: Optional[bytes]
        :returns: 用户 DTO
        :rtype: User
        """
        dto = UserCreate(qq_id=qq_id, avatar=avatar)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_by_qq_id(self, qq_id: str) -> Optional[User]:
        """
        按 QQ ID 查询用户。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 用户 DTO，不存在时返回 ``None``
        :rtype: Optional[User]
        """
        return await self.get_by_id(qq_id)

    async def user_exists(self, qq_id: str) -> bool:
        """
        检查用户是否存在。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 存在返回 ``True``
        :rtype: bool
        """
        return await self.exists_by_id(qq_id)

    async def get_users_by_qq_ids(self, qq_ids: list[str]) -> Sequence[User]:
        """
        根据 QQ 号列表批量获取用户。

        :param qq_ids: QQ 号列表
        :type qq_ids: list[str]
        :returns: 用户 DTO 序列
        :rtype: Sequence[User]
        """
        if not qq_ids:
            return []
        stmt = select(UserModel).where(UserModel.qq_id.in_(qq_ids))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_users_with_avatar(self) -> Sequence[User]:
        """
        获取有头像的用户列表。

        :returns: 用户 DTO 序列
        :rtype: Sequence[User]
        """
        stmt = select(UserModel).where(UserModel.avatar.isnot(None))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_users_without_avatar(self) -> Sequence[User]:
        """
        获取没有头像的用户列表。

        :returns: 用户 DTO 序列
        :rtype: Sequence[User]
        """
        stmt = select(UserModel).where(UserModel.avatar.is_(None))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_users(self) -> int:
        """
        统计用户总数。

        :returns: 用户总数
        :rtype: int
        """
        return await self.count()

    # ---- 更新 ----

    async def update_user(self, qq_id: str, avatar: Optional[bytes] = None) -> bool:
        """
        更新用户信息（目前仅支持头像）。

        :param qq_id: QQ 号
        :type qq_id: str
        :param avatar: 新头像二进制数据，默认为 ``None``
        :type avatar: Optional[bytes]
        :returns: 更新成功返回 ``True``
        :rtype: bool
        """
        if avatar is None:
            return True
        stmt = (
            update(UserModel)
            .where(UserModel.qq_id == qq_id)
            .values(avatar=avatar)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    # ---- 删除 ----

    async def delete_user(self, qq_id: str) -> bool:
        """
        删除用户。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 删除成功返回 ``True``
        :rtype: bool
        """
        return await self.delete_by_id(qq_id)

    # ---- 批量操作 ----

    async def batch_create_users(self, users: list[dict]) -> bool:
        """
        批量创建用户。

        :param users: 用户字典列表，每个 dict 包含 ``qq_id`` 和可选 ``avatar``
        :type users: list[dict]
        :returns: 创建成功返回 ``True``
        :rtype: bool
        """
        if not users:
            return True
        instances = [
            UserModel(qq_id=u["qq_id"], avatar=u.get("avatar"))
            for u in users
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True
