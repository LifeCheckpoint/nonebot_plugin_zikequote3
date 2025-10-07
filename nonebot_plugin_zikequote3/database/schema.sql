-- 初始化数据库 Schema
-- 该文件在每次加载数据库时都会执行一次以确保完整性
-- 因此任何情况下都不要加入破坏性操作

-- 以下所有操作均幂等，且自动被游标事务化

PRAGMA user_version = 1;

-- 保存基本用户信息的表
CREATE TABLE IF NOT EXISTS users (
    qq_id TEXT PRIMARY KEY,
    avatar BLOB
);

-- 保存群组信息的表
CREATE TABLE IF NOT EXISTS groups (
    group_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

-- 保存当前 / 历史名称的表
CREATE TABLE IF NOT EXISTS user_nicknames (
    qq_id TEXT NOT NULL,
    current_using BOOLEAN NOT NULL DEFAULT FALSE,
    name TEXT NOT NULL,
    FOREIGN KEY (qq_id) REFERENCES users(qq_id)
);

-- 保存当前 / 历史群名片的表
CREATE TABLE IF NOT EXISTS group_nicknames (
    qq_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    current_using BOOLEAN NOT NULL DEFAULT FALSE,
    name TEXT NOT NULL,
    FOREIGN KEY (qq_id) REFERENCES users(qq_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

-- 保存用户群组关系的表
CREATE TABLE IF NOT EXISTS group_members (
    group_id TEXT NOT NULL,
    qq_id TEXT NOT NULL,
    permission_group TEXT NOT NULL DEFAULT 'normal',
    PRIMARY KEY (group_id, qq_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (qq_id) REFERENCES users(qq_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_group) REFERENCES permission_groups(group_name) ON DELETE SET DEFAULT
);

-- 保存语录的表
CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    content TEXT NOT NULL,
    image_content_uuid TEXT DEFAULT NULL,
    total_show_time INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES users(qq_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id),
    FOREIGN KEY (image_content_uuid) REFERENCES images(uuid) ON DELETE SET NULL
);

-- 保存语录评论的表
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_id TEXT NOT NULL,
    quote_id TEXT NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users(qq_id),
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id) ON DELETE CASCADE
);

-- 保存语录图片信息的表
CREATE TABLE IF NOT EXISTS images (
    uuid TEXT PRIMARY KEY,
    original_filename TEXT,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum_sha256 TEXT NOT NULL
);

-- 保存暂存信息的表，暂存当前尚未进行语录收集的聊天记录
CREATE TABLE IF NOT EXISTS msgs_queue (
    msg_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    qq_id TEXT NOT NULL,
    time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (qq_id) REFERENCES users(qq_id) ON DELETE CASCADE
);

-- 记录暂存情况的表，message_count > 设定阈值的时候重置并从暂存信息收集语录
CREATE TABLE IF NOT EXISTS queue_group_message_counts (
    group_id TEXT PRIMARY KEY,
    message_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE
);

-- 权限组
CREATE TABLE IF NOT EXISTS permission_groups (
    group_name TEXT PRIMARY KEY,
    be_collected BOOLEAN DEFAULT TRUE NOT NULL,
    get_quote BOOLEAN DEFAULT TRUE NOT NULL,
    add_quote BOOLEAN DEFAULT TRUE NOT NULL,
    search_quote BOOLEAN DEFAULT TRUE NOT NULL,
    review_quote BOOLEAN DEFAULT TRUE NOT NULL,
    update_quote_self BOOLEAN DEFAULT TRUE NOT NULL,
    update_quote_group BOOLEAN DEFAULT FALSE NOT NULL,
    delete_review_self BOOLEAN DEFAULT TRUE NOT NULL,
    delete_review_group BOOLEAN DEFAULT FALSE NOT NULL,
    delete_quote_self BOOLEAN DEFAULT TRUE NOT NULL,
    delete_quote_group BOOLEAN DEFAULT FALSE NOT NULL,
    modify_settings BOOLEAN DEFAULT FALSE NOT NULL,
    common_operations BOOLEAN DEFAULT TRUE NOT NULL,
    ban_others BOOLEAN DEFAULT FALSE NOT NULL,
    op_others BOOLEAN DEFAULT FALSE NOT NULL,
    banop_others BOOLEAN DEFAULT FALSE NOT NULL,
    others BOOLEAN DEFAULT FALSE NOT NULL
);

-- 消息 ID 与语录 ID 映射表
CREATE TABLE IF NOT EXISTS msgid_quoteid_map (
    msg_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id) ON DELETE CASCADE
);

-- 添加权限组
BEGIN TRANSACTION;
WITH new_permissions (
    group_name,
    be_collected, get_quote, add_quote, search_quote, review_quote,
    update_quote_self, update_quote_group,
    delete_review_self, delete_review_group,
    delete_quote_self, delete_quote_group,
    modify_settings, common_operations,
    ban_others, op_others, banop_others, others
) AS (
    VALUES
        -- normal 默认
        (
            'normal',
            TRUE, TRUE, TRUE, TRUE, TRUE,
            TRUE, FALSE,
            TRUE, FALSE,
            TRUE, FALSE,
            FALSE, TRUE,
            FALSE, FALSE, FALSE, FALSE
        ),
        -- ban 完全封禁
        (
            'ban',
            FALSE, FALSE, FALSE, FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE, FALSE, FALSE
        ),
        -- ban_cud 不能添加、修改、删除或评论
        (
            'ban_cud',
            TRUE, TRUE, FALSE, TRUE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE,
            FALSE, FALSE, FALSE, FALSE
        ),
        -- op 管理员
        (
            'op',
            TRUE, TRUE, TRUE, TRUE, TRUE,
            TRUE, TRUE,  -- 可修改群内其他语录
            TRUE, TRUE,  -- 可删除群内其他评论
            TRUE, TRUE,  -- 可删除群内其他语录
            FALSE, TRUE,
            TRUE, FALSE, FALSE, FALSE  -- 可 ban 普通用户
        ),
        -- root 最高权限
        (
            'root',
            TRUE, TRUE, TRUE, TRUE, TRUE,
            TRUE, TRUE,
            TRUE, TRUE,
            TRUE, TRUE,
            TRUE, TRUE, -- 可修改设置
            TRUE, TRUE, TRUE, TRUE -- 可设置他人 op
        )
)
INSERT INTO permission_groups (
    group_name,
    be_collected, get_quote, add_quote, search_quote, review_quote,
    update_quote_self, update_quote_group,
    delete_review_self, delete_review_group,
    delete_quote_self, delete_quote_group,
    modify_settings, common_operations,
    ban_others, op_others, banop_others, others
)
SELECT *
FROM new_permissions
WHERE NOT EXISTS (SELECT 1 FROM permission_groups);
COMMIT;

-- 群聊自定义配置表
CREATE TABLE IF NOT EXISTS group_configs (
    group_id TEXT PRIMARY KEY,
    toml_config TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE
);

-- 索引优化
ANALYZE;
