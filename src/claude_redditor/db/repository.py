"""Data access layer for Reddit Analyzer."""

from typing import List, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from .models import RedditPost, Classification, ScanHistory, Bookmark
from .connection import DatabaseConnection
from ..config import settings  # Import from parent directory
import logging

logger = logging.getLogger(__name__)


class Repository:
    """
    Data access layer.
    Abstracts all SQL logic from the rest of the app.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # ============ CLASSIFICATIONS ============

    def get_cached_classifications(
        self,
        post_ids: List[str],
        source: str = 'reddit',
        project: str = 'default'
    ) -> List[Dict]:
        """
        Get cached classifications (multi-source support).

        Args:
            post_ids: List of post IDs (with prefixes: reddit_abc123, hn_8863)
            source: Content source ('reddit' or 'hackernews')
            project: Project name (default: 'default')

        Returns:
            List of dicts with classification + post data
        """
        if not post_ids:
            return []

        with self.db.get_session() as session:
            results = session.execute(
                select(Classification, RedditPost)
                .join(RedditPost, Classification.post_id == RedditPost.id)
                .where(Classification.post_id.in_(post_ids))
                .where(Classification.source == source)
                .where(Classification.project == project)
            ).all()

            cached = []
            for classification, post in results:
                data = classification.to_dict()
                data['post'] = post.to_dict()
                cached.append(data)

            logger.info(f"Cache hit: {len(cached)}/{len(post_ids)} posts (source: {source})")
            return cached

    def save_classifications(
        self,
        classifications: List[Dict],
        source: str = 'reddit',
        model_version: str = "claude-haiku-4-5-20251001",
        project: str = 'default'
    ) -> None:
        """
        Save classifications (multi-source support).
        If already exists, replace (UPSERT).

        Args:
            classifications: List of classification dicts
            source: Content source ('reddit' or 'hackernews')
            model_version: Claude model version used
            project: Project name (default: 'default')
        """
        if not classifications:
            return

        with self.db.get_session() as session:
            for cls_data in classifications:
                # UPSERT using INSERT ... ON DUPLICATE KEY UPDATE
                stmt = insert(Classification).values(
                    post_id=cls_data['post_id'],
                    source=source,
                    project=project,
                    category=cls_data['category'],
                    confidence=cls_data['confidence'],
                    red_flags=cls_data.get('red_flags', []),
                    reasoning=cls_data.get('reasoning', ''),
                    model_version=model_version,
                    topic_tags=cls_data.get('topic_tags', []),
                    format_tag=cls_data.get('format_tag')
                )

                # On conflict: update
                stmt = stmt.on_duplicate_key_update(
                    source=stmt.inserted.source,
                    project=stmt.inserted.project,
                    category=stmt.inserted.category,
                    confidence=stmt.inserted.confidence,
                    red_flags=stmt.inserted.red_flags,
                    reasoning=stmt.inserted.reasoning,
                    model_version=stmt.inserted.model_version,
                    topic_tags=stmt.inserted.topic_tags,
                    format_tag=stmt.inserted.format_tag,
                    classified_at=func.now()
                )

                session.execute(stmt)

            logger.info(f"Saved {len(classifications)} classifications (source: {source})")

    # ============ POSTS ============

    def save_posts(self, posts: List[Dict], source: str = 'reddit', project: str = 'default') -> None:
        """
        Save posts from any source (multi-source support).
        INSERT IGNORE to avoid duplicates.

        Args:
            posts: List of post dicts (with prefixed IDs)
            source: Content source ('reddit' or 'hackernews')
            project: Project name (default: 'default')
        """
        if not posts:
            return

        with self.db.get_session() as session:
            for post_data in posts:
                # Check if exists
                exists = session.execute(
                    select(RedditPost).where(RedditPost.id == post_data['id'])
                ).first()

                if not exists:
                    post = RedditPost(
                        id=post_data['id'],
                        source=source,
                        project=project,
                        subreddit=post_data.get('subreddit'),  # Nullable for HN
                        title=post_data['title'],
                        author=post_data.get('author'),
                        score=post_data.get('score'),
                        num_comments=post_data.get('num_comments'),
                        created_utc=post_data.get('created_utc'),
                        url=post_data.get('url'),
                        selftext=post_data.get('selftext', '')[:settings.max_lines_article]
                    )
                    session.add(post)

            logger.info(f"Saved {len(posts)} posts (source: {source})")

    # ============ SCAN HISTORY ============

    def save_scan_history(
        self,
        subreddit: str,
        posts_fetched: int,
        posts_classified: int,
        posts_cached: int,
        signal_ratio: float,
        source: str = 'reddit',
        project: str = 'default'
    ) -> None:
        """
        Save scan to history (multi-source support).

        Args:
            subreddit: Subreddit name (for reddit) or "HackerNews" (for HN)
            posts_fetched: Total posts fetched
            posts_classified: New posts classified
            posts_cached: Posts from cache
            signal_ratio: Signal percentage
            source: Content source ('reddit' or 'hackernews')
            project: Project name (default: 'default')
        """
        with self.db.get_session() as session:
            scan = ScanHistory(
                subreddit=subreddit,
                source=source,
                project=project,
                posts_fetched=posts_fetched,
                posts_classified=posts_classified,
                posts_cached=posts_cached,
                signal_ratio=signal_ratio
            )
            session.add(scan)
            logger.info(f"Scan history saved: {subreddit} (source: {source}, project: {project})")

    def get_scan_history(
        self,
        subreddit: Optional[str] = None,
        limit: int = 10,
        project: Optional[str] = None
    ) -> List[Dict]:
        """
        Get scan history.

        Args:
            subreddit: Filter by subreddit (None = all)
            limit: Maximum results
            project: Filter by project (None = all)

        Returns:
            List of scan history dicts
        """
        with self.db.get_session() as session:
            query = select(ScanHistory).order_by(ScanHistory.scan_date.desc())

            if subreddit:
                query = query.where(ScanHistory.subreddit == subreddit)

            if project:
                query = query.where(ScanHistory.project == project)

            query = query.limit(limit)

            results = session.execute(query).scalars().all()
            return [scan.to_dict() for scan in results]

    # ============ STATS ============

    def get_classification_stats(self, subreddit: str, project: Optional[str] = None) -> Dict:
        """
        Aggregated stats by category.

        Args:
            subreddit: Subreddit name
            project: Filter by project (None = all)

        Returns:
            {'technical': 15, 'mystical': 8, ...}
        """
        with self.db.get_session() as session:
            query = select(
                Classification.category,
                func.count(Classification.id).label('count')
            ).join(RedditPost, Classification.post_id == RedditPost.id).where(RedditPost.subreddit == subreddit)

            if project:
                query = query.where(RedditPost.project == project)

            results = session.execute(query.group_by(Classification.category)).all()

            return {category: count for category, count in results}

    def get_total_cached_posts(self, project: Optional[str] = None) -> int:
        """Get total posts in cache."""
        with self.db.get_session() as session:
            query = select(func.count(RedditPost.id))

            if project:
                query = query.where(RedditPost.project == project)

            count = session.execute(query).scalar()
            return count or 0

    def get_total_classifications(self, project: Optional[str] = None) -> int:
        """Get total classifications."""
        with self.db.get_session() as session:
            query = select(func.count(Classification.id))

            if project:
                query = query.where(Classification.project == project)

            count = session.execute(query).scalar()
            return count or 0

    # ============ DIGEST ============

    def get_signal_posts_for_digest(
        self,
        project: str,
        limit: int = 15,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        Get top signal posts not yet sent in a digest.

        Returns posts with:
        - category in (technical, troubleshooting, research_verified)
        - sent_in_digest_at IS NULL
        - ordered by score DESC, confidence DESC

        Args:
            project: Project name
            limit: Maximum number of posts
            min_confidence: Minimum confidence threshold

        Returns:
            List of dicts with post, classification, and selftext_truncated flag
        """
        with self.db.get_session() as session:
            results = session.execute(
                select(RedditPost, Classification)
                .join(Classification, RedditPost.id == Classification.post_id)
                .where(Classification.project == project)
                .where(Classification.category.in_(['technical', 'troubleshooting', 'research_verified']))
                .where(Classification.sent_in_digest_at.is_(None))
                .where(Classification.confidence >= min_confidence)
                .order_by(RedditPost.score.desc(), Classification.confidence.desc())
                .limit(limit)
            ).all()

            return [
                {
                    'post': post.to_dict(),
                    'classification': classification.to_dict(),
                    'selftext_truncated': len(post.selftext or '') == 5000
                }
                for post, classification in results
            ]

    def mark_posts_as_sent_in_digest(
        self,
        post_ids: List[str],
        project: str
    ) -> int:
        """
        Mark posts as sent in digest (set sent_in_digest_at = NOW()).

        Args:
            post_ids: List of post IDs to mark
            project: Project name

        Returns:
            Number of rows updated
        """
        if not post_ids:
            return 0

        from sqlalchemy import update

        with self.db.get_session() as session:
            result = session.execute(
                update(Classification)
                .where(Classification.post_id.in_(post_ids))
                .where(Classification.project == project)
                .values(sent_in_digest_at=func.now())
            )
            session.commit()
            logger.info(f"Marked {result.rowcount} posts as sent in digest (project: {project})")
            return result.rowcount

    # ============ BOOKMARKS ============

    def add_bookmark(
        self,
        story_id: str,
        digest_date: str,
        story_title: str,
        story_url: str = '',
        story_source: str = '',
        story_category: str = '',
        story_topic_tags: List[str] = None,
        story_format_tag: str = None,
        notes: str = None,
        status: str = 'to_read'
    ) -> None:
        """
        Add a new bookmark.

        Args:
            story_id: Story ID (e.g., '2025-01-17-003')
            digest_date: Date string (YYYY-MM-DD)
            story_title: Title of the story
            story_url: URL of the story
            story_source: Source (e.g., 'r/ClaudeAI', 'HackerNews')
            story_category: Category (e.g., 'technical')
            story_topic_tags: List of topic tags
            story_format_tag: Format tag
            notes: Optional user notes
            status: Initial status (to_read, to_implement, done)
        """
        from datetime import datetime

        with self.db.get_session() as session:
            bookmark = Bookmark(
                story_id=story_id,
                digest_date=datetime.strptime(digest_date, '%Y-%m-%d').date(),
                story_title=story_title,
                story_url=story_url,
                story_source=story_source,
                story_category=story_category,
                story_topic_tags=story_topic_tags or [],
                story_format_tag=story_format_tag,
                notes=notes,
                status=status
            )
            session.add(bookmark)
            session.commit()
            logger.info(f"Added bookmark: {story_id}")

    def get_bookmarks(
        self,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get bookmarks, optionally filtered by status.

        Args:
            status: Filter by status (to_read, to_implement, done) or None for all
            limit: Maximum number of bookmarks to return

        Returns:
            List of bookmark dicts
        """
        with self.db.get_session() as session:
            query = select(Bookmark).order_by(Bookmark.bookmarked_at.desc())

            if status:
                query = query.where(Bookmark.status == status)

            query = query.limit(limit)

            result = session.execute(query)
            bookmarks = result.scalars().all()

            # Convert to dicts before session closes
            return [b.to_dict() for b in bookmarks]

    def update_bookmark_status(self, story_id: str, new_status: str) -> bool:
        """
        Update bookmark status.

        Args:
            story_id: Story ID to update
            new_status: New status (to_read, to_implement, done)

        Returns:
            True if updated, False if not found
        """
        from sqlalchemy import update

        with self.db.get_session() as session:
            result = session.execute(
                update(Bookmark)
                .where(Bookmark.story_id == story_id)
                .values(status=new_status)
            )
            session.commit()
            return result.rowcount > 0
