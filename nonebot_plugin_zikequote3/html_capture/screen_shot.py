"""
HTML 截图模块。

提供将 HTML 内容渲染为图片的底层实现。
"""
from ..paths import PluginPath
from nonebot import logger
from nonebot_plugin_htmlrender import get_new_page
import nonebot_plugin_localstore as store
import uuid

async def _html_img_render(
    html_content: str,
    width: int = 1000, height: int = 800,
    *,
    clean_up: bool = True,
    device_scale_factor: float = 2.0,
    timeout: int = 30000,
    wait: int = 200,
    **page_screenshot_kwargs
) -> bytes:
    """
    渲染 HTML 文件并截图，自动处理临时文件。

    :param html_content: HTML 内容字符串
    :type html_content: str
    :param width: 截图宽度
    :type width: int
    :param height: 截图高度
    :type height: int
    :param clean_up: 是否清理临时文件，默认 ``True``
    :type clean_up: bool
    :param device_scale_factor: 设备缩放因子，默认 ``2.0``
    :type device_scale_factor: float
    :param timeout: 超时时间（毫秒），默认 ``30000``
    :type timeout: int
    :param wait: 页面加载后等待时间（毫秒），默认 ``200``
    :type wait: int
    :param page_screenshot_kwargs: 传递给 ``page.screenshot()`` 的额外参数
    :returns: 截图结果字节
    :rtype: bytes
    """

    # 获取临时文件名
    temp_file_name = uuid.uuid4().hex
    temp_html = PluginPath.data_cache_path / f"{temp_file_name}.html"
    temp_image = PluginPath.data_cache_path / f"{temp_file_name}.png"

    # html 文件生成
    try:
        PluginPath.data_cache_path.mkdir(parents=True, exist_ok=True)
        temp_html.write_text(html_content, encoding="utf-8")
    except Exception as e:
        temp_html.unlink(missing_ok=True)
        logger.error(f"生成 HTML 文件失败: {temp_html}")
        raise

    # 截图
    try:
        async with get_new_page(device_scale_factor=device_scale_factor, viewport={"width": width, "height": height}) as page:
            await page.goto(temp_html.absolute().as_uri(), wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(wait)
            img_bytes = await page.screenshot(timeout=timeout, full_page=True, path=temp_image, **page_screenshot_kwargs)
    except Exception as e:
        logger.error(f"渲染 HTML 截图失败: {temp_html}")
        raise

    # 清理临时文件
    if clean_up:
        temp_html.unlink(missing_ok=True)
        temp_image.unlink(missing_ok=True)

    return img_bytes