from ..imports import on_message, on_command
from ..interface.permission import permission_check, PMS


# region 自动收集事件

matcher_listener = on_message(
    priority=15, block=False, permission=permission_check(PMS.BE_COLLECTED)
)

# endregion

# region 语录统计命令
# stastics_cmds

_rank_cmds = ("语录rank", "语录排行", "quote_rank", "语录信息", "quote_info")
matcher_rank = on_command(
    _rank_cmds[0],
    aliases=set(_rank_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_list_cmds = ("语录列表", "语录list", "语录列表", "quote_list", "列语录")
matcher_quote_list = on_command(
    _quote_list_cmds[0],
    aliases=set(_quote_list_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

# endregion

# region 语录修改命令
# modify_cmd

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

# endregion

# region 语录读取命令
# read_cmds

_random_quote_cmds = ("语录", "quote", "随机语录", "来句语录")
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

_quote_search_cmds = (
    "查语录", "查询语录", "quote_search", "语录搜索",
    "语录查找", "搜语录", "找语录", "搜语录", "找语录", "搜索语录", "查找语录",
    "寻找语录", "检索语录"
)
matcher_quote_search = on_command(
    _quote_search_cmds[0],
    aliases=set(_quote_search_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_image_fetching_cmds = (
    "语录原图", "语录图片", "quote_image", "quote_img",
    "语录img", "语录图像", "获取语录图片", "获取语录原图", "获取语录img",
    "获取语录图像", "get_quote_image", "get_quote_img"
)
matcher_quote_image_fetching = on_command(
    _quote_image_fetching_cmds[0],
    aliases=set(_quote_image_fetching_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

# endregion

# region 普通 op 命令
# common_op_cmds

_update_quote_cmds = ("语录强制更新", "更新语录", "语录更新", "强制更新语录", "强制语录更新")
matcher_update_quote = on_command(
    _update_quote_cmds[0],
    aliases=set(_update_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

# endregion

# region 插件配置命令
# settings_cmds
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

_batch_modify_quote_setting_cmds = (
    "批量修改语录设置", "批量修改语录配置", "批量设置语录设置", "批量设置语录配置", 
    "批量更改语录设置", "批量更改语录配置", "批量更新语录设置", "批量更新语录配置",
    "batch_set_quote_setting", "batch_set_quote_config"
)
matcher_batch_modify_quote_setting = on_command(
    _batch_modify_quote_setting_cmds[0],
    aliases=set(_batch_modify_quote_setting_cmds[1:]),
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

_reload_quote_setting_cmds = (
    "重载语录设置", "重载语录配置", "重新加载语录设置", "重新加载语录配置",
    "刷新语录设置", "刷新语录配置", "reload_quote_setting", "reload_quote_config"
)
matcher_reload_quote_setting = on_command(
    _reload_quote_setting_cmds[0],
    aliases=set(_reload_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.OTHERS)
)

# endregion
