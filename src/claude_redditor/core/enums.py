"""Enumerations and constants for post classification."""

from enum import Enum
from typing import List


class CategoryEnum(str, Enum):
    """Post classification categories."""

    # SIGNAL (useful content)
    TECHNICAL = "technical"                  # Prompts, workflows, functional code
    TROUBLESHOOTING = "troubleshooting"      # Real problems + solutions
    RESEARCH_VERIFIED = "research_verified"  # Papers/experiments with verifiable sources

    # NOISE (problematic content)
    MYSTICAL = "mystical"                    # Consciousness claims without evidence
    UNVERIFIED_CLAIM = "unverified_claim"    # Technical assertions without sources
    ENGAGEMENT_BAIT = "engagement_bait"      # Clickbait content

    # META
    COMMUNITY = "community"                   # Subreddit discussion
    MEME = "meme"                            # Humor/entertainment

    # OTHER
    OUTLIER = "outlier"                      # Doesn't fit clearly

    # UNRELATED (off-topic content)
    UNRELATED = "unrelated"                   # Content outside the configured topic scope

    @classmethod
    def signal_categories(cls) -> List["CategoryEnum"]:
        """Return list of categories considered 'signal' (useful content)."""
        return [cls.TECHNICAL, cls.TROUBLESHOOTING, cls.RESEARCH_VERIFIED]

    @classmethod
    def noise_categories(cls) -> List["CategoryEnum"]:
        """Return list of categories considered 'noise' (problematic content)."""
        return [cls.MYSTICAL, cls.UNVERIFIED_CLAIM, cls.ENGAGEMENT_BAIT]

    @classmethod
    def is_signal(cls, category: "CategoryEnum") -> bool:
        """Check if a category is signal."""
        return category in cls.signal_categories()


# Red flag detection patterns
RED_FLAG_PATTERNS = {
    "no_source": [
        "researchers say",
        "studies show",
        "experiments found",
        "scientists discovered",
        "research indicates",
    ],
    "link_in_bio": [
        "link in bio",
        "check my profile",
        "see my research",
        "visit my page",
    ],
    "mystical_language": [
        "consciousness emerged",
        "spiritual",
        "transcendent",
        "awakening",
        "sentient",
        "enlightenment",
        "divine",
    ],
    "cannot_explain": [
        "can't explain",
        "cannot explain",
        "researchers puzzled",
        "mysterious",
        "unexplainable",
        "defies explanation",
    ],
    "sensationalist": [
        "you won't believe",
        "shocking",
        "mind-blowing",
        "incredible discovery",
        "unbelievable",
        "this will shock you",
    ],
}


# Regex pattern for precise numbers without sources
# Matches patterns like "95.7 times", "2,725 emojis", "14.3% more"
PRECISE_NUMBER_PATTERN = r'\b\d+[.,]\d+\s+(times|%|percent|emojis|tokens|words|increase|decrease|more|less)\b'
