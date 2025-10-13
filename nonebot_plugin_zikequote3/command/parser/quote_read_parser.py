from ...imports import *
import click


class QuoteSearchArgs(BaseModel):
    qq: Optional[int] = Field(None, description="用于筛选的QQ号")
    search_with_image: bool = Field(True, description="是否搜索包含图片的语录")
    max_result: int = Field(10, ge=1, description="最大返回结果数量，至少为1")
    use_regex: bool = Field(False, description="是否启用正则表达式匹配")
    keyword: str = Field(..., description="搜索的关键词或模式")


quote_query_parser = typer.Typer()


@click.command("查语录")
@click.option('-qq', type=int, default=None, help='筛选特定QQ号的语录')
@click.option('--no-image', '-ni', is_flag=True, flag_value=False, default=True, help='禁用图片语录搜索 (缩写: -ni)')
@click.option('--max-result', '-m', type=click.IntRange(min=1), default=10, show_default=True, help='最大结果数量 (缩写: -m)')
@click.option('-r', '--regex', is_flag=True, default=False, help='启用正则表达式')
@click.argument('keyword_parts', nargs=-1, required=True)
def quote_search_command(qq, search_with_image, max_result, use_regex, keyword_parts):
    """
    解析语录搜索命令的核心逻辑。
    """
    if not keyword_parts:
        raise ValueError("缺少关键词或搜索模式~")
    
    keyword = " ".join(keyword_parts)
    
    with service_exception("解析语录搜索命令验证"):
        return QuoteSearchArgs(
            qq=qq,
            search_with_image=search_with_image,
            max_result=max_result,
            use_regex=use_regex,
            keyword=keyword
        )
