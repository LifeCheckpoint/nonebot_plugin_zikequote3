from .screenshot import async_generate_screenshot


async def html_img_render(
    html_content: str,
    cache_dir,
    width: int = 1000,
    height: int = 800,
) -> bytes:
    from .html_parser import html_img_render as _html_img_render

    return await _html_img_render(
        html_content,
        cache_dir,
        width=width,
        height=height,
    )


async def parse_md2html(markdown_text: str) -> str:
    from .html_parser import parse_md2html as _parse_md2html

    return await _parse_md2html(markdown_text)