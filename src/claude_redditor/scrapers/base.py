"""Base classes and models for multi-source scraping (Reddit, HackerNews, etc)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Post:
    """
    Generic post model that works across multiple sources (Reddit, HackerNews, etc).

    This normalized format allows the classifier and analyzer to work
    uniformly regardless of the source platform.
    """

    # Universal fields (all sources)
    id: str                      # Prefixed ID: "reddit_abc123" or "hn_8863"
    source: str                  # "reddit" or "hackernews"
    title: str                   # Post title
    url: str                     # Post URL
    author: str                  # Author username
    score: int                   # Upvotes/points
    num_comments: int            # Number of comments
    created_utc: float           # Unix timestamp

    # Optional fields (may be empty depending on source)
    selftext: str = ""           # Post body/text (Reddit selftext, HN text)
    source_url: str = ""         # Original URL if link post (HN external link)

    # Source-specific fields (nullable)
    subreddit: Optional[str] = None     # Reddit only
    flair: Optional[str] = None         # Reddit only
    hn_type: Optional[str] = None       # HackerNews only: "story", "comment", etc

    @property
    def truncated_selftext(self, max_length: int = 5000) -> str:
        """Return selftext truncated to max_length for classification."""
        if len(self.selftext) <= max_length:
            return self.selftext
        return self.selftext[:max_length] + "..."

    @property
    def created_date(self) -> datetime:
        """Convert UTC timestamp to datetime."""
        return datetime.fromtimestamp(self.created_utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization and Claude API."""
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "selftext": self.truncated_selftext,
            "author": self.author,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "url": self.url,
            "source_url": self.source_url,
            "subreddit": self.subreddit,
            "flair": self.flair,
            "hn_type": self.hn_type,
        }


def prefix_id(raw_id: str, source: str) -> str:
    """
    Generate prefixed ID for multi-source compatibility.

    Args:
        raw_id: Original ID from source (e.g., "abc123" from Reddit, "8863" from HN)
        source: Source name ("reddit" or "hackernews")

    Returns:
        Prefixed ID (e.g., "reddit_abc123" or "hn_8863")

    Examples:
        >>> prefix_id("abc123", "reddit")
        "reddit_abc123"
        >>> prefix_id("8863", "hackernews")
        "hn_8863"
    """
    if source == "reddit":
        return f"reddit_{raw_id}"
    elif source == "hackernews":
        return f"hn_{raw_id}"
    else:
        # Prefix with first 6 characters of source name for unknown sources
        # But would be better if a custom entry is used if new sources are added
        return f"{source[:6]}_{raw_id}"


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers (Reddit, HackerNews, etc).

    All scrapers must implement:
    - fetch_posts(): Fetch and normalize posts to Post objects
    - get_source_name(): Return source identifier ("reddit", "hackernews", etc)
    """

    @abstractmethod
    def fetch_posts(
        self,
        limit: int = 100,
        sort: str = "hot",
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts from the source and return normalized Post objects.

        Args:
            limit: Maximum number of posts to fetch
            sort: Sort method (source-specific)
            **kwargs: Additional source-specific parameters

        Returns:
            List of Post objects with prefixed IDs
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Return the source identifier.

        Returns:
            Source name: "reddit", "hackernews", etc
        """
        pass
