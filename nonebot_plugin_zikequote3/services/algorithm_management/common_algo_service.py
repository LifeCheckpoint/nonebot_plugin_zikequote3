from ...imports import *
from typing import TypeVar, Iterable, Hashable

T = TypeVar('T')

def s_deduplicate_by_field_last(items: Iterable[T], key_func: Callable[[T], Any]) -> List[T]:
    """
    根据指定字段去重，保留最后一个出现的元素。
    """
    deduped_dict = {}
    for item in items:
        deduped_dict[key_func(item)] = item
    return list(deduped_dict.values())


def s_intersection_by_field(list1: Iterable[T], list2: Iterable[T], key_func: Callable[[T], Any]) -> List[T]:
    """
    根据指定字段取交集，返回在两个列表中都存在的元素。
    """
    keys_set = {key_func(item) for item in list2}
    return [item for item in list1 if key_func(item) in keys_set]


def s_union_by_field(list1: Iterable[T], list2: Iterable[T], key_func: Callable[[T], Hashable]) -> List[T]:
    """
    根据指定字段取并集，返回并集元素，仅保留第一个出现的元素。
    """
    union_dict = {}
    for item in list1:
        union_dict[key_func(item)] = item
    for item in list2:
        if key_func(item) not in union_dict:
            union_dict[key_func(item)] = item
    return list(union_dict.values())
