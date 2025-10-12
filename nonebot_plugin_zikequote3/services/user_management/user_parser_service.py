from ...imports import *


def s_at_one_user(event: GroupME) -> str | None:
    """
    解析消息中的 @ 用户，返回第一个 @ 用户的 QQ 号

    注意不会对 QQ 号是否有效进行验证

    Args:
        event (GroupME): 事件对象
    """
    at_segs: List[MsgSeg] = event.get_message()["at"]
    at_one: str | int | None = at_segs[0].data.get("qq") if at_segs else None

    if at_one == "all":
        return None

    return str(at_one) if at_one else None


# HACK: 较难维护，考虑重构
def s_parse_at_and_str_user(
    key: str, event: Optional[GroupME], group_id: str | None = None,
    exact: bool = True, empty_parse_to_self: bool = True, multiple_at: bool = False, parse_at_all: bool = False
) -> List[str]:
    """
    解析消息中的 @ 或昵称所代表的 QQ，返回一个字符串列表表示 QQ 号

    注意不会对 QQ 号是否有效进行验证，优先解析 @ 段

    解析逻辑：

    1. 提供了事件对象且消息中存在 @ 段
        1.1 multiple_at 为 False，则返回第一个 @ 用户的 QQ 号
        1.2 multiple_at 为 True，则返回所有 @ 用户的 QQ 号
    2. 未提供事件对象或消息中不存在 @ 段
        2.1 key 为空且 empty_parse_to_self 为 True，返回调用者的 QQ 号（如果提供了事件对象）
        2.2 key 为空且 empty_parse_to_self 为 False，返回空列表
        2.3 key 为纯数字字符串，返回该数字字符串作为 QQ 号
        2.4 key 为非纯数字字符串，尝试将其作为昵称进行搜索
            2.4.1 exact 为 True，则进行精确匹配
            2.4.2 exact 为 False，则进行模糊匹配
            2.4.3 group_id 未提供且未提供事件对象，则无法进行搜索，返回空列表
    3. key 为 "@所有人" 且 parse_at_all 为 True，则返回 ["all"]
    4. key 为 "@所有人" 且 parse_at_all 为 False，则返回空列表
    5. 其他情况，返回空列表

    Args:
        arg_msg (Message): 参数消息对象
        event (GroupME): 事件对象
        group_id (str | None): 群组 ID
        exact (bool): 是否进行精确匹配，默认为 True
        empty_parse_to_self (bool): 当参数为空时，是否返回调用者的 QQ 号，默认为 True
        multiple_at (bool): 是否允许返回多个 @ 用户，默认为 False
        parse_at_all (bool): 是否将 @所有人 解析为 "all"，默认为 False
    """
    from .user_service import s_search_users_by_name

    key = key.strip()

    # 如果提供了事件，默认无需再使用 group_id 参数
    group_id = str(event.group_id) if event is not None else group_id

    # 解析 @ 段，如果不提供事件则认为没有 @ 段
    if event is not None:
        at_segs: List[MsgSeg] = event.get_message()["at"]
        at_one: str | int | None = at_segs[0].data.get("qq") if at_segs else None
    else:
        at_one = None

    if at_one == "all":
        return ["all"] if parse_at_all else []

    # 非@用户，解析参数
    if not at_one:
        if key == "" and empty_parse_to_self:
            # 空参数且提供了事件，返回调用者
            return [str(event.user_id)] if event else []
        elif key == "" and not empty_parse_to_self:
            # 空参数且不返回调用者
            return []
        elif key.isnumeric():
            # 输入 QQ 号
            return [key]
        else:
            # 输入昵称，尝试搜索
            return s_search_users_by_name(key, str(group_id), exact=exact)
        
    else:
        # @用户

        if not multiple_at:
            return [str(at_one)]
        else:
            return [
                str(seg.data.get("qq"))
                for seg in at_segs
                if seg.data.get("qq") and str(seg.data.get("qq")) != "all"
            ]