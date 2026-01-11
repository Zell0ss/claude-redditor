"""HackerNews scraper using Firebase API with keyword filtering."""

import time
import requests
from typing import List, Optional
from datetime import datetime

from .base import BaseScraper, Post, prefix_id


class HackerNewsScraper(BaseScraper):
    """
    Scraper for HackerNews using the official Firebase API.

    Features:
    - No authentication required
    - 500 stories/min rate limit (generous)
    - Keyword filtering for relevant posts
    - Supports: top, new, best stories
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, keywords: Optional[List[str]] = None):
        """
        Initialize HN scraper.

        Args:
            keywords: List of keywords to filter stories (case-insensitive)
                     If None, fetches all stories without filtering
        """
        self.keywords = [k.lower() for k in keywords] if keywords else []
        self.last_request_time = 0
        self.rate_limit = 500  # requests per minute
        print(f"✓ HackerNews scraper: Firebase API ({self.rate_limit} req/min)")
        if self.keywords:
            print(f"  Filtering by keywords: {', '.join(self.keywords)}")

    def get_source_name(self) -> str:
        """Return source identifier."""
        return "hackernews"

    def _rate_limit(self):
        """Simple rate limiting: 0.12s between requests (500/min)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        self.last_request_time = time.time()

    def _get(self, endpoint: str) -> dict:
        """
        Make GET request to HN API with rate limiting.

        Args:
            endpoint: API endpoint (e.g., "item/8863.json")

        Returns:
            JSON response as dict

        Raises:
            requests.exceptions.RequestException: On network errors
        """
        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def fetch_posts(
        self,
        limit: int = 100,
        sort: str = "top",
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts from HackerNews.

        Args:
            limit: Maximum number of posts to fetch (default 100, max 500)
            sort: Sort method - "top", "new", or "best"

        Returns:
            List of Post objects with prefixed IDs ("hn_8863")
            Filtered by keywords if provided during initialization
        """
        # Validate limit
        if limit > 500:
            print(f"⚠ Limiting to 500 posts (API maximum), requested {limit}")
            limit = 500

        # Get story IDs based on sort method
        if sort == "top":
            endpoint = "topstories.json"
        elif sort == "new":
            endpoint = "newstories.json"
        elif sort == "best":
            endpoint = "beststories.json"
        else:
            print(f"⚠ Unknown sort '{sort}', using 'top'")
            endpoint = "topstories.json"

        try:
            story_ids = self._get(endpoint)
            print(f"Found {len(story_ids)} {sort} stories on HN")

            # Fetch posts
            if self.keywords:
                posts = self.search_by_keywords(story_ids, limit)
            else:
                posts = self._fetch_stories(story_ids[:limit])

            return posts

        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching HN stories: {e}")
            return []

    def _fetch_stories(self, story_ids: List[int]) -> List[Post]:
        """
        Fetch multiple stories by ID.

        Args:
            story_ids: List of HN story IDs

        Returns:
            List of Post objects (skips deleted/failed stories)
        """
        posts = []
        for story_id in story_ids:
            try:
                story_data = self._get(f"item/{story_id}.json")
                if story_data and story_data.get("type") == "story":
                    post = self._parse_story(story_data)
                    if post:
                        posts.append(post)
            except Exception as e:
                print(f"  ⚠ Skipping story {story_id}: {e}")
                continue

        return posts

    def _parse_story(self, story: dict) -> Optional[Post]:
        """
        Parse HN story JSON to Post object.

        Args:
            story: Story data from HN API

        Returns:
            Post object with prefixed ID, or None if invalid
        """
        if not story or story.get("deleted") or story.get("dead"):
            return None

        # Extract fields
        raw_id = str(story.get("id", "unknown"))
        prefixed_id = prefix_id(raw_id, "hackernews")

        title = story.get("title", "[No title]")
        url = story.get("url", f"https://news.ycombinator.com/item?id={raw_id}")
        author = story.get("by", "[deleted]")
        score = story.get("score", 0)
        num_comments = story.get("descendants", 0)  # Total comment count
        created_utc = float(story.get("time", 0))  # Already unix timestamp

        # Text content (HN "Ask HN", "Show HN", etc may have text)
        selftext = story.get("text", "")
        # Remove HTML tags (basic approach)
        if selftext:
            import re
            selftext = re.sub(r"<[^>]+>", "", selftext)

        # External URL (for link posts)
        source_url = story.get("url", "")

        return Post(
            id=prefixed_id,
            source="hackernews",
            title=title,
            url=f"https://news.ycombinator.com/item?id={raw_id}",  # HN discussion URL
            author=author,
            score=score,
            num_comments=num_comments,
            created_utc=created_utc,
            selftext=selftext,
            source_url=source_url,  # Original URL if link post
            subreddit=None,
            flair=None,
            hn_type=story.get("type"),
        )

    def _matches_keywords(self, story: dict) -> bool:
        """
        Check if story matches any of the configured keywords.

        Args:
            story: Story data from HN API

        Returns:
            True if title or text contains any keyword (case-insensitive)
        """
        if not self.keywords:
            return True  # No filtering

        title = story.get("title", "").lower()
        text = story.get("text", "").lower()
        combined = f"{title} {text}"

        return any(keyword in combined for keyword in self.keywords)

    def search_by_keywords(self, story_ids: List[int], limit: int) -> List[Post]:
        """
        Search stories by keywords, stopping when limit is reached.

        Args:
            story_ids: List of story IDs to search through
            limit: Maximum number of matching posts to return

        Returns:
            List of Post objects matching keywords (up to limit)
        """
        matching_posts = []
        checked = 0
        max_check = min(len(story_ids), limit * 10)  # Check up to 10x limit

        print(f"Searching for keywords: {', '.join(self.keywords)}")
        print(f"Will check up to {max_check} stories...")

        for story_id in story_ids[:max_check]:
            checked += 1

            try:
                story_data = self._get(f"item/{story_id}.json")

                if not story_data or story_data.get("type") != "story":
                    continue

                if story_data.get("deleted") or story_data.get("dead"):
                    continue

                # Check if matches keywords
                if self._matches_keywords(story_data):
                    post = self._parse_story(story_data)
                    if post:
                        matching_posts.append(post)
                        print(f"  ✓ Match {len(matching_posts)}: {post.title[:60]}...")

                        if len(matching_posts) >= limit:
                            break

            except Exception as e:
                print(f"  ⚠ Error checking story {story_id}: {e}")
                continue

        print(f"✓ Found {len(matching_posts)} matching posts (checked {checked} stories)")
        return matching_posts
