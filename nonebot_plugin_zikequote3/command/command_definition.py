from ..imports import on_message, on_command, on_alconna, perm_nodes, default_cfg
from arclet.alconna import Alconna, Arg, AllParam
from nonebot_plugin_alconna.uniseg.segment import At
from nepattern import BasePattern


# region 自动收集事件

matcher_collecting_listener = on_message(
    priority=15, block=False
)
perm_nodes.n_becollected_llm.patch_matcher(matcher_collecting_listener)


# endregion

# region 语录统计命令

cmdname_get_ranking = (
    "语录rank", "语录ranking", "语录排行", "语录排行榜",
    "语录统计", "语录统计信息", "语录群排行", "排行语录",
    "统计语录",
)
matcher_get_ranking = on_command(
    cmdname_get_ranking[0],
    aliases=set(cmdname_get_ranking[1:]),
    priority=10, block=True
)
perm_nodes.n_ranking.patch_matcher(matcher_get_ranking)


cmdname_get_quote_list = (
    "语录列表", "语录list", "语录列表", "列语录",
    "个人语录", "个人语录列表", "语录个人列表",
)
alc_get_quote_list = Alconna(
    cmdname_get_quote_list[0],
    cmdname_get_quote_list[1:],
    Arg("range?", "re:\\d{1,4}(?:-\\d+)?", None),
    Arg("at_user?", At, None),
    Arg("qq?", "re:\\d{5,}", None),
    Arg("nickname?", AllParam(str), ""),
)
matcher_get_quote_list = on_alconna(
    alc_get_quote_list,
    use_cmd_start=True, priority=10, block=True, skip_for_unmatch=False,
)
perm_nodes.n_listing.patch_matcher(matcher_get_quote_list)


# endregion

# region 语录修改命令

cmdname_add_quote = ("加语录", "添加语录", "新增语录", "语录添加")
matcher_add_quote = on_command(
    cmdname_add_quote[0],
    aliases=set(cmdname_add_quote[1:]),
    priority=10, block=True
)
perm_nodes.n_quote_add.patch_matcher(matcher_add_quote)


cmdname_add_quote_image = (
    "加语录图", "加语录图片", "加语录图像", "语录加图", "语录加图片", "语录加图像",
    "添加语录图", "添加语录图片", "添加语录图像", "语录添加图", "语录添加图片", "语录添加图像",
    "新增语录图", "新增语录图片", "新增语录图像", "语录新增图", "语录新增图片", "语录新增图像",
    "附加语录图", "附加语录图片", "附加语录图像", "语录附加图", "语录附加图片", "语录附加图像",
    # 搁这儿排列组合呢
)
matcher_add_quote_image = on_command(
    cmdname_add_quote_image[0],
    aliases=set(cmdname_add_quote_image[1:]),
    priority=10, block=True
)
perm_nodes.n_quote_attachimage.patch_matcher(matcher_add_quote_image)


cmdname_remove_quote_image = ("删语录", "删除语录", "语录删除")
matcher_remove_quote = on_command(
    cmdname_remove_quote_image[0],
    aliases=set(cmdname_remove_quote_image[1:]),
    priority=10, block=True
)
perm_nodes.n_quote_delete.patch_matcher(matcher_remove_quote)


cmdname_remove_quote_image = (
    "删语录图", "删语录图片", "删语录图像", "语录删图", "语录删图片", "语录删图像",
    "删除语录图", "删除语录图片", "删除语录图像", "语录删除图", "语录删除图片", "语录删除图像",
    "移除语录图", "移除语录图片", "移除语录图像", "语录移除图", "语录移除图片", "语录移除图像",
)
matcher_remove_quote_image = on_command(
    cmdname_remove_quote_image[0],
    aliases=set(cmdname_remove_quote_image[1:]),
    priority=10, block=True
)
perm_nodes.n_quote_removeimage.patch_matcher(matcher_remove_quote_image)


cmdname_add_quote_comment = ("评语录", "评论语录", "评价语录", "评")
matcher_add_quote_comment = on_command(
    cmdname_add_quote_comment[0],
    aliases=set(cmdname_add_quote_comment[1:]),
    priority=10, block=True
)
perm_nodes.n_review_add.patch_matcher(matcher_add_quote_comment)

# 允许不使用前缀直接评论
matcher_add_quote_comment_no_prefix = None
if default_cfg.comment.enable_comment_without_prefix:
    matcher_add_quote_comment_no_prefix = on_message(
        priority=15, block=False
    )
    perm_nodes.n_review_add.patch_matcher(matcher_add_quote_comment_no_prefix)


cmdname_remove_quote_comment = ("删评论", "删除评论", "删除语录评论", "删除语录评价", "删语评")
matcher_remove_quote_comment = on_command(
    cmdname_remove_quote_comment[0],
    aliases=set(cmdname_remove_quote_comment[1:]),
    priority=10, block=True
)
perm_nodes.n_review_delete.patch_matcher(matcher_remove_quote_comment)


# endregion

# region 语录查询命令

cmdname_random_quote = (
    "语录", "quote", "随机语录", "随机quote",
    "名人名言", "群友名言", "群友语录", "神人语录",
    "随机神人语录"
)
matcher_random_quote = on_command(
    cmdname_random_quote[0],
    aliases=set(cmdname_random_quote[1:]),
    priority=11, block=True
)
perm_nodes.n_get_text.patch_matcher(matcher_random_quote)


cmdname_random_quote_card = ("语录卡", "语录卡片", "语录card")
matcher_random_quote_card = on_command(
    cmdname_random_quote_card[0],
    aliases=set(cmdname_random_quote_card[1:]),
    priority=10, block=True
)
perm_nodes.n_get_card.patch_matcher(matcher_random_quote_card)


cmdname_search_quote = (
    "查语录", "查询语录", "语录搜索", "语录查找",
    "搜语录", "找语录", "搜语录", "找语录", 
    "搜索语录", "查找语录", "寻找语录", "检索语录"
)
matcher_search_quote = on_command(
    cmdname_search_quote[0],
    aliases=set(cmdname_search_quote[1:]),
    priority=10, block=True
)
perm_nodes.n_search.patch_matcher(matcher_search_quote)


cmdname_random_quote_image = (
    "语录图", "语录查图", "语录取图", "查语录图", "取语录图",
    "语录查图片", "语录取图片", "查语录图片", "取语录图片",
    "语录原图", "语录图片", "语录img", "语录图像",
    "获取语录图片", "获取语录原图", "获取语录img", "获取语录图像",
)
matcher_random_quote_image = on_command(
    cmdname_random_quote_image[0],
    aliases=set(cmdname_random_quote_image[1:]),
    priority=10, block=True
)
perm_nodes.n_get_image.patch_matcher(matcher_random_quote_image)


# endregion

# region 普通操作命令

cmdname_update_quote_force = (
    "语录强制更新", "更新语录", "语录更新", "强制更新语录",
    "强制语录更新", "刷新语录", "语录刷新", "强制刷新语录",
    "强制语录刷新",
)
matcher_update_quote_force = on_command(
    cmdname_update_quote_force[0],
    aliases=set(cmdname_update_quote_force[1:]),
    priority=10, block=True
)
perm_nodes.n_forcerefresh.patch_matcher(matcher_update_quote_force)

# endregion

# region 插件配置命令

cmdname_get_current_config = (
    "当前语录设置", "查看语录设置", "查看语录配置", 
    "语录配置查看", "语录设置查看", "查看当前语录设置", "查看当前语录配置"
)
matcher_get_current_config = on_command(
    cmdname_get_current_config[0],
    aliases=set(cmdname_get_current_config[1:]),
    priority=10, block=True
)
perm_nodes.n_settings_get.patch_matcher(matcher_get_current_config)


cmdname_modify_config = (
    "修改语录设置", "修改语录配置", "设置语录设置", "设置语录配置", 
    "更改语录设置", "更改语录配置", "更新语录设置", "更新语录配置",
    "set_quote_setting", "set_quote_config"
)
matcher_modify_config = on_command(
    cmdname_modify_config[0],
    aliases=set(cmdname_modify_config[1:]),
    priority=10, block=True
)
perm_nodes.n_settings_modify_group.patch_matcher(matcher_modify_config)


cmdname_batch_modify_config = (
    "批量修改语录设置", "批量修改语录配置", "批量设置语录设置", "批量设置语录配置", 
    "批量更改语录设置", "批量更改语录配置", "批量更新语录设置", "批量更新语录配置",
)
matcher_batch_modify_config = on_command(
    cmdname_batch_modify_config[0],
    aliases=set(cmdname_batch_modify_config[1:]),
    priority=10, block=True
)
perm_nodes.n_settings_modify_global.patch_matcher(matcher_batch_modify_config)


cmdname_reset_config = (
    "重置语录设置", "重置语录配置", "恢复语录设置", "恢复语录配置",
)
matcher_reset_config = on_command(
    cmdname_reset_config[0],
    aliases=set(cmdname_reset_config[1:]),
    priority=10, block=True
)
perm_nodes.n_settings_reset_group.patch_matcher(matcher_reset_config)


cmdname_reload_config = (
    "重载语录设置", "重载语录配置", "重新加载语录设置", "重新加载语录配置",
    "刷新语录设置", "刷新语录配置",
)
matcher_reload_config = on_command(
    cmdname_reload_config[0],
    aliases=set(cmdname_reload_config[1:]),
    priority=10, block=True
)
perm_nodes.n_settings_modify.patch_matcher(matcher_reload_config)

# endregion

# region 其他命令

cmdname_get_privacy = (
    "语录隐私政策", "语录隐私", "语录政策", "语录隐私条款",
    "查看语录隐私政策", "查看语录隐私", "查看语录政策", "查看语录隐私条款",
    "语录隐私政策查看", "语录隐私查看", "语录政策查看", "语录隐私条款查看",
)
matcher_get_privacy = on_command(
    cmdname_get_privacy[0],
    aliases=set(cmdname_get_privacy[1:]),
    priority=10, block=True
)
perm_nodes.n_perm_s.patch_matcher(matcher_get_privacy)


cmdname_stop_using_zikequote3 = (
    "停用语录", "停用zikequote3", "停用Zikequote3", "停用ZikeQuote3",
    "停用语录功能",
)
matcher_stop_using_zikequote3 = on_command(
    cmdname_stop_using_zikequote3[0],
    aliases=set(cmdname_stop_using_zikequote3[1:]),
    priority=10, block=True
)
perm_nodes.n_perm_s.patch_matcher(matcher_stop_using_zikequote3)


# endregion