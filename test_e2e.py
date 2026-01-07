"""End-to-end test: scrape → classify → analyze → report."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.scraper import create_scraper
from claude_redditor.classifier import create_classifier
from claude_redditor.analyzer import create_analyzer
from claude_redditor.reporter import create_reporter
from claude_redditor.config import settings
from rich import print as rprint


def test_single_subreddit():
    """Test full pipeline with a single subreddit."""
    subreddit = "ClaudeAI"
    limit = 15

    rprint(f"\n[bold cyan]Testing Full Pipeline: r/{subreddit}[/bold cyan]\n")

    # Step 1: Scrape
    rprint(f"[yellow]1/4[/yellow] Scraping {limit} posts from r/{subreddit}...")
    scraper = create_scraper()
    posts = scraper.fetch_posts(subreddit, limit=limit, sort="hot")
    rprint(f"[green]✓[/green] Scraped {len(posts)} posts\n")

    # Step 2: Classify
    rprint(f"[yellow]2/4[/yellow] Classifying posts...")
    classifier = create_classifier()
    classifications = classifier.classify_posts(posts)
    rprint(f"[green]✓[/green] Classified {len(classifications)} posts\n")

    # Step 3: Analyze
    rprint(f"[yellow]3/4[/yellow] Analyzing results...")
    analyzer = create_analyzer()
    report = analyzer.analyze(
        posts=posts,
        classifications=classifications,
        subreddit=subreddit,
        period=f"recent {limit} hot posts",
    )
    rprint(f"[green]✓[/green] Analysis complete\n")

    # Step 4: Report
    rprint(f"[yellow]4/4[/yellow] Generating report...\n")
    reporter = create_reporter()
    reporter.render_terminal(report, show_details=True)

    # Export JSON
    json_path = reporter.export_json(report)
    rprint(f"\n[green]✓[/green] Report exported to: {json_path}")

    rprint(f"\n[bold green]✓ End-to-end test complete![/bold green]\n")


def test_multiple_subreddits():
    """Test with multiple subreddits and comparison."""
    subreddits = settings.get_subreddit_list()[:2]  # Test with first 2
    limit = 10

    rprint(f"\n[bold cyan]Testing Multiple Subreddits Comparison[/bold cyan]\n")

    reports = []

    for subreddit in subreddits:
        rprint(f"\n[cyan]Processing r/{subreddit}...[/cyan]")

        # Scrape
        scraper = create_scraper()
        posts = scraper.fetch_posts(subreddit, limit=limit, sort="hot")

        # Classify
        classifier = create_classifier()
        classifications = classifier.classify_posts(posts)

        # Filter to only posts that were successfully classified
        classified_post_ids = {c.post_id for c in classifications}
        filtered_posts = [p for p in posts if p.id in classified_post_ids]

        if len(filtered_posts) != len(posts):
            rprint(f"[yellow]⚠[/yellow] {len(posts) - len(filtered_posts)} posts failed classification")

        # Analyze
        analyzer = create_analyzer()
        report = analyzer.analyze(
            posts=filtered_posts,
            classifications=classifications,
            subreddit=subreddit,
            period=f"recent {limit} posts",
        )

        reports.append(report)
        rprint(f"[green]✓[/green] r/{subreddit} complete (Signal: {report.signal_ratio:.1%})\n")

    # Comparison report
    rprint("\n[bold]Comparison Report:[/bold]\n")
    reporter = create_reporter()
    reporter.render_comparison(reports)

    rprint(f"\n[bold green]✓ Multi-subreddit comparison complete![/bold green]\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        test_multiple_subreddits()
    else:
        test_single_subreddit()
