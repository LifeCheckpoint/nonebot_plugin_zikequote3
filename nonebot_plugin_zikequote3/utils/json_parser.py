"""
JSON 解析工具。

提供 LLM 输出的 JSON 字符串到 Pydantic 模型的宽松解析功能。
"""

import json
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


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
    
    return model_type(**json.loads(json_str))
