import math
from ....database.models.quotes import Quote
from ....imports import *
from ...algorithm_management.showcase_algo_parse_service import (
    AlgoInverseFrequencyWeight as IFW,
    AlgoLogInverseFrequencyWeight as LogIFW,
)

def s_ifw(quotes: List[Quote], params: IFW) -> Dict[str, float]:
    """
    逆频率加权算法，通过较强的惩罚频率抑制马太效应，从而实现近乎均衡的随机选择

    其计算方式为：
    1. 计算每个语录的初始权重：`w_i0 = (1 / (c_i - min_j(c_j) + a))^λ`
    2. 归一化权重：`w_i = w_i0 / sum_j(w_j0)`

    可以证明最终收敛到均匀分布，且方差降低速率为 O(1/n)

    Args:
        quotes (List[Quote]): 语录列表
        params (AlgoInverseFrequencyWeight): 算法参数
    
    ## 算法参数
    - `lambda_`: 正则化幂变换系数，越大则越均匀
    - `a_`: 冷启动平滑稀疏，越大则启动时方差越大

    Returns:
        results (Dict[str, float]): {quote_id: weight}
    """
    quote_key_totalshow: Callable[[Quote], int] = lambda q: q.total_show_time
    min_c_j = min(*quotes, key=quote_key_totalshow).total_show_time
    wi0 = {
        q.quote_id: (1 / (q.total_show_time - min_c_j + params.a_)) ** params.lambda_
        for q in quotes
    }
    wi = {id: weight / sum(wi0.values()) for id, weight in wi0.items()}

    return wi

def s_logifw(quotes: List[Quote], params: LogIFW) -> Dict[str, float]:
    """
    对数逆频率加权算法，通过对数平滑减缓频率惩罚，从而实现相比 IFW 方差更大的随机选择

    其计算方式为：
    1. 计算每个语录的初始权重：`w_i0 = (1 / (log(c_i - min_j(c_j) + log_a) + a))^λ`
    2. 归一化权重：`w_i = w_i0 / sum_j(w_j0)`

    Args:
        quotes (List[Quote]): 语录列表
        params (AlgoLogInverseFrequencyWeight): 算法参数
    
    ## 算法参数
    - `lambda_`: 正则化幂变换系数，越大则越均匀
    - `log_a_`: 对数平滑稀疏，越大则整体拉回力度小，方差大
    - `a_`: 冷启动平滑稀疏，越大则启动时方差越大

    Returns:
        results (Dict[str, float]): {quote_id: weight}
    """
    quote_key_totalshow: Callable[[Quote], int] = lambda q: q.total_show_time
    min_c_j = min(*quotes, key=quote_key_totalshow).total_show_time
    wi0 = {
        q.quote_id: (1 / (math.log(q.total_show_time - min_c_j + params.log_a_) + params.a_)) ** params.lambda_
        for q in quotes
    }
    wi = {id: weight / sum(wi0.values()) for id, weight in wi0.items()}

    return wi