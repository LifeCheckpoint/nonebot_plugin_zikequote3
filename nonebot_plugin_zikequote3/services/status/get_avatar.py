from ...imports import *
import aiohttp

async def get_user_avatar(qq: str) -> bytes:
    """
    获取用户头像
    """
    url = f"http://q.qlogo.cn/headimg_dl?dst_uin={qq}&spec=640&img_type=jpg"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()
    