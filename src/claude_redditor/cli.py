"""CLI interface for Reddit Signal/Noise Analyzer."""

import typer
from typing import Optional
from pathlib import Path
from rich import print as rprint
from rich.console import Console

from .scraper import create_scraper
from .classifier import create_classifier
from .analyzer import create_analyzer, create_cached_engine
from .reporter import create_reporter
from .config import settings
from rich.table import Table
from rich.panel import Panel

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
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Bypass database cache (classify all posts)"
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
        if not subreddits:
            rprint("[red]✗ No subreddits configured[/red]")
            rprint("[yellow]Set SUBREDDITS in .env file (comma-separated)[/yellow]")
            rprint("Example: SUBREDDITS=ClaudeAI,Claude,ClaudeCode\n")
            raise typer.Exit(1)
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

            # Classify (with or without cache)
            classifier = create_classifier()
            cached_engine = create_cached_engine(settings)

            # Convert posts to dicts for compatibility
            posts_dicts = [
                {
                    'id': p.id,
                    'title': p.title,
                    'selftext': p.selftext,
                    'author': p.author,
                    'score': p.score,
                    'num_comments': p.num_comments,
                    'created_utc': p.created_utc,
                    'url': p.url,
                    'subreddit': p.subreddit,
                }
                for p in posts
            ]

            if no_cache or not settings.is_mysql_configured():
                if no_cache:
                    rprint(f"[yellow]Cache bypassed[/yellow]")
                rprint(f"[dim]Classifying {len(posts)} posts with Claude...[/dim]")
                classifications = classifier.classify_posts(posts)
                cache_stats = {'total': len(posts), 'cached': 0, 'new': len(classifications), 'cache_hit_rate': 0.0}
            else:
                rprint(f"[dim]Checking cache and classifying new posts...[/dim]")
                classifications, cache_stats = cached_engine.analyze_with_cache(posts_dicts, classifier)

                # Show cache stats
                table = Table(title="💾 Cache Stats", show_header=False, box=None)
                table.add_row("Total posts", str(cache_stats['total']))
                table.add_row("Cached", f"[green]{cache_stats['cached']}[/green] ({cache_stats['cache_hit_rate']:.1%})")
                table.add_row("New classified", f"[cyan]{cache_stats['new']}[/cyan]")
                if cache_stats['api_cost_saved'] > 0:
                    table.add_row("API cost saved", f"~${cache_stats['api_cost_saved']:.3f}")
                console.print(table)
                rprint()

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

            # Save scan history if cache is enabled
            if not no_cache and settings.is_mysql_configured():
                cached_engine.save_scan_result(sub, cache_stats, report.signal_ratio)

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

    if not subreddits:
        rprint("\n[red]✗ No subreddits configured[/red]")
        rprint("[yellow]Set SUBREDDITS in .env file (comma-separated)[/yellow]")
        rprint("Example: SUBREDDITS=ClaudeAI,Claude,ClaudeCode\n")
        raise typer.Exit(1)

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

    # Database
    rprint(f"\n[bold]Database Cache:[/bold]")
    if settings.is_mysql_configured():
        rprint(f"  Status: [green]Enabled (MariaDB)[/green]")
        rprint(f"  Host: {settings.mysql_host}:{settings.mysql_port}")
        rprint(f"  Database: {settings.mysql_database}")
        rprint(f"  User: {settings.mysql_user}")
    else:
        rprint(f"  Status: [yellow]Disabled[/yellow]")
        rprint(f"  [dim]Set MYSQL_* variables in .env to enable[/dim]")

    # Subreddits
    rprint(f"\n[bold]Target Subreddits:[/bold]")
    subreddit_list = settings.get_subreddit_list()
    if subreddit_list:
        for sub in subreddit_list:
            rprint(f"  • r/{sub}")
    else:
        rprint(f"  [yellow]None configured[/yellow]")
        rprint(f"  [dim]Set SUBREDDITS in .env file[/dim]")

    # Behavior
    rprint(f"\n[bold]Behavior:[/bold]")
    rprint(f"  Batch Size: {settings.default_batch_size} posts")
    rprint(f"  Cache TTL: {settings.cache_ttl_hours} hours")
    rprint(f"  Debug Mode: {'Enabled' if settings.debug else 'Disabled'}")

    # Paths
    rprint(f"\n[bold]Output Paths:[/bold]")
    rprint(f"  Reports: {settings.reports_dir}")
    rprint(f"  Cache: {settings.cache_dir}")
    rprint(f"  Classifications: {settings.classifications_dir}")

    rprint()


@app.command(name="init-db")
def init_db():
    """
    Initialize database schema.

    Creates tables if they don't exist. Safe to run multiple times.
    Requires MySQL/MariaDB credentials in .env file.

    Example:

        reddit-analyzer init-db
    """
    if not settings.is_mysql_configured():
        rprint("[red]✗ MySQL not configured[/red]")
        rprint("[yellow]Add MYSQL_* variables to .env file[/yellow]\n")
        raise typer.Exit(1)

    from .db.connection import DatabaseConnection

    rprint("\n[cyan]Initializing database...[/cyan]\n")

    try:
        db = DatabaseConnection(settings)

        # Test connection
        if not db.test_connection():
            rprint("[red]✗ Database connection failed[/red]")
            rprint("[yellow]Check MySQL credentials and server status[/yellow]\n")
            raise typer.Exit(1)

        rprint("[green]✓[/green] Connection test passed")

        # Create schema
        db.init_db()

        rprint("[green]✓[/green] Database schema initialized")
        rprint(f"  Host: {settings.mysql_host}:{settings.mysql_port}")
        rprint(f"  Database: {settings.mysql_database}\n")
        rprint("[bold green]✓ Database ready![/bold green]\n")

    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command()
def history(
    subreddit: Optional[str] = typer.Argument(
        None,
        help="Filter by subreddit (optional)"
    ),
    limit: int = typer.Option(
        10,
        "--limit", "-l",
        help="Number of history entries to show"
    ),
):
    """
    Show scan history from database.

    Requires database to be configured and initialized.

    Examples:

        reddit-analyzer history

        reddit-analyzer history ClaudeAI --limit 20
    """
    if not settings.is_mysql_configured():
        rprint("[yellow]⚠ Database cache not configured[/yellow]\n")
        raise typer.Exit(1)

    try:
        from .db.connection import DatabaseConnection
        from .db.repository import Repository

        db = DatabaseConnection(settings)
        repo = Repository(db)

        history_data = repo.get_scan_history(subreddit, limit)

        if not history_data:
            rprint("[yellow]No scan history found[/yellow]\n")
            return

        # Create table
        table = Table(title="📈 Scan History")
        table.add_column("Date", style="cyan")
        table.add_column("Subreddit", style="bold")
        table.add_column("Fetched", justify="right")
        table.add_column("Classified", justify="right", style="cyan")
        table.add_column("Cached", justify="right", style="green")
        table.add_column("Signal %", justify="right", style="bold")

        for scan in history_data:
            table.add_row(
                scan['scan_date'].strftime("%Y-%m-%d %H:%M"),
                f"r/{scan['subreddit']}",
                str(scan['posts_fetched']),
                str(scan['posts_classified']),
                str(scan['posts_cached']),
                f"{scan['signal_ratio']:.1f}%" if scan['signal_ratio'] else "N/A"
            )

        rprint()
        console.print(table)
        rprint()

    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command(name="cache-stats")
def cache_stats():
    """
    Show database cache statistics.

    Displays total posts and classifications in cache.

    Example:

        reddit-analyzer cache-stats
    """
    if not settings.is_mysql_configured():
        rprint("[yellow]⚠ Database cache not configured[/yellow]\n")
        raise typer.Exit(1)

    try:
        from .db.connection import DatabaseConnection
        from .db.repository import Repository

        db = DatabaseConnection(settings)
        repo = Repository(db)

        total_posts = repo.get_total_cached_posts()
        total_classifications = repo.get_total_classifications()

        # Create panel
        stats_text = (
            f"[bold]Total Posts:[/bold] {total_posts:,}\n"
            f"[bold]Total Classifications:[/bold] {total_classifications:,}\n"
        )

        if total_classifications > 0:
            estimated_cost_saved = total_classifications * 0.001
            stats_text += f"[bold]Estimated API Cost Saved:[/bold] ${estimated_cost_saved:.2f}"

        panel = Panel(
            stats_text,
            title="💾 Cache Statistics",
            border_style="cyan"
        )

        rprint()
        console.print(panel)
        rprint()

    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    rprint("\n[bold cyan]Reddit Signal/Noise Analyzer[/bold cyan]")
    rprint("Version: 0.1.0")
    rprint("Powered by Claude AI (Anthropic)")
    rprint("\nGitHub: https://github.com/Zell0ss/claude-redditor\n")


if __name__ == "__main__":
    app()
