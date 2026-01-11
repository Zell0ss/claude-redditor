"""Test script for HackerNews scraper."""

import sys
sys.path.insert(0, 'src')

from claude_redditor.scrapers import create_hn_scraper

print("Testing HackerNews Scraper\n")
print("=" * 60)

# Test 1: Fetch with keywords
print("\n[TEST 1] Fetching 5 posts with keywords ['claude', 'anthropic']")
print("-" * 60)

scraper = create_hn_scraper(keywords=['claude', 'anthropic'])
posts = scraper.fetch_posts(limit=5, sort='top')

print(f"\n✓ Fetched {len(posts)} posts:\n")
for i, post in enumerate(posts, 1):
    print(f"{i}. [{post.id}] {post.title}")
    print(f"   Score: {post.score}, Comments: {post.num_comments}")
    print(f"   URL: {post.url}")
    print(f"   Source URL: {post.source_url}")
    print()

# Test 2: Verify IDs are prefixed
print("\n[TEST 2] Verifying IDs are prefixed with 'hn_'")
print("-" * 60)
for post in posts:
    if post.id.startswith('hn_'):
        print(f"✓ {post.id} - correctly prefixed")
    else:
        print(f"✗ {post.id} - MISSING PREFIX!")

# Test 3: Verify source field
print("\n[TEST 3] Verifying source field is 'hackernews'")
print("-" * 60)
for post in posts:
    if post.source == 'hackernews':
        print(f"✓ {post.id} - source = 'hackernews'")
    else:
        print(f"✗ {post.id} - source = '{post.source}' (expected 'hackernews')")

print("\n" + "=" * 60)
print("✅ HackerNews scraper tests complete!")
