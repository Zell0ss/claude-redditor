#!/usr/bin/env python3
"""
Debug script for testing scan functionality.
Equivalent to: ./reddit-analyzer scan ClaudeAI --limit 5 --project claudeia --no-cache
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.config import settings
from claude_redditor.scrapers.reddit import RedditScraper
from claude_redditor.classifier import create_classifier
from claude_redditor.analyzer import create_cached_engine
from claude_redditor.projects import project_loader


def main():
    """Debug scan ClaudeAI subreddit with tier tagging."""

    # Configuration
    subreddit = "ClaudeAI"
    limit = 5
    project_name = "claudeia"
    no_cache = True  # Force re-classification

    print(f"\n[DEBUG] Starting scan of r/{subreddit}")
    print(f"[DEBUG] Limit: {limit}, Project: {project_name}, No-cache: {no_cache}\n")

    # Load project configuration
    project = project_loader.load(project_name)
    print(f"[DEBUG] Project loaded: {project.name}")
    print(f"[DEBUG] Topic: {project.topic}\n")

    # Initialize scraper
    scraper = RedditScraper()
    print(f"[DEBUG] Reddit scraper initialized")
    print(f"[DEBUG] Mode: {scraper.mode}\n")

    # Fetch posts
    print(f"[DEBUG] Fetching posts from r/{subreddit}...")
    posts = scraper.fetch_posts(subreddit, limit=limit)
    print(f"[DEBUG] Fetched {len(posts)} posts\n")

    if not posts:
        print("[DEBUG] No posts found!")
        return

    # Show fetched posts
    for i, post in enumerate(posts, 1):
        print(f"  {i}. {post.title[:60]}... (score: {post.score})")
    print()

    # Initialize classifier and analyzer
    classifier = create_classifier()
    engine = create_cached_engine(settings)

    print(f"[DEBUG] Classifier initialized with model: {classifier.model}")
    print(f"[DEBUG] Cache enabled: {engine.cache_enabled}\n")

    # Classify posts (with or without cache)
    if no_cache or not engine.cache_enabled:
        print("[DEBUG] Forcing re-classification (cache disabled)")
        from claude_redditor.core.models import RedditPost

        # Convert Post objects to RedditPost objects
        posts_to_classify = [
            RedditPost(
                id=p.id,
                title=p.title,
                selftext=p.selftext,
                author=p.author,
                score=p.score,
                num_comments=p.num_comments,
                created_utc=p.created_utc,
                url=p.url,
                subreddit=p.subreddit or '',
                flair=p.flair
            )
            for p in posts
        ]

        print(f"[DEBUG] Classifying {len(posts_to_classify)} posts with project '{project_name}'...\n")
        classifications = classifier.classify_posts(posts_to_classify, project=project_name)

        cache_stats = {
            'total': len(posts),
            'cached': 0,
            'new': len(classifications),
            'cache_hit_rate': 0.0,
        }
    else:
        print("[DEBUG] Using cache if available")
        # Convert Post objects to dicts for analyze_with_cache
        posts_dicts = [p.to_dict() for p in posts]
        classifications, cache_stats = engine.analyze_with_cache(
            posts_dicts,
            classifier,
            source='reddit',
            project=project_name
        )

    print(f"\n[DEBUG] Classification complete!")
    print(f"[DEBUG] Cache stats: {cache_stats['new']} new, {cache_stats['cached']} cached")
    print(f"[DEBUG] Hit rate: {cache_stats['cache_hit_rate']:.1%}\n")

    # Show results
    print("=" * 80)
    print("CLASSIFICATION RESULTS")
    print("=" * 80)

    for i, cls in enumerate(classifications, 1):
        print(f"\n{i}. Post: {cls.post_id}")
        print(f"   Category: {cls.category.value}")
        print(f"   Confidence: {cls.confidence:.2f}")
        print(f"   Topic tags: {', '.join(cls.topic_tags) if cls.topic_tags else 'None'}")
        print(f"   Format tag: {cls.format_tag or 'None'}")

        # Tier data
        if cls.tier_tags:
            print(f"   Tier scoring: {cls.tier_scoring}")
            print(f"   Tier clusters: {len(cls.tier_clusters)} clusters")
            tier_count = sum(len(tags) for tags in cls.tier_tags.values() if tags)
            print(f"   Tier tags: {tier_count} tags across {len([t for t in cls.tier_tags.values() if t])} tiers")

            # Show tier1 and tier2 as preview
            if cls.tier_tags.get('tier1'):
                print(f"     - Tier 1: {', '.join(cls.tier_tags['tier1'][:3])}")
            if cls.tier_tags.get('tier2'):
                print(f"     - Tier 2: {', '.join(cls.tier_tags['tier2'][:3])}")
            if cls.tier_tags.get('tier3'):
                print(f"     - Tier 3: {', '.join(cls.tier_tags['tier3'][:3])}")
            if cls.tier_tags.get('tier4'):
                print(f"     - Tier 4: {', '.join(cls.tier_tags['tier4'][:3])}")
        else:
            print(f"   Tier tags: None (UNRELATED or not classified)")

        print(f"   Red flags: {', '.join(cls.red_flags) if cls.red_flags else 'None'}")
        print(f"   Reasoning: {cls.reasoning[:100]}...")

    print("\n" + "=" * 80)
    print(f"[DEBUG] Done! Classified {len(classifications)} posts")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
