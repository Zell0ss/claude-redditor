-- Migration 007: Add multi-tier tagging system
-- Date: 2026-01-28
-- Description: Adds tier_tags (9-tier classification), tier_clusters, and tier_scoring
--              to support deep analytical classification of posts

-- Add tier columns to classifications table
ALTER TABLE classifications
ADD COLUMN tier_tags JSON DEFAULT NULL
COMMENT '9-tier classification structure: {tier1: [...], tier2: [...], ..., tier9: [...]}';

ALTER TABLE classifications
ADD COLUMN tier_clusters JSON DEFAULT NULL
COMMENT 'Array of detected cluster descriptions from tier analysis';

ALTER TABLE classifications
ADD COLUMN tier_scoring INT DEFAULT NULL
COMMENT 'Scoring 30-95 based on tier pattern analysis';

-- Add index for scoring queries (useful for finding high-value content)
CREATE INDEX idx_classifications_tier_scoring ON classifications(tier_scoring);

-- Add tier fields to bookmarks table for denormalization
ALTER TABLE bookmarks
ADD COLUMN story_tier_tags JSON DEFAULT NULL
COMMENT '9-tier tags from source story (denormalized)';

ALTER TABLE bookmarks
ADD COLUMN story_tier_clusters JSON DEFAULT NULL
COMMENT 'Cluster descriptions from source story (denormalized)';

ALTER TABLE bookmarks
ADD COLUMN story_tier_scoring INT DEFAULT NULL
COMMENT 'Scoring from source story (denormalized)';

-- Verify changes
-- SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'classifications' AND COLUMN_NAME LIKE 'tier%';


SELECT 
  post_id, 
  category, 
  tier_scoring,
  JSON_EXTRACT(tier_tags, '$.tier1') as tier1_tags,
  JSON_LENGTH(tier_clusters) as num_clusters
FROM classifications
WHERE tier_tags IS NOT NULL
  AND project = 'claudeia'
ORDER BY classified_at DESC
LIMIT 5

SELECT 
  post_id, 
  category, 
  tier_scoring,
  JSON_EXTRACT(tier_tags, '$.tier1') as tier1_tags,
  JSON_EXTRACT(tier_tags, '$.tier2') as tier2_tags,
  JSON_EXTRACT(tier_tags, '$.tier3') as tier3_tags,
  JSON_LENGTH(tier_clusters) as cluster_count
FROM classifications
WHERE project = 'claudeia' 
  AND tier_tags IS NOT NULL
ORDER BY classified_at DESC;


SHOW COLUMNS FROM classifications LIKE 'tier%'

SELECT post_id, tier_scoring, tier_tags IS NOT NULL as has_tiers
FROM classifications 
WHERE project='claudeia'
ORDER BY classified_at DESC 
LIMIT 5;


UPDATE classifications
SET tier_tags = JSON_REPLACE(
    tier_tags,
    '$.tier1', JSON_ARRAY_APPEND('[]', '$', 
        JSON_EXTRACT(tier_tags, '$.tier1[0]')
    )
)
WHERE project = 'claudeia'
  AND tier_tags IS NOT NULL
  AND JSON_CONTAINS(CAST(tier_tags AS CHAR), '"[NEW:"');

UPDATE classifications
SET tier_tags = REPLACE(
    REPLACE(CAST(tier_tags AS CHAR), '"[NEW: ', '"'),
    ']"', '"'
)
WHERE project = 'claudeia'
  AND tier_tags IS NOT NULL
  AND CAST(tier_tags AS CHAR) LIKE '%"[NEW:%';

SELECT 
    post_id,
    CAST(tier_tags AS CHAR) as original,
    REPLACE(
        REPLACE(CAST(tier_tags AS CHAR), '"[NEW: ', '"'),
        ']"', '"'
    ) as cleaned
FROM classifications
WHERE project = 'claudeia'
  AND tier_tags IS NOT NULL
  AND CAST(tier_tags AS CHAR) LIKE '%"[NEW:%'
LIMIT 5;