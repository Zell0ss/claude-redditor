-- Migration: Add 'unrelated' category for topic filtering
-- Date: 2026-01-12
-- Description: Adds 'unrelated' as a new category value for posts outside the configured topic scope

-- Add 'unrelated' to category enum in classifications table
ALTER TABLE classifications
MODIFY COLUMN category ENUM(
    'technical',
    'troubleshooting',
    'research_verified',
    'mystical',
    'unverified_claim',
    'engagement_bait',
    'community',
    'meme',
    'outlier',
    'unrelated'
) NOT NULL;

-- Verify migration
SELECT
    'Migration completed successfully' AS status,
    COUNT(*) AS total_classifications,
    COUNT(CASE WHEN category = 'unrelated' THEN 1 END) AS unrelated_count
FROM classifications;
