from ...imports import *
from .range_param_type import PARAMTYPE_RANGE
import click

class QuoteListCommandParams(BaseModel):
    page_from: Optional[int] = Field(..., description="起始页码")
    page_to: Optional[int] = Field(..., description="结束页码")
    name: Optional[str] = Field(..., description="可能含空格的名称")


quote_statistics_parser = typer.Typer()


@quote_statistics_parser.command("语录列表")
def quote_list_command(
    args: List[str] = typer.Argument(..., help="格式: [页码/范围] <名称>")
):
    """
    查询语录列表。
    
    使用方法:
    - /语录列表
    - /语录列表 <名称>
    - /语录列表 <页码> <名称>
    - /语录列表 <起始页码-结束页码> <名称>
    """

    # 去除命令头
    args = args[1:]

    # /语录列表
    if not args:
        return QuoteListCommandParams(page_from=None, page_to=None, name=None)
    
    page_range_str = args[0]
    name_parts = args[1:]
    
    page_range_obj = None
    
    # 尝试将第一个参数解析为页码范围
    try:
        page_range_obj = PARAMTYPE_RANGE.convert(page_range_str, None, None)
    except click.BadParameter:
        # 如果解析失败，说明第一个参数是名称的一部分
        name_parts.insert(0, page_range_str)
        page_range_obj = None
    
    full_name = " ".join(name_parts)
    full_name = full_name if full_name != "" else None
    page_from = None
    page_to = None

    if isinstance(page_range_obj, tuple):
        page_from, page_to = page_range_obj
    elif isinstance(page_range_obj, int):
        page_from = page_range_obj
    
    return QuoteListCommandParams(page_from=page_from, page_to=page_to, name=full_name)