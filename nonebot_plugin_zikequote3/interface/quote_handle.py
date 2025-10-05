from ..imports import *
from .quote_type import QuoteManager, QuoteInfoV2, QuoteV2Comment, ID_AI
from ..utils.formating import generate_color_palette

def get_quote_file(group_id: int) -> str:
    """根据群组 ID 获取语录文件名"""
    return f"{group_id}.json"

def add_quote(group_id: int, quote: QuoteInfoV2):
    """
    添加语录到指定群组的语录文件中
    """
    quote_manager = QuoteManager(get_quote_file(group_id))
    with quote_manager:
        quote_manager.add_quote(quote)

def add_comment(group_id: int, quote_id: int, comment: QuoteV2Comment) -> bool:
    """
    添加评论到指定语录
    """
    quote_manager = QuoteManager(get_quote_file(group_id))
    with quote_manager:
        success = quote_manager.add_comment(quote_id, comment)
    return success

def remove_quote(group_id: int, quote_id: int) -> bool:
    """
    删除指定群组的语录
    """
    success = False
    quote_manager = QuoteManager(get_quote_file(group_id))
    with quote_manager:
        quotes = quote_manager.get_quotes()
        for quote in quotes:
            if quote["quote_id"] == quote_id:
                quotes.remove(quote)
                success = True
                break
        quote_manager.set_quotes(quotes)
    return success

def calculate_weight(quotes: List[QuoteInfoV2], filter: Callable[[QuoteInfoV2], bool] = lambda quote: True) -> Dict[int, float]:
    """
    计算语录的选取权重

    `return`: {quote_id: weight}
    """
    if not quotes:
        return {}
    
    filtered_quotes = [quote for quote in quotes if filter(quote)]
    if not filtered_quotes:
        return {}
    
    # 按照概率选择语录，出现次数越多的语录，概率越低，概率反比于出现次数
    # 通过幂变换平滑 / 增加权重差异
    # 同时出现次数要减去最低出现次数以防止最后 weight 趋于平均

    weights = {}
    min_show_time = abs(min(quote.show_time for quote in filtered_quotes))
    for quote in filtered_quotes:
        weights[quote.quote_id] = (1 / (quote.show_time - min_show_time + 1)) ** cfg.weight_p_transform
    
    total_weight = sum(weights.values())
    for id, weight in weights.items():
        weights[id] = weight / total_weight

    return weights

def get_typed_quote_list(group_id: int, filter: Callable[[QuoteInfoV2], bool] = lambda quote: True) -> List[QuoteInfoV2]:
    """
    获取语录列表 (typed)
    """
    quote_manager = QuoteManager(get_quote_file(group_id))
    quote_manager.load_from_file()
    quotes = quote_manager.get_typed_quotes()
    return [quote for quote in quotes if filter(quote)]

def get_random_quote(
        group_id: int,
        filter: Callable[[QuoteInfoV2], bool] = lambda quote: True,
        list_num: Optional[int] = None,
        update_showtime: bool = True,
    ) -> Optional[Union[QuoteInfoV2, List[QuoteInfoV2]]]:
    """
    随机获取语录

    `group_id`: 群组 ID
    `filter`: 过滤函数，返回 True 的语录会被选中
    `list_num`: 随机获取的语录数量，默认 None 表示选取一条并返回单独的语录对象，否则返回列表
    `update_showtime`: 是否更新语录展示次数，默认 True
    """
    quotes = get_typed_quote_list(group_id, filter)
    if not quotes:
        return None
    
    weights = calculate_weight(quotes)
    if not weights:
        return None
    
    if list_num is not None and list_num > len(quotes):
        list_num = len(quotes)

    if list_num is not None and list_num < 1:
        return None
    
    # 选择随机语录
    if list_num is None:
        result = random.choices(quotes, weights=list(weights.values()), k=1)[0]
    else:
        result = random.choices(quotes, weights=list(weights.values()), k=list_num)

    # 更新语录展示次数
    if update_showtime:
        qm = QuoteManager(get_quote_file(group_id))
        with qm:
            if isinstance(result, QuoteInfoV2):
                qm.update_show_time(result.quote_id)
            else:
                for quote in result: qm.update_show_time(quote.quote_id)

    return result
