"""
数据类型解析工具模块。

提供命令参数中常用数据类型的解析函数，如页码范围解析等。
"""

from typing import Optional, Tuple


def parse_page_range(s: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    解析页码范围字符串为起止页码元组。

    支持单页码（如 ``"3"``）和范围格式（如 ``"2-5"``）。

    :param s: 页码范围字符串，可为 ``None``
    :type s: Optional[str]
    :returns: ``(page_from, page_to)`` 元组，无法解析时对应位置为 ``None``
    :rtype: Tuple[Optional[int], Optional[int]]
    """
    if s is None:
        return (None, None)
    
    s = s.strip()
    if not s:
        return (None, None)
    if "-" in s:
        parts = s.split("-", 1)
        try:
            page_from = int(parts[0])
        except ValueError:
            page_from = None
        try:
            page_to = int(parts[1])
        except ValueError:
            page_to = None
        return (page_from, page_to)
    else:
        try:
            val = int(s)
        except ValueError:
            return (None, None)
        return (val, None)