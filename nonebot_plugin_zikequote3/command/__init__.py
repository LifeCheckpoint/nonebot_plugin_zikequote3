"""
命令层包入口。

重新导出所有命令处理器，使上层可通过 ``from command import *`` 一次性注册全部命令。
"""

from .cmds import *