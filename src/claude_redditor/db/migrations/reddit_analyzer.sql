SELECT source, fetched_at_date, count(*) 
FROM dashboard_view 
group by `source`, `fetched_at_date` 
ORDER BY `fetched_at_date` DESC;

select * from posts where selftext like "%Ghibli%" limit 10;


SELECT p.* , story_id
FROM posts p inner join bookmarks b on p.url = b.story_url
WHERE story_id = '2026-01-17-003'

ALTER TABLE bookmarks ADD COLUMN post_id VARCHAR(50) NULL COMMENT 'Original post ID (reddit_abc123 or hn_12345678)'; 
CREATE INDEX idx_bookmarks_post_id ON bookmarks(post_id);


CREATE VIEW v_rich_bookmark AS
  SELECT
      b.id,
      b.story_id,
      b.digest_date,
      b.bookmarked_at,
      b.notes,
      b.status,
      b.story_title,
      b.story_url,
      b.story_source,
      b.story_category,
      b.story_topic_tags,
      b.story_format_tag,
      b.post_id,
      -- From posts
      p.author,
      p.score,
      p.num_comments,
      -- From classifications
      c.confidence,
      c.red_flags,
      c.reasoning
  FROM bookmarks b
  LEFT JOIN posts p ON b.post_id = p.id
  LEFT JOIN classifications c ON b.post_id = c.post_id;

