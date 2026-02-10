"""
UserNicknameRepository —— 用户昵称数据仓储。

覆盖原 ``UserNicknameDAO`` 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, select, update

from ..models.user_nicknames import UserNickname, UserNicknameCreate
from ..sa.models.user_nickname import UserNicknameModel
from .base import BaseRepository


class UserNicknameRepository(BaseRepository[UserNicknameModel, UserNicknameCreate, UserNickname]):
    """
    用户昵称 Repository，封装用户昵称表的数据访问操作。

    :param session: 异步数据库会话
    :type session: AsyncSession
    """

    model_class = UserNicknameModel

    # ---- 创建 ----

    async def add_nickname(self, qq_id: str, current_using: bool, name: str) -> UserNickname:
        """
        添加用户昵称并返回 DTO。

        :param qq_id: QQ 号
        :type qq_id: str
        :param current_using: 是否正在使用
        :type current_using: bool
        :param name: 昵称
        :type name: str
        :returns: 用户昵称 DTO
        :rtype: UserNickname
        """
        dto = UserNicknameCreate(qq_id=qq_id, current_using=current_using, name=name)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_current_nickname(self, qq_id: str) -> Optional[UserNickname]:
        """
        获取用户当前使用的昵称。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 用户昵称 DTO，不存在时返回 ``None``
        :rtype: Optional[UserNickname]
        """
        stmt = select(UserNicknameModel).where(
            UserNicknameModel.qq_id == qq_id,
            UserNicknameModel.current_using == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return row.to_dto() if row else None

    async def get_all_nicknames(self, qq_id: str) -> Sequence[UserNickname]:
        """
        获取用户所有昵称记录。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 用户昵称 DTO 序列
        :rtype: Sequence[UserNickname]
        """
        stmt = select(UserNicknameModel).where(UserNicknameModel.qq_id == qq_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_user_by_nickname(self, name_pattern: str) -> Sequence[UserNickname]:
        """
        通过昵称模式搜索用户（LIKE 匹配）。

        :param name_pattern: LIKE 匹配模式
        :type name_pattern: str
        :returns: 匹配的用户昵称 DTO 序列
        :rtype: Sequence[UserNickname]
        """
        stmt = select(UserNicknameModel).where(
            UserNicknameModel.name.like(name_pattern)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    # ---- 更新 ----

    async def set_current_nickname(self, qq_id: str, name: str) -> bool:
        """
        设置用户当前昵称。

        先取消所有 current_using，再设置目标昵称；若不存在则创建。

        :param qq_id: QQ 号
        :type qq_id: str
        :param name: 目标昵称
        :type name: str
        :returns: 操作成功返回 ``True``
        :rtype: bool
        """
        # 1. 取消该用户所有 current_using
        stmt_clear = (
            update(UserNicknameModel)
            .where(UserNicknameModel.qq_id == qq_id)
            .values(current_using=False)
        )
        await self._session.execute(stmt_clear)

        # 2. 设置目标昵称为 current_using
        stmt_set = (
            update(UserNicknameModel)
            .where(
                UserNicknameModel.qq_id == qq_id,
                UserNicknameModel.name == name,
            )
            .values(current_using=True)
        )
        result = await self._session.execute(stmt_set)

        # 3. 若目标昵称不存在，则创建
        if result.rowcount == 0:  # type: ignore[union-attr]
            instance = UserNicknameModel(qq_id=qq_id, current_using=True, name=name)
            self._session.add(instance)

        await self._session.flush()
        return True

    # ---- 删除 ----

    async def remove_nickname(self, qq_id: str, name: str) -> bool:
        """
        删除指定昵称。

        :param qq_id: QQ 号
        :type qq_id: str
        :param name: 昵称
        :type name: str
        :returns: 删除成功返回 ``True``，不存在返回 ``False``
        :rtype: bool
        """
        stmt = select(UserNicknameModel).where(
            UserNicknameModel.qq_id == qq_id,
            UserNicknameModel.name == name,
        )
        result = await self._session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            await self._session.delete(instance)
            await self._session.flush()
            return True
        return False

    async def clear_user_nicknames(self, qq_id: str) -> bool:
        """
        清空用户所有昵称。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 操作成功返回 ``True``
        :rtype: bool
        """
        stmt = delete(UserNicknameModel).where(UserNicknameModel.qq_id == qq_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True
