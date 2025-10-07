"""
语录数据迁移脚本
将旧的JSON格式语录数据迁移到新的SQL数据库
"""

import sys
sys.path.append(r"D:\wroot\nonebot-plugin-zikequote3\nonebot_plugin_zikequote3")

import json
import logging
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from database.connection_manager import ConnectionManager
from database.dao.user_dao import UserDAO
from database.dao.group_dao import GroupDAO
from database.dao.nickname_dao import UserNicknameDAO, GroupNicknameDAO
from database.dao.quote_dao import QuoteDAO
from database.dao.review_dao import ReviewDAO
from database.dao.group_member_dao import GroupMemberDAO
from database.models.users import UserCreate
from database.models.groups import GroupCreate
from database.models.user_nicknames import UserNicknameCreate
from database.models.group_nicknames import GroupNicknameCreate
from database.models.quotes import QuoteCreate
from database.models.reviews import ReviewCreate
from database.models.group_members import GroupMemberCreate


class QuoteMigration:
    """语录数据迁移类"""
    
    def __init__(self, json_data_path: str, db_path: str = "data/zikequote3.db"):
        """
        初始化迁移器
        
        Args:
            json_data_path: JSON数据目录路径
            db_path: 数据库文件路径
        """
        self.json_data_path = Path(json_data_path)
        self.db_path = db_path
        self.connection_manager = ConnectionManager(Path(db_path))
        
        # 初始化DAO
        self.user_dao = UserDAO(self.connection_manager)
        self.group_dao = GroupDAO(self.connection_manager)
        self.user_nickname_dao = UserNicknameDAO(self.connection_manager)
        self.group_nickname_dao = GroupNicknameDAO(self.connection_manager)
        self.quote_dao = QuoteDAO(self.connection_manager)
        self.review_dao = ReviewDAO(self.connection_manager)
        self.group_member_dao = GroupMemberDAO(self.connection_manager)
        
        # 数据缓存
        self.users_data: Dict[str, Dict] = {}  # user_id -> user_data
        self.groups_data: Dict[str, Dict] = {}  # group_id -> group_data
        self.quotes_data: List[Dict] = []
        self.reviews_data: List[Dict] = []
        
        # 昵称历史记录（用于确定最新昵称）
        self.user_nickname_history: Dict[str, List[Tuple[int, str]]] = {}  # user_id -> [(timestamp, nickname)]
        self.group_nickname_history: Dict[str, Dict[str, List[Tuple[int, str]]]] = {}  # group_id -> {user_id -> [(timestamp, card)]}
        
        self.logger = logging.getLogger(__name__)

    def _convert_id(self, original_id: int) -> str:
        """
        转换ID：负数转正数，模10^10，不足10位补随机数字
        
        Args:
            original_id: 原始ID
            
        Returns:
            转换后的10位ID字符串
        """
        converted_id = abs(original_id) % (10 ** 10)
        id_str = str(converted_id)
        
        # 如果不足10位，用随机数字补足到10位
        if len(id_str) < 10:
            import random
            # 生成随机数字补足到10位
            random_digits = ''.join(str(random.randint(0, 9)) for _ in range(10 - len(id_str)))
            id_str = id_str + random_digits
        
        return id_str

    def _convert_timestamp(self, unix_timestamp: int) -> str:
        """
        转换时间戳：Unix时间戳转ISO 8601格式
        
        Args:
            unix_timestamp: Unix时间戳
            
        Returns:
            ISO 8601格式的时间字符串
        """
        try:
            dt = datetime.fromtimestamp(unix_timestamp)
            return dt.isoformat()
        except (ValueError, OSError):
            self.logger.warning(f"无效的时间戳: {unix_timestamp}, 使用当前时间")
            return datetime.now().isoformat()

    def _parse_json_file(self, file_path: Path) -> Optional[Dict]:
        """
        解析JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            解析后的数据字典，解析失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"解析JSON文件失败 {file_path}: {e}")
            return None

    def _collect_nickname_history(self, quote_data: Dict, group_id: str):
        """
        收集昵称历史记录
        
        Args:
            quote_data: 语录数据
            group_id: 群组ID
        """
        author_id = str(quote_data.get('author_id', ''))
        author_name = quote_data.get('author_name', '')
        author_card = quote_data.get('author_card', '')
        timestamp = quote_data.get('time_stamp', 0)
        
        if author_id and author_name:
            if author_id not in self.user_nickname_history:
                self.user_nickname_history[author_id] = []
            self.user_nickname_history[author_id].append((timestamp, author_name))
        
        if author_id and author_card and group_id:
            if group_id not in self.group_nickname_history:
                self.group_nickname_history[group_id] = {}
            if author_id not in self.group_nickname_history[group_id]:
                self.group_nickname_history[group_id][author_id] = []
            self.group_nickname_history[group_id][author_id].append((timestamp, author_card))

    def _get_latest_nickname(self, user_id: str) -> Optional[str]:
        """
        获取用户最新昵称
        
        Args:
            user_id: 用户ID
            
        Returns:
            最新昵称，如果没有记录返回None
        """
        if user_id not in self.user_nickname_history:
            return None
        
        # 按时间戳降序排序，取最新的
        sorted_history = sorted(self.user_nickname_history[user_id], key=lambda x: x[0], reverse=True)
        return sorted_history[0][1] if sorted_history else None

    def _get_latest_group_card(self, group_id: str, user_id: str) -> Optional[str]:
        """
        获取用户在群中的最新群名片
        
        Args:
            group_id: 群组ID
            user_id: 用户ID
            
        Returns:
            最新群名片，如果没有记录返回None
        """
        if group_id not in self.group_nickname_history:
            return None
        if user_id not in self.group_nickname_history[group_id]:
            return None
        
        # 按时间戳降序排序，取最新的
        sorted_history = sorted(self.group_nickname_history[group_id][user_id], key=lambda x: x[0], reverse=True)
        return sorted_history[0][1] if sorted_history else None

    def load_json_data(self) -> bool:
        """
        加载所有JSON数据
        
        Returns:
            是否成功加载
        """
        if not self.json_data_path.exists():
            self.logger.error(f"JSON数据目录不存在: {self.json_data_path}")
            return False
        
        json_files = list(self.json_data_path.glob("*.json"))
        if not json_files:
            self.logger.warning(f"在目录 {self.json_data_path} 中没有找到JSON文件")
            return False
        
        self.logger.info(f"找到 {len(json_files)} 个JSON文件，开始加载数据...")
        
        # 用于跟踪已使用的评论ID，确保唯一性
        used_review_ids = set()
        
        for file_path in json_files:
            self.logger.debug(f"正在处理文件: {file_path}")
            data = self._parse_json_file(file_path)
            if not data:
                continue
            
            # 从文件名获取群组ID
            group_id = file_path.stem
            self.groups_data[group_id] = {
                'group_id': group_id,
                'name': f"group_{group_id}"
            }
            
            # 处理语录列表
            quote_list = data.get('quote_list', [])
            for quote_data in quote_list:
                # 收集用户信息
                author_id = str(quote_data.get('author_id', ''))
                if author_id and author_id not in self.users_data:
                    self.users_data[author_id] = {
                        'qq_id': author_id,
                        'avatar': None
                    }
                
                # 收集昵称历史
                self._collect_nickname_history(quote_data, group_id)
                
                # 转换语录数据
                converted_quote = {
                    'quote_id': self._convert_id(int(quote_data.get('quote_id', 0))),
                    'time_stamp': self._convert_timestamp(quote_data.get('time_stamp', 0)),
                    'author_id': author_id,
                    'group_id': group_id,
                    'content': quote_data.get('quote', ''),
                    'total_show_time': quote_data.get('show_time', 0)
                }
                self.quotes_data.append(converted_quote)
                
                # 处理评论数据
                comments = quote_data.get('comments', [])
                for comment in comments:
                    comment_author_id = str(comment.get('author_id', ''))
                    if comment_author_id and comment_author_id not in self.users_data:
                        self.users_data[comment_author_id] = {
                            'qq_id': comment_author_id,
                            'avatar': None,
                            'permission_group': 'normal'
                        }
                    
                    # 为评论生成随机的10位整数ID
                    while True:
                        new_review_id = str(random.randint(1000000000, 9999999999))
                        if new_review_id not in used_review_ids:
                            used_review_ids.add(new_review_id)
                            break
                    
                    converted_review = {
                        'review_id': new_review_id,
                        'time_stamp': self._convert_timestamp(comment.get('time_stamp', 0)),
                        'author_id': comment_author_id,
                        'quote_id': converted_quote['quote_id'],
                        'content': comment.get('content', '')
                    }
                    self.reviews_data.append(converted_review)
        
        self.logger.info(f"数据加载完成: 用户 {len(self.users_data)} 个, 群组 {len(self.groups_data)} 个, "
                        f"语录 {len(self.quotes_data)} 条, 评论 {len(self.reviews_data)} 条")
        return True

    def check_database_exists(self) -> bool:
        """
        检查数据库是否已存在
        
        Returns:
            数据库是否存在
        """
        return os.path.exists(self.db_path)

    def _user_exists(self, user_id: str) -> bool:
        """检查用户是否存在"""
        try:
            return self.user_dao.user_exists(user_id)
        except Exception:
            return False

    def migrate_users(self) -> bool:
        """迁移用户数据"""
        self.logger.info("开始迁移用户数据...")
        
        success_count = 0
        for user_id, user_data in self.users_data.items():
            # 检查用户是否已存在
            if self._user_exists(user_id):
                self.logger.debug(f"用户已存在，跳过: {user_id}")
                success_count += 1
                continue
            
            user_create = UserCreate(
                qq_id=user_data['qq_id'],
                avatar=user_data['avatar']
            )
            
            if self.user_dao._create_user(user_create):
                success_count += 1
            else:
                self.logger.warning(f"创建用户失败: {user_id}")
        
        self.logger.info(f"用户数据迁移完成: {success_count}/{len(self.users_data)} 个用户")
        return success_count > 0

    def _group_exists(self, group_id: str) -> bool:
        """检查群组是否存在"""
        try:
            return self.group_dao.group_exists(group_id)
        except Exception:
            return False

    def migrate_groups(self) -> bool:
        """迁移群组数据"""
        self.logger.info("开始迁移群组数据...")
        
        success_count = 0
        for group_id, group_data in self.groups_data.items():
            # 检查群组是否已存在
            if self._group_exists(group_id):
                self.logger.debug(f"群组已存在，跳过: {group_id}")
                success_count += 1
                continue
            
            group_create = GroupCreate(
                group_id=group_data['group_id'],
                name=group_data['name']
            )
            
            if self.group_dao._create_group(group_create):
                success_count += 1
            else:
                self.logger.warning(f"创建群组失败: {group_id}")
        
        self.logger.info(f"群组数据迁移完成: {success_count}/{len(self.groups_data)} 个群组")
        return success_count > 0

    def migrate_nicknames(self) -> bool:
        """迁移昵称数据"""
        self.logger.info("开始迁移昵称数据...")
        
        # 迁移用户昵称 - 保存所有历史昵称，标记最新的为当前使用
        user_nickname_count = 0
        for user_id, nickname_history in self.user_nickname_history.items():
            if not nickname_history:
                continue
                
            # 按时间戳排序，获取最新的昵称
            sorted_history = sorted(nickname_history, key=lambda x: x[0], reverse=True)
            latest_nickname = sorted_history[0][1] if sorted_history else None
            
            # 获取所有不同的昵称（去重）
            unique_nicknames = set(nickname for _, nickname in nickname_history)
            
            # 保存所有历史昵称
            for nickname in unique_nicknames:
                is_current = (nickname == latest_nickname)
                nickname_create = UserNicknameCreate(
                    qq_id=user_id,
                    current_using=is_current,
                    name=nickname
                )
                if self.user_nickname_dao._add_nickname(nickname_create):
                    user_nickname_count += 1
                else:
                    self.logger.warning(f"创建用户昵称失败: {user_id} - {nickname}")
        
        # 迁移群名片 - 保存所有历史群名片，每个群中标记最新的为当前使用
        group_nickname_count = 0
        for group_id, user_cards in self.group_nickname_history.items():
            for user_id, card_history in user_cards.items():
                if not card_history:
                    continue
                    
                # 按时间戳排序，获取最新的群名片
                sorted_history = sorted(card_history, key=lambda x: x[0], reverse=True)
                latest_card = sorted_history[0][1] if sorted_history else None
                
                # 获取所有不同的群名片（去重）
                unique_cards = set(card for _, card in card_history)
                
                # 保存所有历史群名片
                for card in unique_cards:
                    is_current = (card == latest_card)
                    nickname_create = GroupNicknameCreate(
                        qq_id=user_id,
                        group_id=group_id,
                        current_using=is_current,
                        name=card
                    )
                    if self.group_nickname_dao._add_group_nickname(nickname_create):
                        group_nickname_count += 1
                    else:
                        self.logger.warning(f"创建群名片失败: 群 {group_id} 用户 {user_id} - {card}")
        
        self.logger.info(f"昵称数据迁移完成: 用户昵称 {user_nickname_count} 个, 群名片 {group_nickname_count} 个")
        return True

    def _quote_exists(self, quote_id: str) -> bool:
        """检查语录是否存在"""
        try:
            quote = self.quote_dao.get_quote_by_id(quote_id)
            return quote is not None
        except Exception:
            return False

    def _review_exists(self, review_id: str) -> bool:
        """检查评论是否存在"""
        try:
            review = self.review_dao.get_review_by_id(review_id)
            return review is not None
        except Exception:
            return False

    def migrate_quotes(self) -> bool:
        """迁移语录数据"""
        self.logger.info("开始迁移语录数据...")
        
        success_count = 0
        for quote_data in self.quotes_data:
            # 检查语录是否已存在
            if self._quote_exists(quote_data['quote_id']):
                self.logger.debug(f"语录已存在，跳过: {quote_data['quote_id']}")
                success_count += 1
                continue
            
            quote_create = QuoteCreate(
                quote_id=quote_data['quote_id'],
                author_id=quote_data['author_id'],
                group_id=quote_data['group_id'],
                content=quote_data['content'],
                image_content_uuid=None,
                total_show_time=quote_data['total_show_time']
            )
            
            if self.quote_dao._create_quote(quote_create):
                success_count += 1
            else:
                self.logger.warning(f"创建语录失败: {quote_data['quote_id']}")
        
        self.logger.info(f"语录数据迁移完成: {success_count}/{len(self.quotes_data)} 条语录")
        return success_count > 0

    def migrate_reviews(self) -> bool:
        """迁移评论数据"""
        self.logger.info("开始迁移评论数据...")
        
        success_count = 0
        for review_data in self.reviews_data:
            # 检查评论是否已存在
            if self._review_exists(review_data['review_id']):
                self.logger.debug(f"评论已存在，跳过: {review_data['review_id']}")
                success_count += 1
                continue
            
            review_create = ReviewCreate(
                review_id=review_data['review_id'],
                author_id=review_data['author_id'],
                quote_id=review_data['quote_id'],
                content=review_data['content']
            )
            
            try:
                if self.review_dao._create_review(review_create):
                    success_count += 1
                else:
                    self.logger.warning(f"创建评论失败: {review_data['review_id']}")
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: reviews.review_id" in str(e):
                    self.logger.debug(f"评论已存在(IntegrityError)，跳过: {review_data['review_id']}")
                    success_count += 1
                else:
                    self.logger.error(f"创建评论时发生数据库错误: {review_data['review_id']}, 错误: {e}")
        
        self.logger.info(f"评论数据迁移完成: {success_count}/{len(self.reviews_data)} 条评论")
        return success_count > 0

    def migrate_group_members(self) -> bool:
        """迁移群成员关系数据"""
        self.logger.info("开始迁移群成员关系数据...")
        
        success_count = 0
        for group_id in self.groups_data:
            # 收集该群组中的所有用户
            group_users = set()
            for quote in self.quotes_data:
                if quote['group_id'] == group_id:
                    group_users.add(quote['author_id'])
            for review in self.reviews_data:
                if any(quote['quote_id'] == review['quote_id'] for quote in self.quotes_data if quote['group_id'] == group_id):
                    group_users.add(review['author_id'])
            
            for user_id in group_users:
                member_create = GroupMemberCreate(
                    qq_id=user_id,
                    group_id=group_id,
                    permission_group='normal'
                )
                
                if self.group_member_dao._create_group_member(member_create):
                    success_count += 1
                else:
                    self.logger.warning(f"创建群成员关系失败: 群 {group_id} 用户 {user_id}")
        
        self.logger.info(f"群成员关系迁移完成: {success_count} 个关系")
        return success_count > 0

    def run_migration(self) -> bool:
        """
        运行完整的数据迁移流程
        
        Returns:
            迁移是否成功
        """
        self.logger.info("开始数据迁移流程...")
        
        # 检查数据库是否已存在
        if self.check_database_exists():
            self.logger.error(f"数据库已存在: {self.db_path}，请先删除现有数据库再运行迁移")
            return False
        
        # 初始化数据库表结构
        try:
            schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
            self.connection_manager.initialize_db(schema_file)
            self.logger.info("数据库表结构初始化完成")
        except Exception as e:
            self.logger.error(f"数据库表结构初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 加载JSON数据
        if not self.load_json_data():
            self.logger.error("加载JSON数据失败")
            return False
        
        # 按顺序迁移数据（注意外键约束）
        migration_steps = [
            ("用户数据", self.migrate_users),
            ("群组数据", self.migrate_groups),
            ("昵称数据", self.migrate_nicknames),
            ("语录数据", self.migrate_quotes),
            ("评论数据", self.migrate_reviews),
            ("群成员关系", self.migrate_group_members)
        ]
        
        for step_name, migration_func in migration_steps:
            self.logger.info(f"正在迁移 {step_name}...")
            if not migration_func():
                self.logger.error(f"{step_name} 迁移失败")
                return False
        
        self.logger.info("数据迁移完成！")
        return True


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # JSON数据目录路径
    json_data_path = r"C:\Users\24352\AppData\Local\nonebot2\ZikeQuote3\quotes"
    # 数据库路径
    db_path = r"C:\Users\24352\AppData\Local\nonebot2\ZikeQuote3\quotes\zikequote3.db"
    
    # 创建迁移器并运行
    migration = QuoteMigration(json_data_path, db_path)
    
    if migration.run_migration():
        print("数据迁移成功完成！")
    else:
        print("数据迁移失败，请检查日志了解详情。")


if __name__ == "__main__":
    main()

    """
    ## 使用指南

    在最上面的 sys.path.append(...) 中，修改为 nonebot_plugin_zikequote3 插件的绝对路径。
    修改 main() 函数中的 json_data_path 和 db_path 变量为 JSON 数据目录和目标数据库路径。
    运行脚本进行数据迁移。
    """