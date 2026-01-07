"""CLI interface for Reddit Signal/Noise Analyzer."""

import typer
from typing import Optional
from pathlib import Path
from rich import print as rprint
from rich.console import Console

from .scraper import create_scraper
from .classifier import create_classifier
from .analyzer import create_analyzer
from .reporter import create_reporter
from .config import settings

app = typer.Typer(
    name="reddit-analyzer",
    help="Analyze Reddit posts and classify them as signal vs noise using Claude AI",
    add_completion=False,
)
console = Console()


@app.command()
def scan(
    subreddit: str = typer.Argument(
        ...,
        help="Subreddit name (without 'r/' prefix). Use 'all' for all configured subreddits."
    ),
    limit: int = typer.Option(
        50,
        "--limit", "-l",
        help="Number of posts to analyze"
    ),
    sort: str = typer.Option(
        "hot",
        "--sort", "-s",
        help="Sort method: hot, new, top, rising"
    ),
    time_filter: str = typer.Option(
        "week",
        "--time-filter", "-t",
        help="Time filter for 'top' sort: hour, day, week, month, year, all"
    ),
    export_json: bool = typer.Option(
        False,
        "--export-json",
        help="Export report to JSON file"
    ),
    no_details: bool = typer.Option(
        False,
        "--no-details",
        help="Show summary only, hide detailed tables"
    ),
):
    """
    Scan and analyze posts from a subreddit.

    Examples:

        reddit-analyzer scan ClaudeAI

        reddit-analyzer scan ClaudeAI --limit 100 --sort top --time-filter month

        reddit-analyzer scan all --limit 20 --export-json
    """
    # Determine which subreddits to analyze
    if subreddit.lower() == "all":
        subreddits = settings.get_subreddit_list()
        rprint(f"\n[cyan]Analyzing all configured subreddits:[/cyan] {', '.join(f'r/{s}' for s in subreddits)}\n")
    else:
        subreddits = [subreddit]

    # Analyze each subreddit
    reports = []

    for sub in subreddits:
        rprint(f"[bold cyan]Analyzing r/{sub}[/bold cyan]")
        rprint(f"[dim]Fetching {limit} {sort} posts...[/dim]\n")

        try:
            # Scrape
            scraper = create_scraper()
            posts = scraper.fetch_posts(sub, limit=limit, sort=sort, time_filter=time_filter)

            if not posts:
                rprint(f"[yellow]⚠ No posts found for r/{sub}[/yellow]\n")
                continue

            rprint(f"[green]✓[/green] Fetched {len(posts)} posts")

            # Classify
            rprint(f"[dim]Classifying with Claude...[/dim]")
            classifier = create_classifier()
            classifications = classifier.classify_posts(posts)

            # Filter successfully classified posts
            classified_post_ids = {c.post_id for c in classifications}
            filtered_posts = [p for p in posts if p.id in classified_post_ids]

            if len(filtered_posts) != len(posts):
                rprint(f"[yellow]⚠ {len(posts) - len(filtered_posts)} posts failed classification[/yellow]")

            # Analyze
            analyzer = create_analyzer()
            report = analyzer.analyze(
                posts=filtered_posts,
                classifications=classifications,
                subreddit=sub,
                period=f"{limit} {sort} posts ({time_filter if sort == 'top' else 'recent'})",
            )

            reports.append(report)

            # Report
            reporter = create_reporter()
            rprint()  # Blank line before report
            reporter.render_terminal(report, show_details=not no_details)

            # Export JSON if requested
            if export_json:
                json_path = reporter.export_json(report)
                rprint(f"[green]✓[/green] Report exported to: {json_path}\n")

        except Exception as e:
            rprint(f"[red]✗ Error analyzing r/{sub}: {e}[/red]\n")
            if typer.confirm("Continue with next subreddit?", default=True):
                continue
            else:
                raise typer.Exit(1)

    # Show comparison if multiple subreddits
    if len(reports) > 1:
        rprint("\n[bold cyan]Subreddit Comparison[/bold cyan]\n")
        reporter = create_reporter()
        reporter.render_comparison(reports)

    rprint(f"\n[bold green]✓ Analysis complete![/bold green]\n")


@app.command()
def compare(
    limit: int = typer.Option(
        20,
        "--limit", "-l",
        help="Number of posts to analyze per subreddit"
    ),
    sort: str = typer.Option(
        "hot",
        "--sort", "-s",
        help="Sort method: hot, new, top, rising"
    ),
    export_json: bool = typer.Option(
        False,
        "--export-json",
        help="Export reports to JSON files"
    ),
):
    """
    Compare signal/noise ratio across all configured subreddits.

    This command analyzes all subreddits defined in the SUBREDDITS
    environment variable and shows a comparison table.

    Example:

        reddit-analyzer compare --limit 30
    """
    subreddits = settings.get_subreddit_list()

    rprint(f"\n[bold cyan]Comparing {len(subreddits)} subreddits[/bold cyan]")
    rprint(f"[dim]Analyzing {limit} {sort} posts from each...[/dim]\n")

    reports = []

    for sub in subreddits:
        rprint(f"[cyan]Processing r/{sub}...[/cyan]")

        try:
            # Scrape
            scraper = create_scraper()
            posts = scraper.fetch_posts(sub, limit=limit, sort=sort)

            if not posts:
                rprint(f"[yellow]⚠ No posts found, skipping[/yellow]\n")
                continue

            # Classify
            classifier = create_classifier()
            classifications = classifier.classify_posts(posts)

            # Filter
            classified_post_ids = {c.post_id for c in classifications}
            filtered_posts = [p for p in posts if p.id in classified_post_ids]

            # Analyze
            analyzer = create_analyzer()
            report = analyzer.analyze(
                posts=filtered_posts,
                classifications=classifications,
                subreddit=sub,
                period=f"{limit} {sort} posts",
            )

            reports.append(report)
            rprint(f"[green]✓[/green] r/{sub} complete (Signal: {report.signal_ratio:.1%})\n")

            # Export if requested
            if export_json:
                reporter = create_reporter()
                json_path = reporter.export_json(report)
                rprint(f"[dim]Exported to: {json_path}[/dim]\n")

        except Exception as e:
            rprint(f"[red]✗ Error: {e}[/red]\n")
            continue

    # Show comparison
    if reports:
        rprint()
        reporter = create_reporter()
        reporter.render_comparison(reports)
        rprint(f"\n[bold green]✓ Comparison complete![/bold green]\n")
    else:
        rprint("[red]✗ No reports generated[/red]")
        raise typer.Exit(1)


@app.command()
def config():
    """
    Show current configuration.
    """
    rprint("\n[bold cyan]Current Configuration[/bold cyan]\n")

    # Reddit
    rprint("[bold]Reddit API:[/bold]")
    if settings.is_reddit_authenticated():
        rprint(f"  Mode: [green]PRAW (authenticated)[/green]")
        rprint(f"  Rate Limit: 60 req/min")
    else:
        rprint(f"  Mode: [yellow]RSS (unauthenticated)[/yellow]")
        rprint(f"  Rate Limit: 10 req/min")
    rprint(f"  User Agent: {settings.reddit_user_agent}")

    # Anthropic
    rprint(f"\n[bold]Anthropic API:[/bold]")
    if settings.anthropic_api_key:
        rprint(f"  Status: [green]Configured[/green]")
        rprint(f"  Model: {settings.anthropic_model}")
    else:
        rprint(f"  Status: [red]Not configured[/red]")
        rprint(f"  [yellow]Set ANTHROPIC_API_KEY in .env file[/yellow]")

    # Subreddits
    rprint(f"\n[bold]Target Subreddits:[/bold]")
    for sub in settings.get_subreddit_list():
        rprint(f"  • r/{sub}")

    # Behavior
    rprint(f"\n[bold]Behavior:[/bold]")
    rprint(f"  Batch Size: {settings.default_batch_size} posts")
    rprint(f"  Cache TTL: {settings.cache_ttl_hours} hours")

    # Paths
    rprint(f"\n[bold]Output Paths:[/bold]")
    rprint(f"  Reports: {settings.reports_dir}")
    rprint(f"  Cache: {settings.cache_dir}")
    rprint(f"  Classifications: {settings.classifications_dir}")

    rprint()


@app.command()
def version():
    """Show version information."""
    rprint("\n[bold cyan]Reddit Signal/Noise Analyzer[/bold cyan]")
    rprint("Version: 0.1.0")
    rprint("Powered by Claude AI (Anthropic)")
    rprint("\nGitHub: https://github.com/Zell0ss/claude-redditor\n")


if __name__ == "__main__":
    app()
