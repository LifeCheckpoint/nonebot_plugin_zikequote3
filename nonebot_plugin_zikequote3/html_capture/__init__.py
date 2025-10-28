from ..imports import default_cfg
from .screen_shot import _html_img_render

def html_img_render(
    html_content: str,
    width: int = 1000,
    height: int = 800,
    *,
    wait: int = 200,
):
    return _html_img_render(
        html_content,
        width=width,
        height=height,
        clean_up=True,
        device_scale_factor=default_cfg.showcase.render_device_factor,
        timeout=30000,
        wait=wait,
    )