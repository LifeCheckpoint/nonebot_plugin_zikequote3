"""
dishka 依赖注入集成层。

提供 Provider 定义、Container 组装和 NoneBot2 桥接。
"""

from .container import create_container

__all__ = ["create_container"]
