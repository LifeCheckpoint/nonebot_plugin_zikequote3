"""
SQLAlchemy 2.0 声明式基类。

所有 ORM 模型都应继承此 Base 类。
"""

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    ORM 模型基类。

    所有 ORM 模型都应继承此类，提供统一的 ``__repr__`` 实现。
    """

    def __repr__(self) -> str:
        """
        返回包含主键信息的字符串表示。

        :returns: 模型实例的字符串表示
        :rtype: str
        """
        # 通过 SQLAlchemy inspect 获取主键列名
        mapper = sa_inspect(type(self))
        pk_attrs: list[str] = [
            col.key for col in mapper.primary_key if col.key is not None
        ]
        parts: list[str] = []
        for attr in pk_attrs:
            val = getattr(self, attr, "?")
            parts.append(f"{attr}={val!r}")
        return f"<{type(self).__name__}({', '.join(parts)})>"
