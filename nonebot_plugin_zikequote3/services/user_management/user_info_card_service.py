from ...imports import *

async def s_get_user_info_html(group_id: str, qq_id: str) -> str:
    """
    获取用户信息卡片 HTML
    """
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...services.user_management.avatar_service import s_get_user_avatar
    from ...templates.schema.user_info import render_user_info
    from ...utils.base64_encoder import to_data_uri

    async with service_exception_a("获取用户信息"):
        exists = db.dao.get_user_dao().user_exists(qq_id)
        if not exists:
            raise ValueError(f"用户 {qq_id} 不存在")
        
        # 获取当前显示名称（优先群名片）
        current_display_name = s_get_user_current_display_name(qq_id, group_id)
        
        # 获取当前昵称（非群名片）
        current_nick_obj = db.dao.get_user_nickname_dao().get_current_nickname(qq_id)
        current_nick = current_nick_obj.name if current_nick_obj else current_display_name

        # 获取当前群名片
        current_card = db.dao.get_group_nickname_dao().get_current_group_nickname(qq_id, group_id)

        # 获取头像
        usr = db.dao.get_user_dao().get_user_by_qq_id(qq_id)
        avatar_bytes = usr.avatar if usr else None
        if not avatar_bytes:
            avatar_bytes = await s_get_user_avatar(qq_id)
            if avatar_bytes:
                db.dao.get_user_dao().update_user(qq_id, avatar_bytes)
        avatar_bs64 = to_data_uri(avatar_bytes) if avatar_bytes else ""

    async with service_exception_a("获取用户统计数据"):
        # 获取语录数
        quote_count = db.dao.get_quote_dao().count_quotes_by_group_and_author(group_id, qq_id)
        
        # 计算排名
        # 获取群内所有成员
        authors = db.dao.get_group_member_dao().get_members_by_group(group_id)
        ranking_list = []
        for author in authors:
            count = db.dao.get_quote_dao().count_quotes_by_group_and_author(group_id, author.qq_id)
            if count > 0:
                ranking_list.append((author.qq_id, count))
        
        # 排序
        ranking_list.sort(key=lambda x: x[1], reverse=True)
        
        # 查找排名
        ranking_value = None
        for idx, (uid, count) in enumerate(ranking_list):
            if uid == qq_id:
                ranking_value = idx + 1
                break

    async with service_exception_a("获取用户历史记录"):
        # 获取曾用昵称
        history_nicks_objs = db.dao.get_user_nickname_dao().get_all_nicknames(qq_id)
        history_nicks = [n.name for n in history_nicks_objs]
        
        # 获取曾用群名片
        history_group_cards_objs = db.dao.get_group_nickname_dao().get_all_group_nicknames(qq_id, group_id)
        history_group_cards = [n.name for n in history_group_cards_objs]

    async with service_exception_a("生成用户信息卡片 HTML"):
        return render_user_info(
            ranking_value=ranking_value,
            quote_count=quote_count,
            qq_id=qq_id,
            primary_nick=current_nick,
            primary_group_card=current_card,
            avatar=avatar_bs64,
            history_nicks=history_nicks,
            history_group_cards=history_group_cards,
        )
