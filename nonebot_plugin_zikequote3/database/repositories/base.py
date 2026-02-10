"""
泛型 Repository 基类，封装通用 CRUD 操作。

所有具体 Repository 继承此基类，通过设置 ``model_class`` 类属性指定操作的 ORM 模型。
方法统一返回 Pydantic DTO，ORM 模型不泄露到 Repository 外部。
使用 ``flush()`` 而非 ``commit()``，事务控制权留给服务层。
"""

from __future__ import annotations

from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")  # SQLAlchemy ORM 模型
CreateDtoT = TypeVar("CreateDtoT")  # Pydantic Create DTO
DtoT = TypeVar("DtoT")  # Pydantic Full DTO


class BaseRepository(Generic[ModelT, CreateDtoT, DtoT]):
    """
    泛型 Repository 基类，封装通用 CRUD 操作。

    子类需设置 ``model_class`` 类属性指定操作的 ORM 模型。
    方法统一返回 Pydantic DTO，ORM 模型不泄露到 Repository 外部。
    使用 ``flush()`` 而非 ``commit()``，事务控制权留给服务层。

    :param session: 异步数据库会话
    :type session: AsyncSession
    """

    model_class: Type[ModelT]  # 子类必须设置

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, dto: CreateDtoT) -> DtoT:
        """
        从 Create DTO 创建记录并返回 Full DTO。

        :param dto: 创建 DTO
        :type dto: CreateDtoT
        :returns: 完整 DTO
        :rtype: DtoT
        """
        instance = self.model_class.from_create_dto(dto)  # type: ignore[attr-defined]
        self._session.add(instance)
        await self._session.flush()
        return instance.to_dto()  # type: ignore[attr-defined]

    async def get_by_id(self, id_value: Any) -> Optional[DtoT]:
        """
        按主键查询，利用 identity map 缓存。

        :param id_value: 主键值
        :type id_value: Any
        :returns: 对应的 DTO，不存在时返回 ``None``
        :rtype: Optional[DtoT]
        """
        instance = await self._session.get(self.model_class, id_value)
        return instance.to_dto() if instance else None  # type: ignore[union-attr]

    async def delete_by_id(self, id_value: Any) -> bool:
        """
        按主键删除，返回是否成功。

        :param id_value: 主键值
        :type id_value: Any
        :returns: 删除成功返回 ``True``，记录不存在返回 ``False``
        :rtype: bool
        """
        instance = await self._session.get(self.model_class, id_value)
        if instance:
            await self._session.delete(instance)
            await self._session.flush()
            return True
        return False

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[DtoT]:
        """
        分页查询所有记录。

        :param limit: 最大返回数量，默认 100
        :type limit: int
        :param offset: 偏移量，默认 0
        :type offset: int
        :returns: DTO 序列
        :rtype: Sequence[DtoT]
        """
        stmt = select(self.model_class).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]  # type: ignore[union-attr]

    async def count(self) -> int:
        """
        统计记录总数。

        :returns: 记录总数
        :rtype: int
        """
        stmt = select(func.count()).select_from(self.model_class)  # type: ignore[arg-type]
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists_by_id(self, id_value: Any) -> bool:
        """
        按主键检查记录是否存在。

        :param id_value: 主键值
        :type id_value: Any
        :returns: 存在返回 ``True``，否则返回 ``False``
        :rtype: bool
        """
        instance = await self._session.get(self.model_class, id_value)
        return instance is not None
