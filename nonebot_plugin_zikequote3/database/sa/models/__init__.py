"""
ORM 模型包 —— 导出所有 ORM 模型类。

包含 5 个基础实体模型和 7 个业务实体模型。
"""

# ---- 基础实体 ----
from .group import GroupModel
from .group_member import GroupMemberModel
from .group_nickname import GroupNicknameModel
from .user import UserModel
from .user_nickname import UserNicknameModel

# ---- 业务实体 ----
from .group_config import GroupConfigModel
from .image import ImageModel
from .mapping import MsgIdQuoteIdMapModel
from .msg_queue import MsgQueueModel
from .queue_count import QueueGroupMessageCountModel
from .quote import QuoteModel
from .review import ReviewModel

__all__ = [
    # 基础实体
    "GroupMemberModel",
    "GroupModel",
    "GroupNicknameModel",
    "UserModel",
    "UserNicknameModel",
    # 业务实体
    "GroupConfigModel",
    "ImageModel",
    "MsgIdQuoteIdMapModel",
    "MsgQueueModel",
    "QueueGroupMessageCountModel",
    "QuoteModel",
    "ReviewModel",
]
