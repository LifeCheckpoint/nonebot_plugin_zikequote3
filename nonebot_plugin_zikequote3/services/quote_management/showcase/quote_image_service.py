from ....imports import *

def s_get_quote_image_data(image_content_uuid: str) -> bytes:
    """
    获取语录图片数据
    """
    with exception_report("获取语录图片数据"):
        if not qimg_store.exists(image_content_uuid):
            raise FileNotFoundError(f"语录图片文件已丢失: {image_content_uuid}")
        
        return qimg_store.get_path(image_content_uuid).read_bytes()