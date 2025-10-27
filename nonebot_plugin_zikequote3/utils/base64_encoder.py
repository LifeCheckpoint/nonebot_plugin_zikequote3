def to_data_uri(data: bytes, mime: str = "image/png") -> str:
    """
    将二进制数据转换为 Data URI 格式
    """
    import base64
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"
