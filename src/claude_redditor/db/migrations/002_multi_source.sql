-- Migration 002: Multi-Source Support (Reddit + HackerNews)
--
-- This migration adds support for multiple content sources while maintaining
-- backward compatibility with existing data.
--
-- Key changes:
-- 1. Rename reddit_posts → posts (source-agnostic)
-- 2. Add `source` column to track content origin
-- 3. Add `source` column to classifications table
-- 4. Update indexes for performance
-- 5. Support prefixed IDs (reddit_abc123, hn_8863)
--
-- IMPORTANT: Backup your database before running this migration!
--   mysqldump reddit_analyzer > backup_before_002.sql

-- ==============================================================================
-- BACKUP (Recommended but commented out - uncomment if you want automatic backup)
-- ==============================================================================

-- Uncomment these lines to create automatic backups:
-- CREATE TABLE posts_backup_002 AS SELECT * FROM reddit_posts;
-- CREATE TABLE classifications_backup_002 AS SELECT * FROM classifications;

BEGIN;

-- ==============================================================================
-- STEP 1: Rename reddit_posts → posts
-- ==============================================================================

RENAME TABLE reddit_posts TO posts;

-- ==============================================================================
-- STEP 2: Add `source` column to posts table
-- ==============================================================================

ALTER TABLE posts
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
COMMENT 'Content source: reddit or hackernews'
AFTER id;

-- and make subreddit column nullable for HN posts
ALTER TABLE posts
MODIFY COLUMN subreddit VARCHAR(100) NULL
COMMENT 'Subreddit name (for reddit) or NULL (for HN source)';
-- ==============================================================================
-- STEP 3: Update existing Reddit post IDs with 'reddit_' prefix (if any exist)
-- ==============================================================================

-- WARNING: Only run this if you have existing data!
-- This will prefix all existing IDs with 'reddit_'
-- Comment out if running on fresh database or if IDs are already prefixed

-- IMPORTANT: Drop FK constraint first to allow ID updates
ALTER TABLE classifications DROP FOREIGN KEY classifications_ibfk_1;

-- Update post IDs with 'reddit_' prefix
UPDATE posts
SET id = CONCAT('reddit_', id)
WHERE source = 'reddit' AND id NOT LIKE 'reddit_%';

-- Update classification post_id references with 'reddit_' prefix
UPDATE classifications
SET post_id = CONCAT('reddit_', post_id)
WHERE post_id NOT LIKE 'reddit_%' AND post_id NOT LIKE 'hn_%';

-- Recreate FK constraint with correct table name (posts instead of reddit_posts)
ALTER TABLE classifications
ADD CONSTRAINT fk_classifications_posts
FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;

-- ==============================================================================
-- STEP 4: Add indexes for performance
-- ==============================================================================

-- Index on source column for filtered queries
ALTER TABLE posts
ADD INDEX idx_source (source);

-- Composite index for source + created_utc (common query pattern)
ALTER TABLE posts
ADD INDEX idx_source_created (source, created_utc DESC);

-- ==============================================================================
-- STEP 5: Update classifications table with source column
-- ==============================================================================

ALTER TABLE classifications
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
COMMENT 'Content source matching the post'
AFTER post_id;

-- Add index for source-based queries
ALTER TABLE classifications
ADD INDEX idx_source (source);

-- ==============================================================================
-- STEP 6: Update scan_history table to support multiple sources
-- ==============================================================================

-- Rename column comment to be source-agnostic
ALTER TABLE scan_history
MODIFY COLUMN subreddit VARCHAR(100) NULL
COMMENT 'Subreddit name (for reddit) or "HackerNews" (for HN source)';

-- Optional: Add source column to scan_history for explicit tracking
ALTER TABLE scan_history
ADD COLUMN source ENUM('reddit', 'hackernews') NULL
COMMENT 'Content source for this scan'
AFTER subreddit;

-- ==============================================================================
-- STEP 7: Verify migration
-- ==============================================================================

-- Show updated schema
DESCRIBE posts;
DESCRIBE classifications;
DESCRIBE scan_history;

COMMIT;

-- ==============================================================================
-- POST-MIGRATION NOTES
-- ==============================================================================

-- 1. ID Format:
--    - Reddit posts: reddit_abc123, reddit_xyz789
--    - HN posts: hn_8863, hn_12345
--
-- 2. Source Values:
--    - 'reddit' for Reddit posts
--    - 'hackernews' for HackerNews posts
--
-- 3. Query Examples:
--    - Get all HN posts: SELECT * FROM posts WHERE source = 'hackernews';
--    - Get Reddit posts from specific subreddit:
SELECT * FROM posts WHERE source = 'reddit' AND subreddit = 'ClaudeAI';
--    - Get all posts ordered by source:
SELECT * FROM posts ORDER BY source, created_utc DESC;
--
-- 4. Rollback (if needed):
--    - Restore from backup: mysql reddit_analyzer < backup_before_002.sql
