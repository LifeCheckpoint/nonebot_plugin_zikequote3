from ....imports import *


def s_get_quote_image_data(image_content_uuid: str) -> bytes:
    """
    获取语录图片数据
    """
    with service_exception("获取语录图片数据"):
        if not qimg_store.exists(image_content_uuid):
            raise FileNotFoundError(f"语录图片文件已丢失: {image_content_uuid}")
        
        return qimg_store.get_path(image_content_uuid).read_bytes()
    

def to_data_uri(data: bytes, mime: str = 'image/png') -> str:
    """
    将二进制数据转换为 Data URI 格式
    """
    import base64
    return f'data:{mime};base64,{base64.b64encode(data).decode()}'


async def s_get_image_data_from_file_or_url(url: str) -> bytes:
    """
    从文件路径或 URL 获取图片数据
    """
    import httpx

    if url.startswith("http"):
        async with service_exception_a("获取网络图片数据"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content

    if Path(url).exists():
        async with service_exception_a("获取缓存图片数据"):
            return Path(url).read_bytes()
    
    async with service_exception_a("获取图片数据"):
        raise ValueError("无效的图片路径或 URL")


async def s_image_info_register(image_data: bytes, original_url_or_file: str):
    """
    向本地文件储存图片，并在数据库进行注册
    """
    async with service_exception_a("注册语录图片信息"):
        uuid = qimg_store.upload(image_data)
        suc = db.dao.get_image_dao().create_image(
            uuid=uuid,
            original_filename=original_url_or_file,
            stored_filename=qimg_store.get_path(uuid).name,
            file_path=str(qimg_store.get_path(uuid)),
            checksum_sha256=qimg_store.get_sha256(uuid),
        )

        if not suc:
            raise RuntimeError("数据库返回信息，注册语录图片信息失败")
    
        return uuid