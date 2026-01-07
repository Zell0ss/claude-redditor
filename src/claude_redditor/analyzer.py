"""Analysis engine for calculating metrics from classified posts."""

from typing import List, Dict
from collections import Counter
from datetime import datetime

from .core.models import RedditPost, Classification, AnalysisReport, PostSummary
from .core.enums import CategoryEnum


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

        # Calculate signal ratio
        signal_count = sum(
            1 for c in classifications if CategoryEnum.is_signal(c.category)
        )
        signal_ratio = signal_count / len(classifications) if classifications else 0.0

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
            if cat in ["community", "meme"]
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


def create_analyzer() -> PostAnalyzer:
    """Factory function to create a PostAnalyzer instance."""
    return PostAnalyzer()
