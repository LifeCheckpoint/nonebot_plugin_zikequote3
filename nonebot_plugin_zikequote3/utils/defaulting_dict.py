from typing import TypeVar, Generic, Dict

T = TypeVar('T')
U = TypeVar('U')

class DefaultingDict(dict, Generic[T, U]):
    """
    默认值字典类，当访问一个不存在的键时，返回一个预设的默认值
    """
    def __init__(self, default_value: U, dictionary: Dict[T, U]):
        self.default_value = default_value
        super().__init__(dictionary)
    
    def __getitem__(self, key: T) -> U:
        """
        尝试获取键值，如果失败（引发KeyError），则返回默认值。
        """
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.default_value