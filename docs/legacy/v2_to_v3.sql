-- v2 to v3，不再强制要求语录存在，只需要语录内容和图片内容至少存在一个

BEGIN TRANSACTION;

PRAGMA foreign_keys=OFF;

-- `content` 列不再有 `NOT NULL` 约束。
-- 在表末尾添加了新的 `CHECK` 约束。
CREATE TABLE quotes_new (
    quote_id TEXT PRIMARY KEY,
    time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    content TEXT,
    image_content_uuid TEXT DEFAULT NULL,
    total_show_time INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES users(qq_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id),
    FOREIGN KEY (image_content_uuid) REFERENCES images(uuid) ON DELETE SET NULL,
    -- 添加新的 CHECK 约束，确保 content 和 image_content_uuid 至少有一个不为 NULL
    CHECK (content IS NOT NULL OR image_content_uuid IS NOT NULL)
);

-- 将旧 `quotes` 表中的所有数据复制到新表 `quotes_new`。
-- 由于旧表中的 `content` 字段本身就是 NOT NULL，所以所有现有数据都符合新的 CHECK 约束，数据迁移不会失败。
INSERT INTO quotes_new (quote_id, time_stamp, author_id, group_id, content, image_content_uuid, total_show_time)
SELECT quote_id, time_stamp, author_id, group_id, content, image_content_uuid, total_show_time
FROM quotes;

DROP TABLE quotes;

ALTER TABLE quotes_new RENAME TO quotes;

PRAGMA user_version = 3;

COMMIT;

BEGIN TRANSACTION;

ANALYZE;

COMMIT;