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
    渲染 HTML 文件并截图，自动处理临时文件

    Args:
        :param html_content: HTML 内容字符串
        :param width: 截图宽度
        :param height: 截图高度

    Returns:
        :return: 截图结果字节
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
            await page.goto("file://" + str(temp_html.absolute()), wait_until="networkidle", timeout=timeout)
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