"""向量搜索可选能力契约。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..database.models.quotes import Quote
from ..exceptions import OperationError

_DEFAULT_VECTOR_UNAVAILABLE_REASON = (
    "向量搜索基础设施未就绪，请检查启动期全局 Embedding 配置（model、base_url、api_key_path）"
)


@dataclass(frozen=True, slots=True)
class VectorCapabilityStatus:
    """描述向量能力当前是否可用及其诊断原因。"""

    available: bool
    reason: str | None = None

    @classmethod
    def available_status(cls) -> "VectorCapabilityStatus":
        """构造可用状态。"""
        return cls(available=True, reason=None)

    @classmethod
    def unavailable_status(
        cls,
        reason: str | None = None,
    ) -> "VectorCapabilityStatus":
        """构造不可用状态。"""
        return cls(
            available=False,
            reason=reason or _DEFAULT_VECTOR_UNAVAILABLE_REASON,
        )


class VectorSearchCapability(ABC):
    """稳定的向量搜索可选能力契约。"""

    @abstractmethod
    def get_status(self) -> VectorCapabilityStatus:
        """获取当前能力状态。"""

    def get_unavailable_reason(self) -> str | None:
        """获取不可用原因；可用时返回 ``None``。"""
        status = self.get_status()
        if status.available:
            return None
        return status.reason or _DEFAULT_VECTOR_UNAVAILABLE_REASON

    def _raise_unavailable(self) -> None:
        """按统一契约抛出能力不可用错误。"""
        raise OperationError(
            self.get_unavailable_reason() or _DEFAULT_VECTOR_UNAVAILABLE_REASON
        )

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        group_id: str,
        *,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[Quote, float]]:
        """执行语义搜索。"""

    @abstractmethod
    async def index_quote(self, quote: Quote) -> None:
        """为单条语录建立向量索引。"""

    @abstractmethod
    async def remove_quote(self, quote_id: str) -> None:
        """删除单条语录的向量索引。"""

    @abstractmethod
    async def reindex_all(self, group_id: Optional[str] = None) -> int:
        """重建向量索引。"""

    @abstractmethod
    async def check_model_consistency(self) -> bool:
        """检查向量模型一致性。"""

    @abstractmethod
    async def is_available(self) -> bool:
        """检查基础设施是否处于可运行状态。"""

    @abstractmethod
    async def get_index_count(self) -> int:
        """获取当前索引中的向量条数。"""


class UnavailableVectorSearchService(VectorSearchCapability):
    """能力不可用时使用的稳定占位实现。"""

    def __init__(self, reason: str | None = None) -> None:
        self._status = VectorCapabilityStatus.unavailable_status(reason)

    def get_status(self) -> VectorCapabilityStatus:
        """返回固定的不可用状态。"""
        return self._status

    async def semantic_search(
        self,
        query: str,
        group_id: str,
        *,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[Quote, float]]:
        self._raise_unavailable()

    async def index_quote(self, quote: Quote) -> None:
        self._raise_unavailable()

    async def remove_quote(self, quote_id: str) -> None:
        self._raise_unavailable()

    async def reindex_all(self, group_id: Optional[str] = None) -> int:
        self._raise_unavailable()

    async def check_model_consistency(self) -> bool:
        self._raise_unavailable()

    async def is_available(self) -> bool:
        return False

    async def get_index_count(self) -> int:
        self._raise_unavailable()
