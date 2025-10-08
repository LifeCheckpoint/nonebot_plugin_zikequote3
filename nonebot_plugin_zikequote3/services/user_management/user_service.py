from ...imports import *


def s_user_exists(qq_id: str) -> bool:
    """
    检查用户是否存在
    """
    with exception_report("检查用户存在性"):
        return db.dao.get_user_dao().user_exists(qq_id)


def s_search_users_by_name(name: str, group_id: Optional[str], exact: bool = True) -> List[str]:
    """
    通用搜索用户

    搜索优先级：正在使用群名片 > 正在使用昵称 > 曾用名片 > 曾用昵称

    Returns:
        results (List[str]): 可能的用户 QQ 号列表。请注意，结果列表一定是同一个优先级内的，不会出现跨优先级的用户搜索
    """
    if group_id is not None:
        results = s_search_users_by_current_card(name, group_id, exact)
        if results:
            return results
    
    results = s_search_users_by_current_name(name, exact)
    if results:
        return results
    
    if group_id is not None:
        results = s_search_users_by_past_card(name, group_id, exact)
        if results:
            return results
        
    results = s_search_users_by_past_name(name, exact)
    return results


def s_search_users_by_current_card(name: str, group_id: str, exact: bool = False) -> List[str]:
    """
    通过正在使用的群名片搜索用户

    Args:
        name (str): 群名片
        group_id (str): 群号
        exact (bool): 是否进行精确搜索

    Returns:
        results (List[str]): 可能的用户 QQ 号列表
    """
    with exception_report("搜索用户群名片"):
        users = db.dao.get_group_nickname_dao().search_users_by_nickname_in_group(
            name=name if exact else f"%{name}%",
            group_id=group_id,
        )
        return [str(u.qq_id) for u in users if u.current_using]
    
    return []


def s_search_users_by_current_name(name: str, exact: bool = False) -> List[str]:
    """
    通过正在使用的昵称搜索用户

    Args:
        name (str): 昵称
        exact (bool): 是否进行精确搜索

    Returns:
        results (List[str]): 可能的用户 QQ 号列表
    """
    with exception_report("搜索用户昵称"):
        users = db.dao.get_user_nickname_dao().search_user_by_nickname(
            name=name if exact else f"%{name}%"
        )
        return [str(u.qq_id) for u in users if u.current_using]
    
    return []


def s_search_users_by_past_card(name: str, group_id: str, exact: bool = False) -> List[str]:
    """
    通过曾用群名片搜索用户

    Args:
        name (str): 群名片
        group_id (str): 群号
        exact (bool): 是否进行精确搜索

    Returns:
        results (List[str]): 可能的用户 QQ 号列表
    """
    with exception_report("搜索用户群名片"):
        users = db.dao.get_group_nickname_dao().search_users_by_nickname_in_group(
            name=name if exact else f"%{name}%",
            group_id=group_id,
        )
        return [str(u.qq_id) for u in users if not u.current_using]
    
    return []


def s_search_users_by_past_name(name: str, exact: bool = False) -> List[str]:
    """
    通过曾用昵称搜索用户

    Args:
        name (str): 昵称
        exact (bool): 是否进行精确搜索

    Returns:
        results (List[str]): 可能的用户 QQ 号列表
    """
    with exception_report("搜索用户昵称"):
        users = db.dao.get_user_nickname_dao().search_user_by_nickname(
            name=name if exact else f"%{name}%"
        )
        return [str(u.qq_id) for u in users if not u.current_using]
    
    return []


def s_get_user_current_group_card(qq_id: str, group_id: str) -> Optional[str]:
    """
    获取用户当前在某个群的群名片

    Args:
        qq_id (str): 用户 QQ 号
        group_id (str): 群号

    Returns:
        card (Optional[str]): 群名片，若无则返回 None
    """
    with exception_report("获取用户群名片"):
        card = db.dao.get_group_nickname_dao().get_current_group_nickname(qq_id, group_id)
        return card


def s_get_user_current_nickname(qq_id: str) -> Optional[str]:
    """
    获取用户当前昵称

    Args:
        qq_id (str): 用户 QQ 号

    Returns:
        nickname (Optional[str]): 昵称，若无则返回 None
    """
    with exception_report("获取用户昵称"):
        nickname = db.dao.get_user_nickname_dao().get_current_nickname(qq_id)
        return nickname.name if nickname else None


def s_get_user_current_display_name(qq_id: str, group_id: Optional[str]) -> str:
    """
    获取用户当前显示名称

    优先级：群名片 > 昵称 > QQ 号

    Args:
        qq_id (str): 用户 QQ 号
        group_id (Optional[str]): 群号，若无则传入 None

    Returns:
        display_name (str): 显示名称
    """
    card = None
    if group_id is not None:
        card = s_get_user_current_group_card(qq_id, group_id)
    
    if card:
        return card
    
    nickname = s_get_user_current_nickname(qq_id)
    if nickname:
        return nickname
    
    return qq_id