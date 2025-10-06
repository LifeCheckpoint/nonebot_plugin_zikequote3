from ....imports import *


def s_get_quote_image_data(image_content_uuid: str) -> bytes:
    """
    获取语录图片数据
    """
    with exception_report("获取语录图片数据"):
        if not qimg_store.exists(image_content_uuid):
            raise FileNotFoundError(f"语录图片文件已丢失: {image_content_uuid}")
        
        return qimg_store.get_path(image_content_uuid).read_bytes()
    

def to_data_uri(data: bytes, mime: str = 'image/png') -> str:
    """
    将二进制数据转换为 Data URI 格式
    """
    import base64
    return f'data:{mime};base64,{base64.b64encode(data).decode()}'
