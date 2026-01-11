#%%
"""Test script for cli."""

import sys
sys.path.insert(0, 'src')

from claude_redditor.scrapers import create_hn_scraper
from claude_redditor.classifier import create_classifier
from claude_redditor.analyzer import create_analyzer, create_cached_engine
from claude_redditor.reporter import create_reporter
from claude_redditor.config import settings
from rich import print as rprint
from rich.console import Console
console = Console()
print("Testing scan_hn\n")
print("=" * 60)
#%%
limit = 10
sort = 'top'
keywords = None  # ['Claude', 'Anthropic', 'AI', 'LLM', 'language model']

#%%
if not keywords:
    keywords = settings.get_hn_keywords()
    rprint(f"[dim]Using default keywords: {', '.join(keywords)}[/dim]")

# %%
scraper = create_hn_scraper(keywords=keywords)
posts = scraper.fetch_posts(limit=limit, sort=sort)

if not posts:
    rprint(f"[yellow]⚠ No posts found matching keywords[/yellow]\n")
    raise SystemExit(0)

rprint(f"[green]✓[/green] Fetched {len(posts)} posts")

#%%
# Classify (with or without cache)
classifier = create_classifier()
cached_engine = create_cached_engine(settings)

# Convert posts to dicts for compatibility
posts_dicts = [p.to_dict() for p in posts]


rprint(f"[dim]Checking cache and classifying new posts...[/dim]")
classifications, cache_stats = cached_engine.analyze_with_cache(
    posts_dicts,
    classifier,
    source='hackernews'
)

# Show cache stats
from rich.table import Table
table = Table(title="💾 Cache Stats", show_header=False, box=None)
table.add_row("Total posts", str(cache_stats['total']))
table.add_row("Cached", f"[green]{cache_stats['cached']}[/green] ({cache_stats['cache_hit_rate']:.1%})")
table.add_row("New classified", f"[cyan]{cache_stats['new']}[/cyan]")
if cache_stats.get('api_cost_saved', 0) > 0:
    table.add_row("API cost saved", f"~${cache_stats['api_cost_saved']:.3f}")
console.print(table)
rprint()

classified_post_ids = {c.post_id for c in classifications}
filtered_posts = [p for p in posts if p.id in classified_post_ids]


#%%
# Analyze
analyzer = create_analyzer()
report = analyzer.analyze(
    posts=filtered_posts,
    classifications=classifications,
    subreddit="HackerNews",
    period=f"{limit} {sort} posts (keywords: {', '.join(keywords)})",
)

#%%