"""Test analyzer with real data from r/ClaudeAI."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.scraper import create_scraper
from claude_redditor.classifier import create_classifier
from claude_redditor.analyzer import create_analyzer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_analyzer():
    """Test full pipeline: scrape → classify → analyze."""

    # Step 1: Scrape posts
    rprint("[cyan]Step 1:[/cyan] Scraping 10 posts from r/ClaudeAI...")
    scraper = create_scraper()
    posts = scraper.fetch_posts("ClaudeAI", limit=10, sort="hot")
    rprint(f"[green]✓ Scraped {len(posts)} posts[/green]\n")

    # Step 2: Classify posts
    rprint("[cyan]Step 2:[/cyan] Classifying posts with Claude...")
    classifier = create_classifier()
    classifications = classifier.classify_posts(posts)
    rprint(f"[green]✓ Classified {len(classifications)} posts[/green]\n")

    # Step 3: Analyze results
    rprint("[cyan]Step 3:[/cyan] Analyzing results...")
    analyzer = create_analyzer()
    report = analyzer.analyze(
        posts=posts,
        classifications=classifications,
        subreddit="ClaudeAI",
        period="recent hot posts",
    )
    rprint(f"[green]✓ Analysis complete[/green]\n")

    # Display results
    console.print(Panel(
        f"""[bold]Subreddit:[/bold] r/{report.subreddit}
[bold]Period:[/bold] {report.period}
[bold]Total Posts:[/bold] {report.total_posts}
[bold]Signal Ratio:[/bold] {report.signal_ratio:.1%}""",
        title="Analysis Report Summary",
        border_style="blue"
    ))

    # Category distribution
    rprint("\n[cyan]Category Distribution:[/cyan]")
    cat_table = Table(show_header=True)
    cat_table.add_column("Category", style="yellow")
    cat_table.add_column("Count", justify="right", style="cyan")
    cat_table.add_column("Percentage", justify="right", style="green")

    for category, count in sorted(report.category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / report.total_posts) * 100
        cat_table.add_row(category, str(count), f"{percentage:.1f}%")

    console.print(cat_table)

    # Red flags
    if report.red_flags_distribution:
        rprint("\n[cyan]Red Flags Detected:[/cyan]")
        flags_table = Table(show_header=True)
        flags_table.add_column("Red Flag", style="red")
        flags_table.add_column("Count", justify="right", style="yellow")

        for flag, count in sorted(report.red_flags_distribution.items(), key=lambda x: x[1], reverse=True):
            flags_table.add_row(flag, str(count))

        console.print(flags_table)
    else:
        rprint("\n[green]✓ No red flags detected![/green]")

    # Summary stats
    rprint("\n[cyan]Summary Statistics:[/cyan]")
    stats = analyzer.get_summary_stats(report)

    stats_text = f"""[bold]Signal Posts:[/bold] {stats['signal_count']} ({stats['signal_percentage']:.1f}%)
[bold]Noise Posts:[/bold] {stats['noise_count']}
[bold]Meta Posts:[/bold] {stats['meta_count']}
[bold]Health Grade:[/bold] {stats['health_grade']}
[bold]Most Common Category:[/bold] {stats['most_common_category']}
[bold]Top Red Flag:[/bold] {stats['top_red_flag'] or 'None'}"""

    # Color based on health grade
    if stats['health_grade'] in ['A+', 'A']:
        border_color = "green"
    elif stats['health_grade'] in ['B', 'C']:
        border_color = "yellow"
    else:
        border_color = "red"

    console.print(Panel(stats_text, title="Statistics", border_style=border_color))

    # Top signal posts
    if report.top_signal:
        rprint("\n[green]Top Signal Posts:[/green]")
        for i, post in enumerate(report.top_signal[:3], 1):
            rprint(f"{i}. [{post.category.value}] {post.title[:60]}... ({post.confidence:.0%})")

    # Top noise posts
    if report.top_noise:
        rprint("\n[red]Top Noise Posts:[/red]")
        for i, post in enumerate(report.top_noise[:3], 1):
            rprint(f"{i}. [{post.category.value}] {post.title[:60]}... ({post.confidence:.0%})")

    rprint("\n[green]✓ Analyzer test complete![/green]")


if __name__ == "__main__":
    test_analyzer()
