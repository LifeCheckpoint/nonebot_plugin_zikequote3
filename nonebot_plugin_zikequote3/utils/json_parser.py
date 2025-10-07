import json
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def llm_json_parse_model(model_type: Type[T], json_str: str) -> T:
    """
    将 JSON 字符串转换为 Pydantic BaseModel 实例，允许模糊转换
    
    Args:
        model_type: Pydantic 模型类型
        json_str: JSON 格式的字符串
    
    Returns:
        对应的 Pydantic 模型实例
    
    Raises:
        json.JSONDecodeError: 如果 JSON 格式错误
        pydantic.ValidationError: 如果数据无法转换为指定的 Pydantic 模型
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
