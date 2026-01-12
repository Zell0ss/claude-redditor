"""Analysis engine for calculating metrics from classified posts."""

from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime
import logging

from .core.models import RedditPost, Classification, AnalysisReport, PostSummary
from .core.enums import CategoryEnum

logger = logging.getLogger(__name__)


class PostAnalyzer:
    """Analyzes classified Reddit posts and generates metrics."""

    def analyze(
        self,
        posts: List[RedditPost],
        classifications: List[Classification],
        subreddit: str = "multiple",
        period: str = "recent",
    ) -> AnalysisReport:
        """
        Analyze posts and classifications to generate a comprehensive report.

        Args:
            posts: List of RedditPost objects
            classifications: List of Classification objects (must match posts)
            subreddit: Name of subreddit (or "multiple" for aggregated)
            period: Time period description (e.g., "week", "month", "recent")

        Returns:
            AnalysisReport with all metrics
        """
        if len(posts) != len(classifications):
            raise ValueError(
                f"Mismatch: {len(posts)} posts but {len(classifications)} classifications"
            )

        # Build lookup dictionary for easy access
        post_lookup = {post.id: post for post in posts}

        # Calculate category distribution
        category_counts = Counter(c.category for c in classifications)

        # Count UNRELATED posts separately
        unrelated_count = sum(1 for c in classifications if c.category == CategoryEnum.UNRELATED)

        # Calculate signal ratio (EXCLUDE UNRELATED from denominator)
        relevant_classifications = [
            c for c in classifications
            if c.category != CategoryEnum.UNRELATED
        ]
        signal_count = sum(
            1 for c in relevant_classifications if CategoryEnum.is_signal(c.category)
        )
        signal_ratio = signal_count / len(relevant_classifications) if relevant_classifications else 0.0

        # Calculate red flags distribution
        red_flags_counter = Counter()
        for classification in classifications:
            for flag in classification.red_flags:
                red_flags_counter[flag] += 1

        # Get top signal posts (highest confidence in signal categories)
        signal_posts = [
            (post_lookup[c.post_id], c)
            for c in classifications
            if CategoryEnum.is_signal(c.category)
        ]
        signal_posts.sort(key=lambda x: x[1].confidence, reverse=True)
        top_signal = [
            PostSummary(
                id=post.id,
                title=post.title,
                score=post.score,
                num_comments=post.num_comments,
                url=post.url,
                category=classification.category,
                confidence=classification.confidence,
            )
            for post, classification in signal_posts[:5]
        ]

        # Get top noise posts (highest confidence in noise categories)
        noise_posts = [
            (post_lookup[c.post_id], c)
            for c in classifications
            if c.category in CategoryEnum.noise_categories()
        ]
        noise_posts.sort(key=lambda x: x[1].confidence, reverse=True)
        top_noise = [
            PostSummary(
                id=post.id,
                title=post.title,
                score=post.score,
                num_comments=post.num_comments,
                url=post.url,
                category=classification.category,
                confidence=classification.confidence,
            )
            for post, classification in noise_posts[:5]
        ]

        # Create report
        return AnalysisReport(
            subreddit=subreddit,
            period=period,
            total_posts=len(posts),
            category_counts=dict(category_counts),
            signal_ratio=signal_ratio,
            red_flags_distribution=dict(red_flags_counter),
            top_signal=top_signal,
            top_noise=top_noise,
            unrelated_count=unrelated_count,
        )

    def compare_subreddits(
        self, reports: List[AnalysisReport]
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare metrics across multiple subreddit reports.

        Args:
            reports: List of AnalysisReport objects

        Returns:
            Dictionary with comparison metrics
        """
        comparison = {}

        for report in reports:
            comparison[report.subreddit] = {
                "signal_ratio": report.signal_ratio,
                "total_posts": report.total_posts,
                "red_flags_count": sum(report.red_flags_distribution.values()),
                "signal_count": sum(
                    count
                    for cat, count in report.category_counts.items()
                    if CategoryEnum.is_signal(CategoryEnum(cat))
                ),
                "noise_count": sum(
                    count
                    for cat, count in report.category_counts.items()
                    if CategoryEnum(cat) in CategoryEnum.noise_categories()
                ),
            }

        return comparison

    def get_summary_stats(self, report: AnalysisReport) -> Dict[str, any]:
        """
        Generate quick summary statistics from a report.

        Args:
            report: AnalysisReport object

        Returns:
            Dictionary with summary stats
        """
        signal_categories = CategoryEnum.signal_categories()
        noise_categories = CategoryEnum.noise_categories()

        signal_count = sum(
            count
            for cat, count in report.category_counts.items()
            if CategoryEnum(cat) in signal_categories
        )

        noise_count = sum(
            count
            for cat, count in report.category_counts.items()
            if CategoryEnum(cat) in noise_categories
        )

        meta_count = sum(
            count
            for cat, count in report.category_counts.items()
            if cat in [CategoryEnum.COMMUNITY.value, CategoryEnum.MEME.value]
        )

        return {
            "signal_count": signal_count,
            "noise_count": noise_count,
            "meta_count": meta_count,
            "signal_percentage": report.signal_ratio * 100,
            "health_grade": self._calculate_health_grade(report.signal_ratio),
            "top_red_flag": (
                max(report.red_flags_distribution.items(), key=lambda x: x[1])[0]
                if report.red_flags_distribution
                else None
            ),
            "most_common_category": (
                max(report.category_counts.items(), key=lambda x: x[1])[0]
                if report.category_counts
                else None
            ),
        }

    def _calculate_health_grade(self, signal_ratio: float) -> str:
        """
        Calculate health grade based on signal ratio.

        Args:
            signal_ratio: Ratio of signal posts (0.0-1.0)

        Returns:
            Grade string (A+, A, B, C, D, F)
        """
        if signal_ratio >= 0.8:
            return "A+"
        elif signal_ratio >= 0.7:
            return "A"
        elif signal_ratio >= 0.6:
            return "B"
        elif signal_ratio >= 0.5:
            return "C"
        elif signal_ratio >= 0.4:
            return "D"
        else:
            return "F"


class CachedAnalysisEngine:
    """
    Analysis engine WITH MariaDB cache support.
    Caches classifications to avoid re-processing posts.
    """

    def __init__(self, config):
        """
        Initialize cached analysis engine.

        Args:
            config: Settings object with MySQL configuration
        """
        self.config = config
        self.analyzer = PostAnalyzer()

        # Only initialize DB if MySQL is configured
        if config.is_mysql_configured():
            from .db.connection import DatabaseConnection
            from .db.repository import Repository

            self.db = DatabaseConnection(config)
            self.repo = Repository(self.db)
            self.cache_enabled = True
            logger.info("Cache enabled (MariaDB)")
        else:
            self.db = None
            self.repo = None
            self.cache_enabled = False
            logger.info("Cache disabled (no MySQL credentials)")

    def analyze_with_cache(
        self,
        posts: List[Dict],
        classifier,
        model_version: Optional[str] = None,
        source: str = 'reddit',
        project: str = 'default'
    ) -> Tuple[List[Classification], Dict]:
        """
        Analyze posts using cache (multi-source support).

        Flow:
        1. Check cache for post_ids
        2. Classify only posts not in cache
        3. Save new classifications
        4. Return all (cached + new)

        Args:
            posts: List of post dicts (from scraper, with prefixed IDs)
            classifier: PostClassifier instance
            model_version: Claude model version (default: from config)
            source: Content source ('reddit' or 'hackernews')
            project: Project name (default: 'default')

        Returns:
            (classifications, cache_stats)
        """
        if not posts:
            return [], {'total': 0, 'cached': 0, 'new': 0, 'cache_hit_rate': 0}

        model_version = model_version or self.config.anthropic_model

        # If cache disabled, classify everything
        if not self.cache_enabled:
            logger.info(f"Classifying {len(posts)} posts (cache disabled)")
            # Convert dicts to RedditPost objects
            posts_to_classify = [
                RedditPost(
                    id=p['id'],
                    title=p['title'],
                    selftext=p.get('selftext', ''),
                    author=p.get('author', '[deleted]'),
                    score=p.get('score', 0),
                    num_comments=p.get('num_comments', 0),
                    created_utc=p.get('created_utc', 0),
                    url=p.get('url', ''),
                    subreddit=p.get('subreddit', ''),
                    flair=p.get('flair')
                )
                for p in posts
            ]
            classifications = classifier.classify_posts(posts_to_classify, project=project)
            cache_stats = {
                'total': len(posts),
                'cached': 0,
                'new': len(classifications),
                'cache_hit_rate': 0.0,
                'api_cost_saved': 0.0
            }
            return classifications, cache_stats

        # Extract post IDs
        post_ids = [p['id'] for p in posts]
        logger.info(f"Analyzing {len(post_ids)} posts (cache enabled)")

        # Check cache
        cached_data = self.repo.get_cached_classifications(post_ids, source=source, project=project)
        cached_ids = {c['post_id'] for c in cached_data}

        # Convert cached data to Classification objects
        cached_classifications = []
        for data in cached_data:
            cached_classifications.append(
                Classification(
                    post_id=data['post_id'],
                    category=CategoryEnum(data['category']),
                    confidence=data['confidence'],
                    red_flags=data['red_flags'],
                    reasoning=data['reasoning']
                )
            )

        # Identify posts to classify
        to_classify = [p for p in posts if p['id'] not in cached_ids]

        # Classify new posts
        new_classifications = []
        if to_classify:
            logger.info(f"Classifying {len(to_classify)} new posts...")
            # Convert dicts to RedditPost objects
            posts_to_classify = [
                RedditPost(
                    id=p['id'],
                    title=p['title'],
                    selftext=p.get('selftext', ''),
                    author=p.get('author', '[deleted]'),
                    score=p.get('score', 0),
                    num_comments=p.get('num_comments', 0),
                    created_utc=p.get('created_utc', 0),
                    url=p.get('url', ''),
                    subreddit=p.get('subreddit', ''),
                    flair=p.get('flair')
                )
                for p in to_classify
            ]
            new_classifications = classifier.classify_posts(posts_to_classify, project=project)

            # Save to DB
            self.repo.save_posts(to_classify, source=source, project=project)

            # Convert to dicts for saving
            new_classifications_dicts = [
                {
                    'post_id': c.post_id,
                    'category': c.category.value,
                    'confidence': c.confidence,
                    'red_flags': c.red_flags,
                    'reasoning': c.reasoning
                }
                for c in new_classifications
            ]
            self.repo.save_classifications(new_classifications_dicts, source=source, model_version=model_version, project=project)
            logger.info(f"Saved {len(new_classifications)} new classifications")

        # Calculate stats
        cache_stats = {
            'total': len(posts),
            'cached': len(cached_classifications),
            'new': len(new_classifications),
            'cache_hit_rate': len(cached_classifications) / len(posts) if posts else 0,
            'api_cost_saved': len(cached_classifications) * 0.001  # ~$0.001 per classification
        }

        # Combine all classifications
        all_classifications = cached_classifications + new_classifications

        logger.info(
            f"Analysis complete: {cache_stats['cached']} cached, "
            f"{cache_stats['new']} new (hit rate: {cache_stats['cache_hit_rate']:.1%})"
        )

        return all_classifications, cache_stats

    def save_scan_result(
        self,
        subreddit: str,
        cache_stats: Dict,
        signal_ratio: float,
        source: str = 'reddit',
        project: str = 'default'
    ):
        """Save scan result to history."""
        if self.cache_enabled:
            self.repo.save_scan_history(
                subreddit=subreddit,
                posts_fetched=cache_stats['total'],
                posts_classified=cache_stats['new'],
                posts_cached=cache_stats['cached'],
                signal_ratio=signal_ratio * 100,  # Convert to percentage
                source=source,
                project=project
            )


def create_analyzer() -> PostAnalyzer:
    """Factory function to create a PostAnalyzer instance."""
    return PostAnalyzer()


def create_cached_engine(config) -> CachedAnalysisEngine:
    """Factory function to create a CachedAnalysisEngine instance."""
    return CachedAnalysisEngine(config)
