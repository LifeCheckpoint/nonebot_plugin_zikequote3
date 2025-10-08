-- v1 -> v2: 删除已废弃的 queue_group_message_counts 表

BEGIN TRANSACTION;

DROP TABLE IF EXISTS queue_group_message_counts;

PRAGMA user_version = 2;

COMMIT;