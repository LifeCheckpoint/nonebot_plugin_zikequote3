from typing import List
from ...database.models.quotes import Quote, QuoteCreate
from ...imports import db, logger

async def s_migrate_quotes(
    final_quotes: List[Quote],
    source_group: str,
    target_group: str,
    overwrite: bool,
    keep_source: bool
) -> bool:
    """
    执行语录迁移
    
    Args:
        final_quotes: 处理后的最终语录列表
        source_group: 源群号
        target_group: 目标群号
        overwrite: 是否覆写
        keep_source: 是否保留源群语录
    """
    quote_dao = db.dao.get_quote_dao()
    
    # 如果是覆写模式，先清空目标群语录
    if overwrite:
        logger.info(f"迁移模式为覆写，正在清空目标群 {target_group} 的语录...")
        quote_dao.delete_quotes_by_group(target_group)
        
    # 批量写入新的语录
    # 将 Quote 对象转换为 QuoteCreate 对象
    quotes_to_create = []
    
    if not overwrite:
        # 如果不是覆写模式，我们也需要先清空目标群，因为我们要写入的是合并后的完整集合
        logger.info(f"为了应用合并与去重，正在清空目标群 {target_group} 的旧语录...")
        quote_dao.delete_quotes_by_group(target_group)

    quotes_to_create = []
    for q in final_quotes:
        quotes_to_create.append(QuoteCreate(
            quote_id=q.quote_id,
            author_id=q.author_id,
            group_id=target_group, # 归属为目标群
            content=q.content,
            image_content_uuid=q.image_content_uuid,
            total_show_time=q.total_show_time
        ))
        
    # 如果不保留源群，清空源群语录 (Move模式)
    # 必须在写入前清空，以释放 ID，避免主键冲突
    if not keep_source:
        logger.info(f"正在清空源群 {source_group} 的语录 (Move模式)...")
        quote_dao.delete_quotes_by_group(source_group)

    if quotes_to_create:
        logger.info(f"正在向目标群 {target_group} 写入 {len(quotes_to_create)} 条语录...")
        quote_dao.batch_create_quotes(quotes_to_create)
        
    return True
