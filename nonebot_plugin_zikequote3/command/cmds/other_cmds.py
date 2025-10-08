from ...imports import *
from ..command_definition import *


@matcher_get_privacy.handle()
async def f_get_privacy():
    """
    获取隐私政策
    """
    from ...templates import md
    from ...html_capture import html_img_render
    privacy_markdown = module_resources_root / "privacy.md"

    if not privacy_markdown.exists():
        await matcher_get_privacy.finish("隐私政策文件不存在，请联系管理员处理（＞人＜；）")

    try:
        html = md.render_markdown(privacy_markdown.read_text(encoding="utf-8"))
        img = await html_img_render(html, cache_dir=module_render_image_root, width=800)
        await matcher_get_privacy.finish(MsgSeg.image(img))
    except:
        await matcher_get_privacy.finish(privacy_markdown.read_text(encoding="utf-8"))
    