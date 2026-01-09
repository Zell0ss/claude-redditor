-- Reddit Analyzer - Initial Schema
-- Compatible with MariaDB 10.2+

CREATE DATABASE IF NOT EXISTS reddit_analyzer
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE reddit_analyzer;

-- Table 1: Posts
CREATE TABLE IF NOT EXISTS reddit_posts (
    id VARCHAR(20) PRIMARY KEY COMMENT 'Reddit post ID',
    subreddit VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    author VARCHAR(100),
    score INT,
    num_comments INT,
    created_utc BIGINT COMMENT 'Unix timestamp',
    url TEXT,
    selftext TEXT COMMENT 'Truncated to 1000 chars',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_subreddit (subreddit),
    INDEX idx_created (created_utc),
    INDEX idx_fetched (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 2: Classifications
CREATE TABLE IF NOT EXISTS classifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id VARCHAR(20) NOT NULL,
    category ENUM(
        'technical', 'troubleshooting', 'research_verified',
        'mystical', 'unverified_claim', 'engagement_bait',
        'community', 'meme', 'outlier'
    ) NOT NULL,
    confidence DECIMAL(3,2) COMMENT '0.00-1.00',
    red_flags JSON COMMENT 'Array of red flags detected',
    reasoning TEXT,
    model_version VARCHAR(50) DEFAULT 'claude-haiku-4-5-20251001',
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_post (post_id),
    FOREIGN KEY (post_id) REFERENCES reddit_posts(id) ON DELETE CASCADE,
    INDEX idx_category (category),
    INDEX idx_classified_at (classified_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 3: Scan History
CREATE TABLE IF NOT EXISTS scan_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subreddit VARCHAR(100) NOT NULL,
    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posts_fetched INT COMMENT 'Total posts obtained from Reddit',
    posts_classified INT COMMENT 'New posts classified',
    posts_cached INT COMMENT 'Posts obtained from cache',
    signal_ratio DECIMAL(5,2) COMMENT 'Signal percentage',

    INDEX idx_subreddit_date (subreddit, scan_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Show tables created
SHOW TABLES;
