from ..imports import on_message, on_command
from ..interface.permission import permission_check, PMS


# info_quote
matcher_listener = on_message(
    priority=15, block=False, permission=permission_check(PMS.BE_COLLECTED)
)

_rank_cmds = ("语录rank", "语录排行", "quote_rank", "语录信息", "quote_info")
matcher_rank = on_command(
    _rank_cmds[0],
    aliases=set(_rank_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_setting_showing_cmds = ("语录设置", "语录设置信息", "quote_setting", "语录配置", "quote_config", "查看语录设置", "查看语录配置")
matcher_setting_showing = on_command(
    _setting_showing_cmds[0],
    aliases=set(_setting_showing_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.OTHERS)
)


# modify_quote
_update_quote_cmds = ("语录强制更新", "更新语录", "语录更新", "强制更新语录", "强制语录更新")
matcher_update_quote = on_command(
    _update_quote_cmds[0],
    aliases=set(_update_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_add_quote_cmds = ("加语录", "add_quote", "quote_add", "添加语录", "新增语录", "语录添加")
matcher_add_quote = on_command(
    _add_quote_cmds[0],
    aliases=set(_add_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.ADD_QUOTE)
)

_remove_quote_cmds = ("删语录", "remove_quote", "quote_remove", "删除语录", "语录删除")
matcher_remove_quote = on_command(
    _remove_quote_cmds[0],
    aliases=set(_remove_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.DELETE_QUOTE_GROUP)
)

_comment_quote_cmds = ("评语录", "quote_comment", "评论语录", "评价语录", "评")
matcher_comment_quote = on_command(
    _comment_quote_cmds[0],
    aliases=set(_comment_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.REVIEW_QUOTE)
)

_del_comment_cmds = ("删评论", "del_comment", "删除评论", "删除语录评论", "删除语录评价")
matcher_del_comment = on_command(
    _del_comment_cmds[0],
    aliases=set(_del_comment_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.DELETE_REVIEW_GROUP)
)


# old_quote
_old_quote_cmds = ("老语录", "lt语录", "lt_quote", "老语录", "oldquote", "旧语录", "LT语录")
matcher_old_quote = on_command(
    _old_quote_cmds[0],
    aliases=set(_old_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)


# read_quote
_random_quote_cmds = ("语录", "quote", "随机语录")
matcher_random_quote = on_command(
    _random_quote_cmds[0],
    aliases=set(_random_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_card_cmds = ("语录卡", "语录图", "quote_card", "语录card", "语录图片")
matcher_quote_card = on_command(
    _quote_card_cmds[0],
    aliases=set(_quote_card_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_list_cmds = ("语录列表", "语录list", "语录列表", "quote_list", "列语录")
matcher_quote_list = on_command(
    _quote_list_cmds[0],
    aliases=set(_quote_list_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_search_cmds = ("查语录", "quote_search", "语录搜索", "语录查找", "搜语录", "找语录")
matcher_quote_search = on_command(
    _quote_search_cmds[0],
    aliases=set(_quote_search_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)


# settings
_get_quote_setting_cmds = (
    "当前语录设置", "get_quote_setting", "get_quote_config", "查看语录设置", "查看语录配置", 
    "语录配置查看", "语录设置查看", "查看当前语录设置", "查看当前语录配置"
)
matcher_get_quote_setting = on_command(
    _get_quote_setting_cmds[0],
    aliases=set(_get_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.OTHERS)
)

_modify_quote_setting_cmds = (
    "修改语录设置", "修改语录配置", "设置语录设置", "设置语录配置", 
    "更改语录设置", "更改语录配置", "更新语录设置", "更新语录配置",
    "set_quote_setting", "set_quote_config"
)
matcher_modify_quote_setting = on_command(
    _modify_quote_setting_cmds[0],
    aliases=set(_modify_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.OTHERS)
)

_reset_quote_setting_cmds = (
    "重置语录设置", "重置语录配置", "恢复语录设置", "恢复语录配置",
    "reset_quote_setting", "reset_quote_config"
)
matcher_reset_quote_setting = on_command(
    _reset_quote_setting_cmds[0],
    aliases=set(_reset_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.OTHERS)
)
