-- Migration 006: Add multi-tags support and bookmarks table
-- Date: 2025-01-17
-- Purpose: Sprint 0 - Schema for multi-tag classification and bookmark system

-- =============================================================================
-- Part 1: Add tag columns to classifications table
-- =============================================================================

-- topic_tags: Array of tags like ["prompts", "tools", "buildable"]
ALTER TABLE classifications
ADD COLUMN topic_tags JSON DEFAULT NULL
COMMENT 'Array of topic tags: prompts, tools, models, research, coding, buildable, hardware, troubleshooting, news, meta-tooling';

-- format_tag: Single tag like "tutorial", "showcase", "code-snippet"
ALTER TABLE classifications
ADD COLUMN format_tag VARCHAR(50) DEFAULT NULL
COMMENT 'Format tag: tutorial, showcase, discussion, question, resource, code-snippet';

-- digest_date: Date when included in a digest (for easier querying)
ALTER TABLE classifications
ADD COLUMN digest_date DATE DEFAULT NULL
COMMENT 'Date of the digest this post was included in';

-- Index for filtering by digest_date
CREATE INDEX idx_classifications_digest_date ON classifications(digest_date);

-- =============================================================================
-- Part 2: Create bookmarks table
-- =============================================================================

CREATE TABLE IF NOT EXISTS bookmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    story_id VARCHAR(50) NOT NULL UNIQUE COMMENT 'ID like "2025-01-17-003"',
    digest_date DATE NOT NULL COMMENT 'Date of the digest',


    bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When bookmarked',
    notes TEXT DEFAULT NULL COMMENT 'User notes',
    status ENUM('to_read', 'to_implement', 'done') NOT NULL DEFAULT 'to_read',

    story_title TEXT NOT NULL,
    story_url TEXT,
    story_source VARCHAR(50) COMMENT 'r/ClaudeAI or HackerNews',
    story_category VARCHAR(50) COMMENT 'technical, research, etc.',
    story_topic_tags JSON COMMENT 'Array of topic tags',
    story_format_tag VARCHAR(50) COMMENT 'tutorial, code-snippet, etc.',

    INDEX idx_bookmarks_digest_date (digest_date),
    INDEX idx_bookmarks_status (status),
    INDEX idx_bookmarks_bookmarked_at (bookmarked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Verification queries (run manually to check)
-- =============================================================================
-- DESCRIBE classifications;
-- DESCRIBE bookmarks;
-- SELECT COUNT(*) FROM classifications WHERE topic_tags IS NOT NULL;
