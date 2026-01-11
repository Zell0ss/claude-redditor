"""Multi-source scraper package (Reddit, HackerNews, etc)."""

from typing import Optional, List

from .base import Post, BaseScraper, prefix_id
from .reddit import RedditScraper
from .hackernews import HackerNewsScraper

__all__ = [
    "Post",
    "BaseScraper",
    "prefix_id",
    "RedditScraper",
    "HackerNewsScraper",
    "create_reddit_scraper",
    "create_hn_scraper",
    "ScraperManager",
]


def create_reddit_scraper() -> RedditScraper:
    """Factory function to create a RedditScraper instance."""
    return RedditScraper()


def create_hn_scraper(keywords: Optional[List[str]] = None) -> HackerNewsScraper:
    """
    Factory function to create a HackerNewsScraper instance.

    Args:
        keywords: List of keywords to filter HN posts

    Returns:
        HackerNewsScraper instance
    """
    return HackerNewsScraper(keywords=keywords)


class ScraperManager:
    """
    Manager for handling multiple scrapers across different sources.

    Useful for unified operations like:
    - Fetching from multiple sources
    - Cross-source comparison
    - Aggregated analysis
    """

    def __init__(self):
        """Initialize scraper manager."""
        self.scrapers = {
            "reddit": None,
            "hackernews": None,
        }

    def get_reddit_scraper(self) -> RedditScraper:
        """Get or create Reddit scraper."""
        if not self.scrapers["reddit"]:
            self.scrapers["reddit"] = create_reddit_scraper()
        return self.scrapers["reddit"]

    def get_hn_scraper(self, keywords: Optional[List[str]] = None) -> HackerNewsScraper:
        """Get or create HackerNews scraper."""
        # Always create new instance if keywords change
        self.scrapers["hackernews"] = create_hn_scraper(keywords)
        return self.scrapers["hackernews"]

    def fetch_all_sources(
        self,
        reddit_subreddits: List[str] = None,
        hn_keywords: List[str] = None,
        limit: int = 50
    ) -> dict:
        """
        Fetch posts from all sources.

        Args:
            reddit_subreddits: List of subreddits to fetch
            hn_keywords: Keywords for HN filtering
            limit: Posts per source

        Returns:
            Dict with keys "reddit" and "hackernews" containing lists of Posts
        """
        results = {
            "reddit": [],
            "hackernews": []
        }

        # Fetch from Reddit
        if reddit_subreddits:
            reddit_scraper = self.get_reddit_scraper()
            for subreddit in reddit_subreddits:
                try:
                    posts = reddit_scraper.fetch_posts(subreddit, limit=limit)
                    results["reddit"].extend(posts)
                except Exception as e:
                    print(f"⚠ Error fetching r/{subreddit}: {e}")

        # Fetch from HN
        if hn_keywords:
            hn_scraper = self.get_hn_scraper(hn_keywords)
            try:
                posts = hn_scraper.fetch_posts(limit=limit)
                results["hackernews"] = posts
            except Exception as e:
                print(f"⚠ Error fetching HN: {e}")

        return results
