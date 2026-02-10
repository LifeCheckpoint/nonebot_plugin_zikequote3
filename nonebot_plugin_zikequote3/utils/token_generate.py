"""
Token 生成与管理工具。

提供基于内存的一次性 Token 生成、验证与过期清理功能。
"""

import time
import secrets
import threading
from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field, PrivateAttr


class TokenMetadata(BaseModel):
    """
    Token 元数据模型。

    记录单个 Token 的剩余使用次数和过期时间。
    """

    remaining_uses: int = Field(description="剩余使用次数")
    expires_at: float = Field(description="过期时间戳")

class TokenManager(BaseModel):
    """
    Token 管理器。

    基于内存的有状态 Token 存储，支持生成、验证消耗和过期清理。
    线程安全，使用 ``RLock`` 保护内部状态。
    """

    _tokens: Dict[str, TokenMetadata] = PrivateAttr(default_factory=dict)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    def generate(self, max_uses: int = 1, ttl: int = 60) -> str:
        """
        生成一个 Token。

        :param max_uses: 最大使用次数，默认 1
        :type max_uses: int
        :param ttl: Token 有效期（秒），默认 60
        :type ttl: int
        :returns: 生成的 URL 安全 Token 字符串
        :rtype: str
        """
        token = secrets.token_urlsafe(8)
        expires_at = time.time() + ttl
        
        metadata = TokenMetadata(
            remaining_uses=max_uses,
            expires_at=expires_at
        )
        
        with self._lock:
            self._tokens[token] = metadata
        return token

    def verify_and_use(self, token: str) -> Tuple[bool, str]:
        """
        验证并消耗一次 Token。

        :param token: 待验证的 Token 字符串
        :type token: str
        :returns: ``(是否成功, 描述信息)`` 元组
        :rtype: Tuple[bool, str]
        """
        now = time.time()
        
        with self._lock:
            metadata: Optional[TokenMetadata] = self._tokens.get(token)

            if not metadata:
                return False, "Token 不存在"

            # 校验过期
            if now > metadata.expires_at:
                del self._tokens[token]
                return False, "Token 已过期"

            # 校验次数
            if metadata.remaining_uses <= 0:
                del self._tokens[token]
                return False, "Token 使用超限制"

            # 消耗次数
            metadata.remaining_uses -= 1
            
            # 如果次数用完，立即删除
            if metadata.remaining_uses <= 0:
                del self._tokens[token]
                
            return True, "成功"

    def cleanup(self) -> int:
        """
        清理所有已过期的 Token。

        :returns: 被清理的过期 Token 数量
        :rtype: int
        """
        now = time.time()
        with self._lock:
            expired_tokens = [
                t for t, meta in self._tokens.items() 
                if now > meta.expires_at
            ]
            for t in expired_tokens:
                del self._tokens[t]
        return len(expired_tokens)

    def get_status(self) -> Dict[str, dict]:
        """
        将当前所有 Token 导出为字典。

        :returns: Token 字符串到元数据字典的映射
        :rtype: Dict[str, dict]
        """
        with self._lock:
            return {k: v.model_dump() for k, v in self._tokens.items()}
