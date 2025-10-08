from ...imports import *
from pydantic import BaseModel, Field


class GroupInformation(BaseModel):
    """
    群组信息类型

    字段参考了 `cqhttp` 的老文档，不一定有效
    """
    group_id: int = Field(..., description="群号")
    group_name: str = Field(..., description="群名称")
    group_memo: Optional[str] = Field(None, description="群备注")
    group_create_time: Optional[int] = Field(None, description="群创建时间戳")
    group_level: Optional[int] = Field(None, description="群等级")
    member_count: Optional[int] = Field(None, description="群成员数")
    max_member_count: Optional[int] = Field(None, description="群最大成员数")


async def s_update_group_info_api(group_id: str, bot: Bot):
    """
    通过接口 API 更新 / 创建群组信息，带缓存机制
    """
    async with service_exception_a(f"获取群 {group_id} 的信息"):
        info = await bot.get_group_info(
            group_id=int(group_id),
            no_cache=False
        )

        ginfo = GroupInformation(
            group_id=int(group_id),
            group_name=info.get("group_name", ""),
            group_memo=info.get("group_memo"),
            group_create_time=info.get("group_create_time"),
            group_level=info.get("group_level"),
            member_count=info.get("member_count"),
            max_member_count=info.get("max_member_count"),
        )

    async with service_exception_a(f"更新群 {group_id} 的名称"):
        db.dao.get_group_dao().update_or_create_group(group_id, ginfo.group_name)
        logger.info(f"群 {group_id} 创建 / 名称更新为 {ginfo.group_name}")
