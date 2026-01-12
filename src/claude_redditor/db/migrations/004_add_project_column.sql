-- Migration: Add 'project' column for multi-project isolation
-- Date: 2026-01-12
-- Description: Adds 'project' VARCHAR(50) to posts, classifications, and scan_history tables
--              to support multi-project isolation (e.g., "claudeia" vs "wineworld")
--
-- This allows the same codebase/database to analyze different content domains independently:
-- - ClaudeIA: AI/LLM content (podcast sourcing)
-- - WineWorld: Wine industry content (blog sourcing)
--
-- IMPORTANT: Backup your database before running this migration!
--   mysqldump reddit_analyzer > backup_before_004_$(date +%Y%m%d).sql

BEGIN;

-- ==============================================================================
-- STEP 1: Add project column to posts table
-- ==============================================================================

ALTER TABLE posts
ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'default'
COMMENT 'Project identifier (e.g., "claudeia", "wineworld")' AFTER source;

-- Add indexes for efficient project-based filtering
ALTER TABLE posts ADD INDEX idx_project (project);
ALTER TABLE posts ADD INDEX idx_project_source_created (project, source, created_utc DESC);

-- ==============================================================================
-- STEP 2: Add project column to classifications table
-- ==============================================================================

ALTER TABLE classifications
ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'default'
COMMENT 'Project identifier (matches post.project)' AFTER source;

-- Add indexes for project-based queries
ALTER TABLE classifications ADD INDEX idx_project (project);
ALTER TABLE classifications ADD INDEX idx_project_category (project, category);

-- Update UNIQUE constraint to include project
-- (allows same post_id to have different classifications per project)
ALTER TABLE classifications DROP INDEX unique_post;
ALTER TABLE classifications ADD UNIQUE KEY unique_post_project (post_id, project);

-- ==============================================================================
-- STEP 3: Add project column to scan_history table
-- ==============================================================================

ALTER TABLE scan_history
ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'default'
COMMENT 'Project identifier for this scan' AFTER source;

-- Add indexes for project filtering and history queries
ALTER TABLE scan_history ADD INDEX idx_project (project);
ALTER TABLE scan_history ADD INDEX idx_project_subreddit_date (project, subreddit, scan_date DESC);

-- ==============================================================================
-- STEP 4: Verify migration success
-- ==============================================================================

-- Display updated table structures
SELECT 'posts table structure:' AS status;
DESCRIBE posts;

SELECT 'classifications table structure:' AS status;
DESCRIBE classifications;

SELECT 'scan_history table structure:' AS status;
DESCRIBE scan_history;

-- Show new indexes
SELECT 'New indexes on classifications:' AS status;
SHOW INDEX FROM classifications WHERE Key_name LIKE '%project%';

SELECT 'New indexes on scan_history:' AS status;
SHOW INDEX FROM scan_history WHERE Key_name LIKE '%project%';

-- Show current data distribution by project (should all be 'default')
SELECT 'Current project distribution:' AS status;
SELECT
    'posts' AS table_name,
    project,
    COUNT(*) AS count
FROM posts
GROUP BY project
UNION ALL
SELECT
    'classifications',
    project,
    COUNT(*)
FROM classifications
GROUP BY project
UNION ALL
SELECT
    'scan_history',
    project,
    COUNT(*)
FROM scan_history
GROUP BY project;

COMMIT;

-- ==============================================================================
-- POST-MIGRATION NOTES
-- ==============================================================================

-- Migration completed successfully!
--
-- Usage Notes:
-- 1. All existing data has been assigned to project='default'
-- 2. New scans must specify --project flag (e.g., --project claudeia)
-- 3. Projects are isolated - same post can have different classifications per project
-- 4. UNIQUE constraint is now (post_id, project) instead of just post_id
--
-- Example Commands:
--   ./reddit-analyzer scan all --project claudeia --limit 50
--   ./reddit-analyzer scan-hn --project wineworld --limit 100
--   ./reddit-analyzer history --project claudeia
--
-- Rollback (if needed):
--   mysql reddit_analyzer < backup_before_004_YYYYMMDD.sql
