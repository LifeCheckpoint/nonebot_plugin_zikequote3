from ...imports import *
from pydantic import BaseModel, Field

class PersonalInformation(BaseModel):
    """
    个人信息类型

    字段参考了 `cqhttp` 的老文档，不一定有效
    """
    group_id: int = Field(..., description="群号")
    user_id: int = Field(..., description="QQ 号")
    nickname: str = Field(..., description="昵称")
    card: str = Field(..., description="群名片")
    sex: Literal["male", "female", "unknown"] = Field("unknown", description="性别")
    age: Optional[int] = Field(None, description="年龄")
    area: Optional[str] = Field(None, description="地区")
    join_time: Optional[int] = Field(None, description="入群时间戳")
    last_sent_time: Optional[int] = Field(None, description="最后发言时间戳")
    level: Optional[str] = Field(None, description="成员等级")
    role: Literal["owner", "admin", "member"] = Field("member", description="成员角色")
    unfriendly: bool = Field(False, description="是否不良记录成员")
    title: Optional[str] = Field(None, description="专属头衔")
    title_expire_time: Optional[int] = Field(None, description="专属头衔过期时间戳")
    card_changeable: bool = Field(True, description="是否允许修改群名片")
    shut_up_timestamp: Optional[int] = Field(None, description="禁言到期时间戳")

async def s_update_personal_info_api(group_id: str, qq_id: str, bot: Bot):
    """
    通过接口 API 更新个人信息，带缓存机制
    """
    with exception_report(f"获取用户 {qq_id} 在群 {group_id} 的信息"):
        info = await bot.get_group_member_info(
            group_id=int(group_id),
            user_id=int(qq_id),
            no_cache=False
        )

        # 将 info 转换为 PersonalInformation
        pinfo = PersonalInformation(
            group_id=int(group_id),
            user_id=int(qq_id),
            nickname=info.get("nickname", ""),
            card=info.get("card", ""),
            sex=info.get("sex", "unknown"),
            age=info.get("age"),
            area=info.get("area"),
            join_time=info.get("join_time"),
            last_sent_time=info.get("last_sent_time"),
            level=info.get("level"),
            role=info.get("role", "member"),
            unfriendly=info.get("unfriendly", False),
            title=info.get("title"),
            title_expire_time=info.get("title_expire_time"),
            card_changeable=info.get("card_changeable", True),
            shut_up_timestamp=info.get("shut_up_timestamp"),
        )

    with exception_report(f"更新用户 {qq_id} 在群 {group_id} 的昵称 / 群名片缓存"):
        current_nickname = db.dao.get_user_nickname_dao().get_current_nickname(qq_id)
        current_card = db.dao.get_group_nickname_dao().get_current_group_nickname(qq_id, group_id)
    
    with exception_report(f"检查并更新用户 {qq_id} 在群 {group_id} 的昵称 / 群名片缓存"):
        if current_nickname != pinfo.nickname:
            db.dao.get_user_nickname_dao().set_current_nickname(qq_id, pinfo.nickname)
            logger.info(f"用户 {qq_id} 的昵称缓存已更新: {current_nickname} -> {pinfo.nickname}")
        if current_card != pinfo.card:
            db.dao.get_group_nickname_dao().set_current_group_nickname(qq_id, group_id, pinfo.card)
            logger.info(f"用户 {qq_id} 在群 {group_id} 的群名片缓存已更新: {current_card} -> {pinfo.card}")
    
async def s_update_user_avatar(qq_id: str):
    """
    更新用户头像，注意不要频繁调用引起堵塞
    """
    from .avatar_service import get_user_avatar

    with exception_report(f"更新用户 {qq_id} 头像"):
        avatar_bytes = await get_user_avatar(qq_id)
        db.dao.get_user_dao().update_user(qq_id, avatar_bytes)
