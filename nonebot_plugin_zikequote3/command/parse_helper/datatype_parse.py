from typing import Optional, Tuple

def parse_page_range(s: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    解析 page_from, page_to
    """
    if s is None:
        return (None, None)
    
    s = s.strip()
    if not s:
        return (None, None)
    if "-" in s:
        parts = s.split("-", 1)
        try:
            page_from = int(parts[0])
        except ValueError:
            page_from = None
        try:
            page_to = int(parts[1])
        except ValueError:
            page_to = None
        return (page_from, page_to)
    else:
        try:
            val = int(s)
        except ValueError:
            return (None, None)
        return (val, None)