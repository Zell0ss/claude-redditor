-- Migration 005: Add sent_in_digest_at column for digest tracking
-- Date: 2026-01-14
-- Description: Adds 'sent_in_digest_at' TIMESTAMP to classifications table
--              to track which posts have been included in daily digest emails.
--
-- IMPORTANT: Backup your database before running this migration!
--   mysqldump reddit_analyzer > backup_before_005_$(date +%Y%m%d).sql

-- Add sent_in_digest_at column to classifications
ALTER TABLE classifications
ADD COLUMN sent_in_digest_at TIMESTAMP NULL
COMMENT 'When this post was included in a daily digest email'
AFTER classified_at;

-- Add index for efficient "not sent" queries
-- This index optimizes: WHERE project = ? AND category IN (...) AND sent_in_digest_at IS NULL
ALTER TABLE classifications
ADD INDEX idx_sent_in_digest (project, category, sent_in_digest_at);

-- Verify migration
SELECT 'Classifications table structure after migration:' AS status;
DESCRIBE classifications;

SELECT 'New index on classifications:' AS status;
SHOW INDEX FROM classifications WHERE Key_name = 'idx_sent_in_digest';

-- ==============================================================================
-- POST-MIGRATION NOTES
-- ==============================================================================
--
-- Usage:
--   reddit-analyzer digest --project claudeia --limit 15
--   reddit-analyzer digest --project claudeia --dry-run
--
-- The digest command will:
--   1. Query signal posts where sent_in_digest_at IS NULL
--   2. Generate Spanish news articles with radio host commentary
--   3. Mark posts as sent (SET sent_in_digest_at = NOW())
--
-- Rollback (if needed):
--   ALTER TABLE classifications DROP INDEX idx_sent_in_digest;
--   ALTER TABLE classifications DROP COLUMN sent_in_digest_at;
