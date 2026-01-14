"""Fetch full content for truncated posts."""

import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def fetch_full_content(url: str, max_chars: int = 15000) -> Optional[str]:
    """
    Fetch full content from URL when selftext was truncated.

    Handles:
    - Reddit posts (via .json endpoint)
    - HackerNews links (external articles)
    - External article URLs

    Args:
        url: URL to fetch content from
        max_chars: Maximum characters to return

    Returns:
        Cleaned text content, or None if fetch fails
    """
    if not url:
        return None

    try:
        # For Reddit posts, use JSON endpoint
        if 'reddit.com' in url:
            return _fetch_reddit_content(url, max_chars)

        # For HackerNews item pages, use their API
        if 'news.ycombinator.com' in url:
            # HN item pages don't have much content, skip
            return None

        # For external URLs, fetch and extract text
        return _fetch_external_content(url, max_chars)

    except Exception as e:
        logger.warning(f"Failed to fetch content from {url}: {e}")
        return None


def _fetch_reddit_content(url: str, max_chars: int) -> Optional[str]:
    """Fetch full selftext from Reddit JSON endpoint."""
    try:
        # Convert URL to JSON endpoint
        json_url = url.rstrip('/') + '.json'

        response = requests.get(
            json_url,
            headers={'User-Agent': 'reddit-analyzer/1.0'},
            timeout=10
        )

        if response.ok:
            data = response.json()

            # Reddit JSON structure: [listing, comments]
            # listing.data.children[0].data.selftext
            if isinstance(data, list) and len(data) > 0:
                post_data = data[0].get('data', {}).get('children', [{}])[0].get('data', {})
                selftext = post_data.get('selftext', '')

                if selftext:
                    logger.info(f"Fetched full Reddit content: {len(selftext)} chars")
                    return selftext[:max_chars]

        return None

    except Exception as e:
        logger.warning(f"Failed to fetch Reddit content: {e}")
        return None


def _fetch_external_content(url: str, max_chars: int) -> Optional[str]:
    """Fetch and extract text from external article URLs."""
    try:
        # Try to import BeautifulSoup (optional dependency)
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
            return None

        response = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout=15
        )

        if not response.ok:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            element.decompose()

        # Try to find main content area
        content = None

        # Look for article or main tags first
        for tag in ['article', 'main', '[role="main"]', '.post-content', '.article-content']:
            content = soup.select_one(tag)
            if content:
                break

        # Fallback to body
        if not content:
            content = soup.body

        if content:
            # Extract text with newline separators
            text = content.get_text(separator='\n', strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)

            if text:
                logger.info(f"Fetched external content: {len(text)} chars from {url}")
                return text[:max_chars]

        return None

    except Exception as e:
        logger.warning(f"Failed to fetch external content from {url}: {e}")
        return None
