"""
Base64 编码工具。

提供二进制数据到 Data URI 格式的转换功能。
"""


def to_data_uri(data: bytes, mime: str = "image/png") -> str:
    """
    将二进制数据转换为 Data URI 格式。

    :param data: 待编码的二进制数据
    :type data: bytes
    :param mime: MIME 类型，默认为 ``"image/png"``
    :type mime: str
    :returns: Data URI 格式字符串
    :rtype: str
    """
    import base64
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"
