"""
命令处理器子包。

汇总导出所有命令处理器模块，使上层 ``command/__init__.py`` 可一次性注册。
"""

from .add_quote_cmd import *
from .add_quote_comment_cmd import *
from .collecting_listener_cmd import *
from .config_cmd import *
from .get_privacy_cmd import *
from .get_quote_list_cmd import *
from .get_ranking_cmd import *
from .random_quote_card_cmd import *
from .random_quote_cmd import *
from .random_quote_image_cmd import *
from .remove_quote_cmd import *
from .remove_quote_comment_cmd import *
from .search_quote_cmd import *
from .update_quote_force_cmd import *
from .group_migration import *
from .get_user_info_cmd import *
from .help_cmd import *
