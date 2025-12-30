import time
import secrets
import threading
from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field, PrivateAttr

class TokenMetadata(BaseModel):
    remaining_uses: int = Field(description="剩余使用次数")
    expires_at: float = Field(description="过期时间戳")

class TokenManager(BaseModel):
    _tokens: Dict[str, TokenMetadata] = PrivateAttr(default_factory=dict)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    def generate(self, max_uses: int = 1, ttl: int = 60) -> str:
        """
        生成一个 Token
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
        验证并消耗一次 Token
        """
        now = time.time()
        
        with self._lock:
            metadata: Optional[TokenMetadata] = self._tokens.get(token)

            if not metadata:
                return False, "Token does not exist"

            # 校验过期
            if now > metadata.expires_at:
                del self._tokens[token]
                return False, "Token has expired"

            # 校验次数
            if metadata.remaining_uses <= 0:
                del self._tokens[token]
                return False, "Token usage limit reached"

            # 消耗次数
            metadata.remaining_uses -= 1
            
            # 如果次数用完，立即删除
            if metadata.remaining_uses <= 0:
                del self._tokens[token]
                
            return True, "Success"

    def cleanup(self) -> int:
        """
        清理所有已过期的 Token
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

    def get_status(self):
        """
        将当前所有 tokens 导出为字典
        """
        with self._lock:
            return {k: v.model_dump() for k, v in self._tokens.items()}
