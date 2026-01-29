"""Data models for the Reddit analyzer."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from .enums import CategoryEnum


@dataclass
class RedditPost:
    """Represents a Reddit post with relevant metadata."""

    id: str
    title: str
    selftext: str
    author: str
    score: int
    num_comments: int
    created_utc: float
    url: str
    subreddit: str
    flair: Optional[str] = None

    @property
    def truncated_selftext(self, max_length: int = 5000) -> str:
        """Return selftext truncated to max_length characters for classification."""
        if len(self.selftext) <= max_length:
            return self.selftext
        return self.selftext[:max_length] + "..."

    @property
    def created_date(self) -> datetime:
        """Convert UTC timestamp to datetime."""
        return datetime.fromtimestamp(self.created_utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "selftext": self.truncated_selftext,
            "author": self.author,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "url": self.url,
            "subreddit": self.subreddit,
            "flair": self.flair,
        }


@dataclass
class Classification:
    """Classification result for a Reddit post."""

    post_id: str
    category: CategoryEnum
    confidence: float
    red_flags: List[str] = field(default_factory=list)
    reasoning: str = ""
    topic_tags: List[str] = field(default_factory=list)
    format_tag: Optional[str] = None
    # Multi-tier tagging system (9 tiers + scoring + clusters)
    tier_tags: Optional[Dict[str, List[str]]] = None
    tier_clusters: List[str] = field(default_factory=list)
    tier_scoring: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "post_id": self.post_id,
            "category": self.category.value,
            "confidence": self.confidence,
            "red_flags": self.red_flags,
            "reasoning": self.reasoning,
            "topic_tags": self.topic_tags,
            "format_tag": self.format_tag,
            "tier_tags": self.tier_tags,
            "tier_clusters": self.tier_clusters,
            "tier_scoring": self.tier_scoring,
        }


@dataclass
class PostSummary:
    """Condensed post information for reports."""

    id: str
    title: str
    score: int
    num_comments: int
    url: str
    category: CategoryEnum
    confidence: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "score": self.score,
            "num_comments": self.num_comments,
            "url": self.url,
            "category": self.category.value,
            "confidence": self.confidence,
        }


@dataclass
class AnalysisReport:
    """Analysis results for a subreddit scan."""

    subreddit: str
    period: str
    total_posts: int
    category_counts: Dict[CategoryEnum, int]
    signal_ratio: float
    red_flags_distribution: Dict[str, int]
    top_signal: List[PostSummary] = field(default_factory=list)
    top_noise: List[PostSummary] = field(default_factory=list)
    unrelated_count: int = 0  # Posts filtered as off-topic

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "subreddit": self.subreddit,
            "period": self.period,
            "total_posts": self.total_posts,
            "category_counts": {k.value: v for k, v in self.category_counts.items()},
            "signal_ratio": self.signal_ratio,
            "red_flags_distribution": self.red_flags_distribution,
            "top_signal": [post.to_dict() for post in self.top_signal],
            "top_noise": [post.to_dict() for post in self.top_noise],
            "unrelated_count": self.unrelated_count,
        }
