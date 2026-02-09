"""
基础实体 ORM 模型单元测试。

覆盖 5 个基础实体：UserModel, GroupModel, GroupMemberModel,
UserNicknameModel, GroupNicknameModel。

测试内容：DDL 验证、CRUD 基础、DTO 转换、from_create_dto、外键约束、relationship 加载。
"""

import pytest
from sqlalchemy import inspect as sa_inspect, select

from nonebot_plugin_zikequote3.database.sa.base import Base
from nonebot_plugin_zikequote3.database.sa.models import (
    GroupMemberModel,
    GroupModel,
    GroupNicknameModel,
    UserModel,
    UserNicknameModel,
)
from nonebot_plugin_zikequote3.database.models.users import User, UserCreate
from nonebot_plugin_zikequote3.database.models.groups import Group, GroupCreate
from nonebot_plugin_zikequote3.database.models.group_members import (
    GroupMember,
    GroupMemberCreate,
)
from nonebot_plugin_zikequote3.database.models.user_nicknames import (
    UserNickname,
    UserNicknameCreate,
)
from nonebot_plugin_zikequote3.database.models.group_nicknames import (
    GroupNickname,
    GroupNicknameCreate,
)


# ============================================================================
# DDL 验证
# ============================================================================


class TestDDL:
    """验证 ORM 模型生成的表结构与预期一致。"""

    def test_users_table_columns(self, async_engine):
        """users 表应包含 qq_id (PK) 和 avatar 列。"""
        table = Base.metadata.tables["users"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"qq_id", "avatar"}
        assert table.c.qq_id.primary_key

    def test_groups_table_columns(self, async_engine):
        """groups 表应包含 group_id (PK) 和 name 列。"""
        table = Base.metadata.tables["groups"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"group_id", "name"}
        assert table.c.group_id.primary_key

    def test_group_members_table_columns(self, async_engine):
        """group_members 表应包含联合主键 (group_id, qq_id)。"""
        table = Base.metadata.tables["group_members"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"group_id", "qq_id"}
        pk_cols = {c.name for c in table.primary_key.columns}
        assert pk_cols == {"group_id", "qq_id"}

    def test_user_nicknames_table_columns(self, async_engine):
        """user_nicknames 表应包含 id (PK), qq_id, current_using, name 列。"""
        table = Base.metadata.tables["user_nicknames"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"id", "qq_id", "current_using", "name"}
        assert table.c.id.primary_key

    def test_group_nicknames_table_columns(self, async_engine):
        """group_nicknames 表应包含 id (PK), qq_id, group_id, current_using, name 列。"""
        table = Base.metadata.tables["group_nicknames"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"id", "qq_id", "group_id", "current_using", "name"}
        assert table.c.id.primary_key


# ============================================================================
# UserModel CRUD + DTO
# ============================================================================


class TestUserModel:
    """UserModel 的 CRUD、DTO 转换测试。"""

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        user = UserModel(qq_id="10001", avatar=None)
        async_session.add(user)
        await async_session.flush()

        result = await async_session.get(UserModel, "10001")
        assert result is not None
        assert result.qq_id == "10001"
        assert result.avatar is None

    @pytest.mark.anyio
    async def test_update(self, async_session):
        user = UserModel(qq_id="10002", avatar=None)
        async_session.add(user)
        await async_session.flush()

        user.avatar = b"fake_avatar_data"
        await async_session.flush()

        refreshed = await async_session.get(UserModel, "10002")
        assert refreshed is not None
        assert refreshed.avatar == b"fake_avatar_data"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        user = UserModel(qq_id="10003")
        async_session.add(user)
        await async_session.flush()

        await async_session.delete(user)
        await async_session.flush()

        assert await async_session.get(UserModel, "10003") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        user = UserModel(qq_id="10004", avatar=b"img")
        async_session.add(user)
        await async_session.flush()

        dto = user.to_dto()
        assert isinstance(dto, User)
        assert dto.qq_id == "10004"
        assert dto.avatar == b"img"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        create_dto = UserCreate(qq_id="10005", avatar=None)
        user = UserModel.from_create_dto(create_dto)
        assert isinstance(user, UserModel)
        assert user.qq_id == "10005"

        async_session.add(user)
        await async_session.flush()
        assert await async_session.get(UserModel, "10005") is not None


# ============================================================================
# GroupModel CRUD + DTO
# ============================================================================


class TestGroupModel:
    """GroupModel 的 CRUD、DTO 转换测试。"""

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        group = GroupModel(group_id="90001", name="测试群1")
        async_session.add(group)
        await async_session.flush()

        result = await async_session.get(GroupModel, "90001")
        assert result is not None
        assert result.name == "测试群1"

    @pytest.mark.anyio
    async def test_update(self, async_session):
        group = GroupModel(group_id="90002", name="旧名称")
        async_session.add(group)
        await async_session.flush()

        group.name = "新名称"
        await async_session.flush()

        refreshed = await async_session.get(GroupModel, "90002")
        assert refreshed is not None
        assert refreshed.name == "新名称"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        group = GroupModel(group_id="90003", name="待删除群")
        async_session.add(group)
        await async_session.flush()

        await async_session.delete(group)
        await async_session.flush()

        assert await async_session.get(GroupModel, "90003") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        group = GroupModel(group_id="90004", name="DTO群")
        async_session.add(group)
        await async_session.flush()

        dto = group.to_dto()
        assert isinstance(dto, Group)
        assert dto.group_id == "90004"
        assert dto.name == "DTO群"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        create_dto = GroupCreate(group_id="90005", name="新建群")
        group = GroupModel.from_create_dto(create_dto)
        assert isinstance(group, GroupModel)

        async_session.add(group)
        await async_session.flush()
        assert await async_session.get(GroupModel, "90005") is not None


# ============================================================================
# GroupMemberModel CRUD + DTO + 外键 + relationship
# ============================================================================


class TestGroupMemberModel:
    """GroupMemberModel 的 CRUD、DTO 转换、外键约束、relationship 测试。"""

    async def _create_user_and_group(self, session, uid="20001", gid="80001"):
        """辅助方法：创建前置的 User 和 Group。"""
        user = UserModel(qq_id=uid)
        group = GroupModel(group_id=gid, name=f"群{gid}")
        session.add_all([user, group])
        await session.flush()
        return user, group

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await self._create_user_and_group(async_session, "20001", "80001")
        member = GroupMemberModel(group_id="80001", qq_id="20001")
        async_session.add(member)
        await async_session.flush()

        result = await async_session.get(GroupMemberModel, ("80001", "20001"))
        assert result is not None
        assert result.group_id == "80001"
        assert result.qq_id == "20001"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await self._create_user_and_group(async_session, "20002", "80002")
        member = GroupMemberModel(group_id="80002", qq_id="20002")
        async_session.add(member)
        await async_session.flush()

        await async_session.delete(member)
        await async_session.flush()

        assert await async_session.get(GroupMemberModel, ("80002", "20002")) is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await self._create_user_and_group(async_session, "20003", "80003")
        member = GroupMemberModel(group_id="80003", qq_id="20003")
        async_session.add(member)
        await async_session.flush()

        dto = member.to_dto()
        assert isinstance(dto, GroupMember)
        assert dto.group_id == "80003"
        assert dto.qq_id == "20003"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await self._create_user_and_group(async_session, "20004", "80004")
        create_dto = GroupMemberCreate(group_id="80004", qq_id="20004")
        member = GroupMemberModel.from_create_dto(create_dto)
        assert isinstance(member, GroupMemberModel)

        async_session.add(member)
        await async_session.flush()
        assert await async_session.get(GroupMemberModel, ("80004", "20004")) is not None

    @pytest.mark.anyio
    async def test_relationship_to_user_and_group(self, async_session):
        """relationship 能正确加载关联的 User 和 Group。"""
        user, group = await self._create_user_and_group(
            async_session, "20005", "80005"
        )
        member = GroupMemberModel(group_id="80005", qq_id="20005")
        async_session.add(member)
        await async_session.flush()

        # 通过 relationship 访问
        assert member.user.qq_id == "20005"
        assert member.group.group_id == "80005"


# ============================================================================
# UserNicknameModel CRUD + DTO + relationship
# ============================================================================


class TestUserNicknameModel:
    """UserNicknameModel 的 CRUD、DTO 转换、relationship 测试。"""

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        user = UserModel(qq_id="30001")
        async_session.add(user)
        await async_session.flush()

        nick = UserNicknameModel(qq_id="30001", current_using=True, name="昵称A")
        async_session.add(nick)
        await async_session.flush()

        result = await async_session.get(UserNicknameModel, nick.id)
        assert result is not None
        assert result.name == "昵称A"
        assert result.current_using is True

    @pytest.mark.anyio
    async def test_update(self, async_session):
        user = UserModel(qq_id="30002")
        async_session.add(user)
        await async_session.flush()

        nick = UserNicknameModel(qq_id="30002", current_using=True, name="旧昵称")
        async_session.add(nick)
        await async_session.flush()

        nick.current_using = False
        nick.name = "新昵称"
        await async_session.flush()

        refreshed = await async_session.get(UserNicknameModel, nick.id)
        assert refreshed is not None
        assert refreshed.name == "新昵称"
        assert refreshed.current_using is False

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        user = UserModel(qq_id="30003")
        async_session.add(user)
        await async_session.flush()

        nick = UserNicknameModel(qq_id="30003", current_using=False, name="待删除")
        async_session.add(nick)
        await async_session.flush()
        nick_id = nick.id

        await async_session.delete(nick)
        await async_session.flush()

        assert await async_session.get(UserNicknameModel, nick_id) is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        user = UserModel(qq_id="30004")
        async_session.add(user)
        await async_session.flush()

        nick = UserNicknameModel(qq_id="30004", current_using=True, name="DTO昵称")
        async_session.add(nick)
        await async_session.flush()

        dto = nick.to_dto()
        assert isinstance(dto, UserNickname)
        assert dto.qq_id == "30004"
        assert dto.current_using is True
        assert dto.name == "DTO昵称"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        user = UserModel(qq_id="30005")
        async_session.add(user)
        await async_session.flush()

        create_dto = UserNicknameCreate(
            qq_id="30005", current_using=False, name="新建昵称"
        )
        nick = UserNicknameModel.from_create_dto(create_dto)
        assert isinstance(nick, UserNicknameModel)

        async_session.add(nick)
        await async_session.flush()
        assert await async_session.get(UserNicknameModel, nick.id) is not None

    @pytest.mark.anyio
    async def test_relationship_to_user(self, async_session):
        """relationship 能正确加载关联的 User。"""
        user = UserModel(qq_id="30006")
        async_session.add(user)
        await async_session.flush()

        nick = UserNicknameModel(qq_id="30006", current_using=True, name="关联测试")
        async_session.add(nick)
        await async_session.flush()

        assert nick.user.qq_id == "30006"


# ============================================================================
# GroupNicknameModel CRUD + DTO + relationship
# ============================================================================


class TestGroupNicknameModel:
    """GroupNicknameModel 的 CRUD、DTO 转换、relationship 测试。"""

    async def _create_user_and_group(self, session, uid="40001", gid="70001"):
        user = UserModel(qq_id=uid)
        group = GroupModel(group_id=gid, name=f"群{gid}")
        session.add_all([user, group])
        await session.flush()

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await self._create_user_and_group(async_session, "40001", "70001")
        nick = GroupNicknameModel(
            qq_id="40001", group_id="70001", current_using=True, name="群名片A"
        )
        async_session.add(nick)
        await async_session.flush()

        result = await async_session.get(GroupNicknameModel, nick.id)
        assert result is not None
        assert result.name == "群名片A"
        assert result.current_using is True

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await self._create_user_and_group(async_session, "40002", "70002")
        nick = GroupNicknameModel(
            qq_id="40002", group_id="70002", current_using=True, name="旧群名片"
        )
        async_session.add(nick)
        await async_session.flush()

        nick.current_using = False
        nick.name = "新群名片"
        await async_session.flush()

        refreshed = await async_session.get(GroupNicknameModel, nick.id)
        assert refreshed is not None
        assert refreshed.name == "新群名片"
        assert refreshed.current_using is False

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await self._create_user_and_group(async_session, "40003", "70003")
        nick = GroupNicknameModel(
            qq_id="40003", group_id="70003", current_using=False, name="待删除"
        )
        async_session.add(nick)
        await async_session.flush()
        nick_id = nick.id

        await async_session.delete(nick)
        await async_session.flush()

        assert await async_session.get(GroupNicknameModel, nick_id) is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await self._create_user_and_group(async_session, "40004", "70004")
        nick = GroupNicknameModel(
            qq_id="40004", group_id="70004", current_using=True, name="DTO群名片"
        )
        async_session.add(nick)
        await async_session.flush()

        dto = nick.to_dto()
        assert isinstance(dto, GroupNickname)
        assert dto.qq_id == "40004"
        assert dto.group_id == "70004"
        assert dto.current_using is True
        assert dto.name == "DTO群名片"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await self._create_user_and_group(async_session, "40005", "70005")
        create_dto = GroupNicknameCreate(
            qq_id="40005", group_id="70005", current_using=False, name="新建群名片"
        )
        nick = GroupNicknameModel.from_create_dto(create_dto)
        assert isinstance(nick, GroupNicknameModel)

        async_session.add(nick)
        await async_session.flush()
        assert await async_session.get(GroupNicknameModel, nick.id) is not None

    @pytest.mark.anyio
    async def test_relationship_to_group(self, async_session):
        """relationship 能正确加载关联的 Group。"""
        await self._create_user_and_group(async_session, "40006", "70006")
        nick = GroupNicknameModel(
            qq_id="40006", group_id="70006", current_using=True, name="关联测试"
        )
        async_session.add(nick)
        await async_session.flush()

        # async session 需要显式 refresh 来加载 lazy relationship
        await async_session.refresh(nick, ["group"])
        assert nick.group.group_id == "70006"

    @pytest.mark.anyio
    async def test_relationship_to_user(self, async_session):
        """relationship 能正确加载关联的 User。"""
        await self._create_user_and_group(async_session, "40007", "70007")
        nick = GroupNicknameModel(
            qq_id="40007", group_id="70007", current_using=False, name="用户关联"
        )
        async_session.add(nick)
        await async_session.flush()

        # async session 需要显式 refresh 来加载 lazy relationship
        await async_session.refresh(nick, ["user"])
        assert nick.user.qq_id == "40007"
