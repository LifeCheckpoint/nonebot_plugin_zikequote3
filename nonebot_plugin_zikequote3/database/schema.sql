-- 初始化数据库 Schema
-- 该文件在每次加载数据库时都会执行一次以确保完整性
-- 因此任何情况下都不要加入破坏性操作
-- 以下所有操作均幂等

BEGIN TRANSACTION;
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
    PRIMARY KEY (group_id, qq_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (qq_id) REFERENCES users(qq_id) ON DELETE CASCADE
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

-- 消息 ID 与语录 ID 映射表
CREATE TABLE IF NOT EXISTS msgid_quoteid_map (
    msg_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id) ON DELETE CASCADE
);

-- 群聊自定义配置表
CREATE TABLE IF NOT EXISTS group_configs (
    group_id TEXT PRIMARY KEY,
    toml_config TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE
);

COMMIT;

BEGIN TRANSACTION;

-- 索引优化
ANALYZE;

COMMIT;
