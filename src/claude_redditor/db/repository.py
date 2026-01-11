"""Data access layer for Reddit Analyzer."""

from typing import List, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from .models import RedditPost, Classification, ScanHistory
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
        source: str = 'reddit'
    ) -> List[Dict]:
        """
        Get cached classifications (multi-source support).

        Args:
            post_ids: List of post IDs (with prefixes: reddit_abc123, hn_8863)
            source: Content source ('reddit' or 'hackernews')

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
        model_version: str = "claude-haiku-4-5-20251001"
    ) -> None:
        """
        Save classifications (multi-source support).
        If already exists, replace (UPSERT).

        Args:
            classifications: List of classification dicts
            source: Content source ('reddit' or 'hackernews')
            model_version: Claude model version used
        """
        if not classifications:
            return

        with self.db.get_session() as session:
            for cls_data in classifications:
                # UPSERT using INSERT ... ON DUPLICATE KEY UPDATE
                stmt = insert(Classification).values(
                    post_id=cls_data['post_id'],
                    source=source,
                    category=cls_data['category'],
                    confidence=cls_data['confidence'],
                    red_flags=cls_data.get('red_flags', []),
                    reasoning=cls_data.get('reasoning', ''),
                    model_version=model_version
                )

                # On conflict: update
                stmt = stmt.on_duplicate_key_update(
                    source=stmt.inserted.source,
                    category=stmt.inserted.category,
                    confidence=stmt.inserted.confidence,
                    red_flags=stmt.inserted.red_flags,
                    reasoning=stmt.inserted.reasoning,
                    model_version=stmt.inserted.model_version,
                    classified_at=func.now()
                )

                session.execute(stmt)

            logger.info(f"Saved {len(classifications)} classifications (source: {source})")

    # ============ POSTS ============

    def save_posts(self, posts: List[Dict], source: str = 'reddit') -> None:
        """
        Save posts from any source (multi-source support).
        INSERT IGNORE to avoid duplicates.

        Args:
            posts: List of post dicts (with prefixed IDs)
            source: Content source ('reddit' or 'hackernews')
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
        source: str = 'reddit'
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
        """
        with self.db.get_session() as session:
            scan = ScanHistory(
                subreddit=subreddit,
                source=source,
                posts_fetched=posts_fetched,
                posts_classified=posts_classified,
                posts_cached=posts_cached,
                signal_ratio=signal_ratio
            )
            session.add(scan)
            logger.info(f"Scan history saved: {subreddit} (source: {source})")

    def get_scan_history(
        self,
        subreddit: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get scan history.

        Args:
            subreddit: Filter by subreddit (None = all)
            limit: Maximum results

        Returns:
            List of scan history dicts
        """
        with self.db.get_session() as session:
            query = select(ScanHistory).order_by(ScanHistory.scan_date.desc())

            if subreddit:
                query = query.where(ScanHistory.subreddit == subreddit)

            query = query.limit(limit)

            results = session.execute(query).scalars().all()
            return [scan.to_dict() for scan in results]

    # ============ STATS ============

    def get_classification_stats(self, subreddit: str) -> Dict:
        """
        Aggregated stats by category.

        Args:
            subreddit: Subreddit name

        Returns:
            {'technical': 15, 'mystical': 8, ...}
        """
        with self.db.get_session() as session:
            results = session.execute(
                select(
                    Classification.category,
                    func.count(Classification.id).label('count')
                )
                .join(RedditPost, Classification.post_id == RedditPost.id)
                .where(RedditPost.subreddit == subreddit)
                .group_by(Classification.category)
            ).all()

            return {category: count for category, count in results}

    def get_total_cached_posts(self) -> int:
        """Get total posts in cache."""
        with self.db.get_session() as session:
            count = session.execute(
                select(func.count(RedditPost.id))
            ).scalar()
            return count or 0

    def get_total_classifications(self) -> int:
        """Get total classifications."""
        with self.db.get_session() as session:
            count = session.execute(
                select(func.count(Classification.id))
            ).scalar()
            return count or 0
