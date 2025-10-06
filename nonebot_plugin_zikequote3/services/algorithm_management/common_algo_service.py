from ...imports import *
from typing import TypeVar, Iterable

T = TypeVar('T')

def s_deduplicate_by_field_last(items: Iterable[T], key_func: Callable[[T], Any]) -> List[T]:
    deduped_dict = {}
    for item in items:
        deduped_dict[key_func(item)] = item
    return list(deduped_dict.values())
