from ...imports import *


def s_parse_at_and_str_user(
    key: str, event: GroupME,
    exact: bool = True, multiple_at: bool = False, parse_at_all: bool = False
) -> List[str]:
    """
    解析消息中的 @ 或昵称所代表的 QQ，返回一个字符串列表表示 QQ 号

    注意不会对 QQ 号是否有效进行验证

    Args:
        arg_msg (Message): 参数消息对象
        event (GroupME): 事件对象
        exact (bool): 是否进行精确匹配，默认为 True
        multiple_at (bool): 是否允许返回多个 @ 用户，默认为 False
        parse_at_all (bool): 是否将 @所有人 解析为 "all"，默认为 False
    """
    from .user_service import s_search_users_by_name

    key = key.strip()
    at_segs: List[MsgSeg] = event.get_message()["at"]
    at_one: str | int | None = at_segs[0].data.get("qq") if at_segs else None

    if at_one == "all":
        return ["all"] if parse_at_all else []

    if not at_one:
        # 非@用户，解析参数

        if key == "" or key.isnumeric():
            # 输入 QQ 号或空
            return [str(event.user_id)] if key == "" else [key]
        else:
            # 输入昵称，尝试搜索
            return s_search_users_by_name(key, str(event.group_id), exact=exact)
        
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