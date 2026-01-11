"""Reddit scraper with dual-mode support (RSS or PRAW)."""

from typing import List
import time
import requests
import feedparser
import re

from ..config import settings
from .base import BaseScraper, Post, prefix_id


class RedditScraper(BaseScraper):
    """
    Dual-mode Reddit scraper:
    1. RSS feed (no auth): 10 req/min, zero setup
    2. PRAW (with auth): 60 req/min, requires app credentials
    """

    def __init__(self):
        """Initialize scraper in appropriate mode based on available credentials."""
        self.mode = self._detect_mode()
        self.last_request_time = 0

        if self.mode == "praw":
            self._init_praw()
        else:
            self._init_json()

    def get_source_name(self) -> str:
        """Return source identifier."""
        return "reddit"

    def _detect_mode(self) -> str:
        """Detect if Reddit credentials are available."""
        if settings.reddit_client_id and settings.reddit_client_secret:
            return "praw"
        return "json"

    def _init_praw(self):
        """Initialize PRAW (authenticated mode)."""
        try:
            import praw

            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
                check_for_updates=False,
            )
            self.rate_limit = 60
            print(f"✓ Reddit scraper: PRAW mode ({self.rate_limit} req/min)")
        except ImportError:
            print("⚠ PRAW not installed, falling back to RSS mode")
            self.mode = "json"
            self._init_json()

    def _init_json(self):
        """Initialize RSS mode (unauthenticated mode)."""
        # Use browser-like User-Agent to avoid blocks
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.rate_limit = 10
        print(f"✓ Reddit scraper: RSS mode ({self.rate_limit} req/min, no auth required)")

    def _rate_limit_wait(self):
        """Rate limiting: 6 seconds for JSON mode to stay under 10 req/min."""
        if self.mode == "json":
            elapsed = time.time() - self.last_request_time
            if elapsed < 6:
                time.sleep(6 - elapsed)
            self.last_request_time = time.time()

    def fetch_posts(
        self,
        subreddit_name: str,
        limit: int = 100,
        time_filter: str = "week",
        sort: str = "hot",
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts from Reddit and return normalized Post objects.

        Args:
            subreddit_name: Name of subreddit (without 'r/')
            limit: Number of posts (max 100)
            time_filter: Time filter for 'top' sort (hour, day, week, month, year, all)
            sort: Sort method (hot, new, top, rising)

        Returns:
            List of Post objects with prefixed IDs ("reddit_abc123")
        """
        if not subreddit_name:
            raise ValueError("subreddit_name is required for RedditScraper")

        if self.mode == "praw":
            return self._fetch_praw(subreddit_name, limit, time_filter, sort)
        else:
            return self._fetch_json(subreddit_name, limit, sort)

    def _fetch_praw(
        self, subreddit_name: str, limit: int, time_filter: str, sort: str
    ) -> List[Post]:
        """Fetch using PRAW."""
        subreddit = self.reddit.subreddit(subreddit_name)

        # Get posts based on sort method
        if sort == "hot":
            posts = subreddit.hot(limit=limit)
        elif sort == "new":
            posts = subreddit.new(limit=limit)
        elif sort == "top":
            posts = subreddit.top(time_filter=time_filter, limit=limit)
        elif sort == "rising":
            posts = subreddit.rising(limit=limit)
        else:
            posts = subreddit.hot(limit=limit)

        return [self._normalize_praw_post(post) for post in posts]

    def _fetch_json(
        self, subreddit_name: str, limit: int, sort: str
    ) -> List[Post]:
        """Fetch using RSS feed."""
        self._rate_limit_wait()

        # Reddit RSS feeds: /.rss for hot, /new/.rss for new, etc.
        if sort == "new":
            url = f"https://www.reddit.com/r/{subreddit_name}/new/.rss"
        elif sort == "top":
            url = f"https://www.reddit.com/r/{subreddit_name}/top/.rss"
        else:  # hot or rising (RSS doesn't have rising, use hot)
            url = f"https://www.reddit.com/r/{subreddit_name}/.rss"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                print(f"⚠ No posts found in RSS feed for r/{subreddit_name}")
                return []

            # Convert RSS entries to Post objects
            posts = []
            for entry in feed.entries[:limit]:
                posts.append(self._normalize_rss_entry(entry, subreddit_name))

            return posts

        except requests.exceptions.RequestException as e:
            print(f"⚠ Error fetching RSS feed: {e}")
            return []

    def _normalize_praw_post(self, post) -> Post:
        """Normalize PRAW post object to Post with prefixed ID."""
        raw_id = post.id
        prefixed_id = prefix_id(raw_id, "reddit")

        return Post(
            id=prefixed_id,
            source="reddit",
            title=post.title,
            selftext=post.selftext or "",
            author=str(post.author) if post.author else "[deleted]",
            score=post.score,
            num_comments=post.num_comments,
            created_utc=post.created_utc,
            url=post.url,
            source_url=post.url,
            subreddit=post.subreddit.display_name,
            flair=post.link_flair_text,
            hn_type=None,
        )

    def _normalize_rss_entry(self, entry, subreddit_name: str) -> Post:
        """
        Normalize RSS feed entry to Post with prefixed ID.
        Note: RSS has limited data - no score, comments count, or full selftext.
        """
        # Extract post ID from entry.id (format: t3_postid)
        raw_id = entry.id.split("_")[-1] if hasattr(entry, "id") else "unknown"
        prefixed_id = prefix_id(raw_id, "reddit")

        # Extract author from entry (if available)
        author = "[unknown]"
        if hasattr(entry, "author"):
            author = entry.author
        elif hasattr(entry, "authors") and entry.authors:
            author = entry.authors[0].get("name", "[unknown]")

        # Parse selftext from content if available
        selftext = ""
        if hasattr(entry, "content") and entry.content:
            # RSS content is HTML, extract text portion
            content_html = entry.content[0].get("value", "")
            # Simple HTML tag removal (basic approach)
            selftext = re.sub(r"<[^>]+>", "", content_html).strip()
        elif hasattr(entry, "summary"):
            selftext = re.sub(r"<[^>]+>", "", entry.summary).strip()

        # Parse timestamp
        created_utc = 0.0
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            created_utc = time.mktime(entry.published_parsed)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            created_utc = time.mktime(entry.updated_parsed)

        return Post(
            id=prefixed_id,
            source="reddit",
            title=entry.title if hasattr(entry, "title") else "[No title]",
            selftext=selftext[:settings.max_lines_article],  # Truncate based on config
            author=author,
            score=0,  # Not available in RSS
            num_comments=0,  # Not available in RSS
            created_utc=created_utc,
            url=entry.link if hasattr(entry, "link") else "",
            source_url=entry.link if hasattr(entry, "link") else "",
            subreddit=subreddit_name,
            flair=None,  # Not available in RSS
            hn_type=None,
        )

    def get_mode_info(self) -> dict:
        """Get information about the current scraper mode."""
        return {
            "mode": self.mode,
            "rate_limit": f"{self.rate_limit} req/min",
            "authenticated": self.mode == "praw",
        }
