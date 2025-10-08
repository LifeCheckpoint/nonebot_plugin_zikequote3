from typing import Any, Dict

class LockIsHeldError(Exception):
    """当尝试获取一个已被持有的 KeyedRejectingLock 时抛出此异常。"""
    pass

class KeyedRejectingLock:
    """
    基于键的非阻塞异步锁。对于同一个键，当锁被持有时，任何新的获取请求都会立即失败并抛出 LockIsHeldError 异常。不同键之间的锁互不影响。
    """
    def __init__(self):
        self._locks: Dict[Any, str] = {}

    def is_locked(self, credential: Any) -> bool:
        """检查特定凭证的锁当前是否被持有。"""
        return credential in self._locks

    def for_key(self, credential: Any, locked_msg: str = ""):
        """
        为指定的凭证（键）返回一个上下文管理器。
        """
        if not locked_msg:
            locked_msg = f"凭证 '{credential}' 对应的锁已被持有。"
        
        return self._KeyedContextManager(self, credential, locked_msg)

    # 上下文管理协议
    class _KeyedContextManager:
        def __init__(self, parent_lock: 'KeyedRejectingLock', credential: Any, locked_msg: str):
            self._parent = parent_lock
            self._credential = credential
            self._locked_msg = locked_msg

        async def __aenter__(self):
            # 检查父锁的字典中是否已存在此凭证的锁
            if self._credential in self._parent._locks:
                # 如果存在，抛出异常，并使用存储的消息
                raise LockIsHeldError(self._parent._locks[self._credential])
            
            # 如果不存在，锁定它，并将消息存入
            self._parent._locks[self._credential] = self._locked_msg
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self._parent._locks.pop(self._credential, None)
            return False
