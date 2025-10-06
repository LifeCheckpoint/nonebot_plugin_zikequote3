from ..imports import on_message, on_command
from ..services.permission_management.permission_service import permission_check, PMS


# region 自动收集事件
# auto_collect_cmds

matcher_collecting_listener = on_message(
    priority=15, block=False, permission=permission_check(PMS.BE_COLLECTED)
)

# endregion

# region 语录统计命令
# quote_stastics_cmds

_rank_cmds = (
    "语录rank", "语录ranking", "语录排行", "语录排行榜",
    "语录统计", "语录统计信息", "语录群排行", "排行语录",
    "统计语录",
)
matcher_rank = on_command(
    _rank_cmds[0],
    aliases=set(_rank_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_list_cmds = (
    "语录列表", "语录list", "语录列表", "列语录",
    "个人语录", "个人语录列表", "语录个人列表",
)
matcher_quote_list = on_command(
    _quote_list_cmds[0],
    aliases=set(_quote_list_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

# endregion

# region 语录修改命令
# quote_modify_cmds

_add_quote_cmds = ("加语录", "添加语录", "新增语录", "语录添加")
matcher_add_quote = on_command(
    _add_quote_cmds[0],
    aliases=set(_add_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.ADD_QUOTE)
)

_add_quote_image_cmds = (
    "加语录图", "加语录图片", "加语录图像", "语录加图", "语录加图片", "语录加图像",
    "添加语录图", "添加语录图片", "添加语录图像", "语录添加图", "语录添加图片", "语录添加图像",
    "新增语录图", "新增语录图片", "新增语录图像", "语录新增图", "语录新增图片", "语录新增图像",
    "附加语录图", "附加语录图片", "附加语录图像", "语录附加图", "语录附加图片", "语录附加图像",
    # 搁这儿排列组合呢
)
matcher_add_quote_image = on_command(
    _add_quote_image_cmds[0],
    aliases=set(_add_quote_image_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.ADD_QUOTE)
)

_remove_quote_cmds = ("删语录", "删除语录", "语录删除")
matcher_remove_quote = on_command(
    _remove_quote_cmds[0],
    aliases=set(_remove_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.DELETE_QUOTE_GROUP)
)

_remove_quote_image_cmds = (
    "删语录图", "删语录图片", "删语录图像", "语录删图", "语录删图片", "语录删图像",
    "删除语录图", "删除语录图片", "删除语录图像", "语录删除图", "语录删除图片", "语录删除图像",
    "移除语录图", "移除语录图片", "移除语录图像", "语录移除图", "语录移除图片", "语录移除图像",
)
matcher_remove_quote_image = on_command(
    _remove_quote_image_cmds[0],
    aliases=set(_remove_quote_image_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.DELETE_QUOTE_GROUP)
)

_comment_quote_cmds = ("评语录", "评论语录", "评价语录", "评")
matcher_comment_quote = on_command(
    _comment_quote_cmds[0],
    aliases=set(_comment_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.REVIEW_QUOTE)
)

_del_comment_cmds = ("删评论", "删除评论", "删除语录评论", "删除语录评价", "删语评")
matcher_del_comment = on_command(
    _del_comment_cmds[0],
    aliases=set(_del_comment_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.DELETE_REVIEW_GROUP)
)

# endregion

# region 语录读取命令
# quote_read_cmds

_random_quote_cmds = (
    "语录", "quote", "随机语录", "随机quote",
    "名人名言", "群友名言", "群友语录", "神人语录",
    "随机神人语录"
)
matcher_random_quote = on_command(
    _random_quote_cmds[0],
    aliases=set(_random_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_card_cmds = ("语录卡", "语录卡片", "语录card")
matcher_quote_card = on_command(
    _quote_card_cmds[0],
    aliases=set(_quote_card_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_search_cmds = (
    "查语录", "查询语录", "语录搜索", "语录查找",
    "搜语录", "找语录", "搜语录", "找语录", 
    "搜索语录", "查找语录", "寻找语录", "检索语录"
)
matcher_quote_search = on_command(
    _quote_search_cmds[0],
    aliases=set(_quote_search_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

_quote_image_fetching_cmds = (
    "语录查图", "语录取图", "查语录图", "取语录图",
    "语录查图片", "语录取图片", "查语录图片", "取语录图片",
    "语录原图", "语录图片", "语录img", "语录图像",
    "获取语录图片", "获取语录原图", "获取语录img", "获取语录图像",
)
matcher_quote_image_fetching = on_command(
    _quote_image_fetching_cmds[0],
    aliases=set(_quote_image_fetching_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.GET_QUOTE)
)

# endregion

# region 普通 op 命令
# common_op_cmds

_update_quote_cmds = (
    "语录强制更新", "更新语录", "语录更新", "强制更新语录",
    "强制语录更新", "刷新语录", "语录刷新", "强制刷新语录",
    "强制语录刷新",
)
matcher_update_quote = on_command(
    _update_quote_cmds[0],
    aliases=set(_update_quote_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.COMMON_OPERATIONS)
)

# endregion

# region 插件配置命令
# settings_cmds

_get_quote_setting_cmds = (
    "当前语录设置", "查看语录设置", "查看语录配置", 
    "语录配置查看", "语录设置查看", "查看当前语录设置", "查看当前语录配置"
)
matcher_get_quote_setting = on_command(
    _get_quote_setting_cmds[0],
    aliases=set(_get_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.MODIFY_SETTINGS)
)

_modify_quote_setting_cmds = (
    "修改语录设置", "修改语录配置", "设置语录设置", "设置语录配置", 
    "更改语录设置", "更改语录配置", "更新语录设置", "更新语录配置",
    "set_quote_setting", "set_quote_config"
)
matcher_modify_quote_setting = on_command(
    _modify_quote_setting_cmds[0],
    aliases=set(_modify_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.MODIFY_SETTINGS)
)

_batch_modify_quote_setting_cmds = (
    "批量修改语录设置", "批量修改语录配置", "批量设置语录设置", "批量设置语录配置", 
    "批量更改语录设置", "批量更改语录配置", "批量更新语录设置", "批量更新语录配置",
    "batch_set_quote_setting", "batch_set_quote_config"
)
matcher_batch_modify_quote_setting = on_command(
    _batch_modify_quote_setting_cmds[0],
    aliases=set(_batch_modify_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.MODIFY_SETTINGS)
)

_reset_quote_setting_cmds = (
    "重置语录设置", "重置语录配置", "恢复语录设置", "恢复语录配置",
    "reset_quote_setting", "reset_quote_config"
)
matcher_reset_quote_setting = on_command(
    _reset_quote_setting_cmds[0],
    aliases=set(_reset_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.MODIFY_SETTINGS)
)

_reload_quote_setting_cmds = (
    "重载语录设置", "重载语录配置", "重新加载语录设置", "重新加载语录配置",
    "刷新语录设置", "刷新语录配置", "reload_quote_setting", "reload_quote_config"
)
matcher_reload_quote_setting = on_command(
    _reload_quote_setting_cmds[0],
    aliases=set(_reload_quote_setting_cmds[1:]),
    priority=10, block=True, permission=permission_check(PMS.MODIFY_SETTINGS)
)

# endregion
