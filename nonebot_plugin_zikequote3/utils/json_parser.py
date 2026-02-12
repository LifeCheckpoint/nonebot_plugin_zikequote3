"""
JSON 解析工具。

提供 LLM 输出的 JSON 字符串到 Pydantic 模型的宽松解析功能。
"""

import json
import re
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def _strip_json_comments(text: str) -> str:
    """
    去除 JSON 中的行尾注释（// 和 #），不处理字符串内的情况。

    :param text: 可能包含注释的 JSON 文本
    :type text: str
    :returns: 清理后的文本
    :rtype: str
    """
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        # 简单处理：去除不在引号内的行尾注释
        # 匹配：在引号外的 // 或 # 开头的注释
        cleaned_line = re.sub(r'(?<=[,\]\}\d])\s*(?://|#).*$', '', line)
        cleaned.append(cleaned_line)
    return '\n'.join(cleaned)


def llm_json_parse_model(model_type: Type[T], json_str: str) -> T:
    """
    将 JSON 字符串转换为 Pydantic BaseModel 实例，允许模糊转换。

    自动清理 LLM 输出中常见的代码块标记（如 ````json``）。

    :param model_type: 目标 Pydantic 模型类型
    :type model_type: Type[T]
    :param json_str: JSON 格式的字符串
    :type json_str: str
    :returns: 对应的 Pydantic 模型实例
    :rtype: T
    :raises ValueError: LLM 返回空响应时抛出
    :raises json.JSONDecodeError: JSON 格式错误时抛出
    :raises pydantic.ValidationError: 数据无法转换为指定模型时抛出
    """
    json_str = json_str.strip()
    
    # 清理可能的代码块标记
    code_block_markers = [
        "```json", "```Json", "```JSON", "```"
    ]
    for marker in code_block_markers:
        if json_str.startswith(marker) and json_str.endswith("```"):
            json_str = json_str[len(marker):-3].strip()
            break
    
    # 空字符串检查
    if not json_str:
        raise ValueError("LLM returned empty response")
    
    # 去除行尾注释
    json_str = _strip_json_comments(json_str)
    
    return model_type(**json.loads(json_str))
