"""CLI interface for Reddit Signal/Noise Analyzer."""

import typer
from typing import Optional, List
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import create_scraper
from .classifier import create_classifier
from .analyzer import create_analyzer, create_cached_engine
from .reporter import create_reporter
from .config import settings
from .cli_helpers import ensure_mysql_configured, render_cache_stats_table, handle_scan_error, render_classifications_with_tags

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
    project: str = typer.Option(
        "default",
        "--project", "-p",
        help="Project name for multi-project support"
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
        subreddits = settings.get_project_subreddits(project)
        if not subreddits:
            rprint("[red]✗ No subreddits configured[/red]")
            rprint(f"[yellow]Set {project.upper()}_SUBREDDITS in .env file (comma-separated)[/yellow]")
            rprint("Example: SUBREDDITS=ClaudeAI,Claude,ClaudeCode\n")
            raise typer.Exit(1)
        rprint(f"\n[cyan]Analyzing all configured subreddits for project '{project}':[/cyan] {', '.join(f'r/{s}' for s in subreddits)}\n")
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
                classifications = classifier.classify_posts(posts, project=project)
                cache_stats = {'total': len(posts), 'cached': 0, 'new': len(classifications), 'cache_hit_rate': 0.0}
            else:
                rprint(f"[dim]Checking cache and classifying new posts...[/dim]")
                classifications, cache_stats = cached_engine.analyze_with_cache(posts_dicts, classifier, source='reddit', project=project)

                # Show cache stats
                console.print(render_cache_stats_table(cache_stats))
                rprint()

            # Filter successfully classified posts
            classified_post_ids = {c.post_id for c in classifications}
            filtered_posts = [p for p in posts if p.id in classified_post_ids]

            if len(filtered_posts) != len(posts):
                rprint(f"[yellow]⚠ {len(posts) - len(filtered_posts)} posts failed classification[/yellow]")

            # Show classifications with tags
            posts_dict = {p.id: p.title for p in posts}
            render_classifications_with_tags(classifications, posts_dict)

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
                cached_engine.save_scan_result(sub, cache_stats, report.signal_ratio, source='reddit', project=project)

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
            if len(subreddits) > 1:
                rprint(f"[red]✗ Error analyzing r/{sub}: {e}[/red]\n")
                if typer.confirm("Continue with next subreddit?", default=True):
                    continue
                else:
                    raise typer.Exit(1)
            else:
                handle_scan_error(e, f"scan r/{sub}")

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
    project: str = typer.Option(
        "default",
        "--project", "-p",
        help="Project name for multi-project support"
    ),
):
    """
    Compare signal/noise ratio across all configured subreddits.

    This command analyzes all subreddits defined in the SUBREDDITS
    environment variable and shows a comparison table.

    Example:

        reddit-analyzer compare --limit 30
    """
    subreddits = settings.get_project_subreddits(project)

    if not subreddits:
        rprint("\n[red]✗ No subreddits configured[/red]")
        rprint(f"[yellow]Set {project.upper()}_SUBREDDITS in .env file (comma-separated)[/yellow]")
        rprint("Example: SUBREDDITS=ClaudeAI,Claude,ClaudeCode\n")
        raise typer.Exit(1)

    rprint(f"\n[bold cyan]Comparing {len(subreddits)} subreddits for project '{project}'[/bold cyan]")
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
            classifications = classifier.classify_posts(posts, project=project)

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
    project: Optional[str] = typer.Option(
        None,
        "--project", "-p",
        help="Filter by project (optional)"
    ),
):
    """
    Show scan history from database.

    Requires database to be configured and initialized.

    Examples:

        reddit-analyzer history

        reddit-analyzer history ClaudeAI --limit 20
    """
    ensure_mysql_configured(settings)

    try:
        from .db.connection import DatabaseConnection
        from .db.repository import Repository

        db = DatabaseConnection(settings)
        repo = Repository(db)

        history_data = repo.get_scan_history(subreddit, limit, project)

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
def cache_stats(
    project: Optional[str] = typer.Option(
        None,
        "--project", "-p",
        help="Filter by project (optional)"
    ),
):
    """
    Show database cache statistics.

    Displays total posts and classifications in cache.

    Example:

        reddit-analyzer cache-stats
    """
    ensure_mysql_configured(settings)

    try:
        from .db.connection import DatabaseConnection
        from .db.repository import Repository

        db = DatabaseConnection(settings)
        repo = Repository(db)

        total_posts = repo.get_total_cached_posts(project)
        total_classifications = repo.get_total_classifications(project)

        # Create panel
        project_label = f" (Project: {project})" if project else ""
        stats_text = (
            f"[bold]Total Posts:[/bold] {total_posts:,}\n"
            f"[bold]Total Classifications:[/bold] {total_classifications:,}\n"
        )

        if total_classifications > 0:
            estimated_cost_saved = total_classifications * 0.001
            stats_text += f"[bold]Estimated API Cost Saved:[/bold] ${estimated_cost_saved:.2f}"

        panel = Panel(
            stats_text,
            title=f"💾 Cache Statistics{project_label}",
            border_style="cyan"
        )

        rprint()
        console.print(panel)
        rprint()

    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command()
def scan_hn(
    keywords: List[str] = typer.Option(
        None,
        "-k", "--keyword",
        help="Keywords to filter HN posts (can specify multiple: -k claude -k anthropic)"
    ),
    limit: int = typer.Option(
        50,
        "--limit", "-l",
        help="Number of posts to analyze"
    ),
    sort: str = typer.Option(
        "top",
        "--sort", "-s",
        help="Sort method: top, new, best"
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
    project: str = typer.Option(
        "default",
        "--project", "-p",
        help="Project name for multi-project support"
    ),
):
    """
    Scan and analyze posts from HackerNews.

    Examples:

        reddit-analyzer scan-hn -k claude -k anthropic

        reddit-analyzer scan-hn -k llm --limit 20 --sort new

        reddit-analyzer scan-hn -k ai --export-json
    """
    from .scrapers import create_hn_scraper
    from .classifier import create_classifier
    from .analyzer import create_analyzer, create_cached_engine
    from .reporter import create_reporter

    # Use default keywords from config if none provided
    if not keywords:
        keywords = settings.get_project_hn_keywords(project)
        rprint(f"[dim]Using default keywords for project '{project}': {', '.join(keywords)}[/dim]")

    rprint(f"\n[bold cyan]Analyzing HackerNews[/bold cyan]")
    rprint(f"[dim]Keywords: {', '.join(keywords)} | Limit: {limit} | Sort: {sort}[/dim]\n")

    try:
        # Scrape
        scraper = create_hn_scraper(keywords=keywords)
        posts = scraper.fetch_posts(limit=limit, sort=sort)

        if not posts:
            rprint(f"[yellow]⚠ No posts found matching keywords[/yellow]\n")
            raise typer.Exit(0)

        rprint(f"[green]✓[/green] Fetched {len(posts)} posts")

        # Classify (with or without cache)
        classifier = create_classifier()
        cached_engine = create_cached_engine(settings)

        # Convert posts to dicts for compatibility
        posts_dicts = [p.to_dict() for p in posts]

        if no_cache or not settings.is_mysql_configured():
            if no_cache:
                rprint(f"[yellow]Cache bypassed[/yellow]")
            rprint(f"[dim]Classifying {len(posts)} posts with Claude...[/dim]")
            classifications = classifier.classify_posts(posts, project=project)
            cache_stats = {'total': len(posts), 'cached': 0, 'new': len(classifications), 'cache_hit_rate': 0.0}
        else:
            rprint(f"[dim]Checking cache and classifying new posts...[/dim]")
            classifications, cache_stats = cached_engine.analyze_with_cache(
                posts_dicts,
                classifier,
                source='hackernews',
                project=project
            )

            # Show cache stats
            console.print(render_cache_stats_table(cache_stats))
            rprint()

        # Filter successfully classified posts
        classified_post_ids = {c.post_id for c in classifications}
        filtered_posts = [p for p in posts if p.id in classified_post_ids]

        if len(filtered_posts) != len(posts):
            rprint(f"[yellow]⚠ {len(posts) - len(filtered_posts)} posts failed classification[/yellow]")

        # Show classifications with tags
        posts_dict = {p.id: p.title for p in posts}
        render_classifications_with_tags(classifications, posts_dict)

        # Analyze
        analyzer = create_analyzer()
        report = analyzer.analyze(
            posts=filtered_posts,
            classifications=classifications,
            subreddit="HackerNews",
            period=f"{limit} {sort} posts (keywords: {', '.join(keywords)})",
        )

        # Save scan history if cache is enabled
        if settings.is_mysql_configured() and hasattr(cached_engine, 'repo'):
            cached_engine.repo.save_scan_history(
                subreddit="HackerNews",
                posts_fetched=len(posts),
                posts_classified=cache_stats['new'],
                posts_cached=cache_stats['cached'],
                signal_ratio=report.signal_ratio * 100,
                source='hackernews',
                project=project
            )

        # Display
        reporter = create_reporter()
        reporter.render_terminal(report, show_details=not no_details)

        # Export if requested
        if export_json:
            reporter.export_json(report)

        rprint("\n[green]✓ Analysis complete![/green]\n")

    except KeyboardInterrupt:
        rprint("\n[yellow]⚠ Aborted by user[/yellow]\n")
        raise typer.Exit(1)
    except Exception as e:
        handle_scan_error(e, "HackerNews scan")


@app.command()
def digest(
    project: str = typer.Option(
        "claudeia",
        "--project", "-p",
        help="Project name (e.g., 'claudeia', 'wineworld')"
    ),
    limit: int = typer.Option(
        15,
        "--limit", "-l",
        help="Maximum number of posts to include"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory for digest file (default: outputs/digests)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview posts without generating digest or marking as sent"
    ),
    min_confidence: float = typer.Option(
        0.7,
        "--min-confidence",
        help="Minimum classification confidence threshold (0.0-1.0)"
    ),
    format: str = typer.Option(
        "markdown",
        "--format", "-f",
        help="Output format: 'markdown' (default), 'json' (for web), or 'both'"
    ),
):
    """
    Generate daily digest of top signal posts.

    Creates a Spanish-language markdown file with:
    - News articles for each post
    - Radio host commentary
    - Original source links

    Posts are marked as 'sent' after successful generation,
    so they won't appear in future digests.

    Examples:

        reddit-analyzer digest --project claudeia --limit 15

        reddit-analyzer digest --project claudeia --dry-run

        reddit-analyzer digest -p claudeia -l 10 -o /tmp/digests
    """
    ensure_mysql_configured(settings)

    try:
        from .db.connection import DatabaseConnection
        from .db.repository import Repository
        from .digest import DigestGenerator

        db = DatabaseConnection(settings)
        repo = Repository(db)

        if dry_run:
            # Preview mode: show posts that would be included
            posts_data = repo.get_signal_posts_for_digest(
                project=project,
                limit=limit,
                min_confidence=min_confidence
            )

            if not posts_data:
                rprint(f"\n[yellow]No signal posts available for project '{project}'[/yellow]")
                rprint("[dim]Run a scan first: reddit-analyzer scan all --project {project}[/dim]\n")
                raise typer.Exit(0)

            rprint(f"\n[bold cyan]Preview: {len(posts_data)} posts would be included in digest[/bold cyan]\n")

            table = Table(title=f"Digest Preview - {project}")
            table.add_column("#", style="dim", width=3)
            table.add_column("Title", max_width=50)
            table.add_column("Score", justify="right", width=6)
            table.add_column("Category", width=15)
            table.add_column("Confidence", justify="right", width=10)
            table.add_column("Truncated?", width=10)

            for i, item in enumerate(posts_data, 1):
                post = item['post']
                classification = item['classification']
                table.add_row(
                    str(i),
                    post.get('title', '')[:50],
                    str(post.get('score', 0)),
                    classification.get('category', ''),
                    f"{classification.get('confidence', 0):.0%}" if classification.get('confidence') else "N/A",
                    "Yes" if item['selftext_truncated'] else "No"
                )

            console.print(table)
            rprint("\n[dim]Run without --dry-run to generate the digest[/dim]\n")
            raise typer.Exit(0)

        # Validate format
        if format not in ['markdown', 'json', 'both']:
            rprint(f"[red]Invalid format '{format}'. Use 'markdown', 'json', or 'both'[/red]")
            raise typer.Exit(1)

        # Generate digest
        rprint(f"\n[bold cyan]Generating digest for project '{project}'[/bold cyan]")
        rprint(f"[dim]Limit: {limit} posts | Min confidence: {min_confidence:.0%} | Format: {format}[/dim]\n")

        generator = DigestGenerator(repo)

        output_paths = []

        if format in ['markdown', 'both']:
            md_path = generator.generate(
                project=project,
                limit=limit,
                output_dir=output_dir,
                show_progress=True
            )
            output_paths.append(('markdown', md_path))

        if format in ['json', 'both']:
            json_path = generator.generate_json(
                project=project,
                limit=limit,
                show_progress=(format == 'json')  # Only show progress if not already shown for markdown
            )
            output_paths.append(('json', json_path))

        rprint(f"\n[bold green]✓ Digest generated successfully![/bold green]")
        for fmt, path in output_paths:
            rprint(f"[dim]{fmt}: {path}[/dim]")

        # Print paths for N8N to capture
        for _, path in output_paths:
            print(f"\n{path}")

    except typer.Exit:
        raise  # Re-raise typer.Exit without catching it
    except ValueError as e:
        rprint(f"\n[yellow]{e}[/yellow]")
        rprint("[dim]Run a scan first to populate signal posts[/dim]\n")
        raise typer.Exit(0)
    except Exception as e:
        rprint(f"\n[red]✗ Error generating digest: {e}[/red]\n")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    rprint("\n[bold cyan]Reddit Signal/Noise Analyzer[/bold cyan]")
    rprint("Version: 0.1.0")
    rprint("Powered by Claude AI (Anthropic)")
    rprint("\nGitHub: https://github.com/Zell0ss/claude-redditor\n")


# =============================================================================
# BOOKMARK COMMANDS
# =============================================================================

bookmark_app = typer.Typer(
    name="bookmark",
    help="Manage bookmarks for interesting stories from digests"
)
app.add_typer(bookmark_app, name="bookmark")


@bookmark_app.command("show")
def bookmark_show(
    date: str = typer.Argument(
        ...,
        help="Digest date (YYYY-MM-DD) or 'latest'"
    ),
):
    """
    Show all stories from a digest JSON file.

    Examples:

        reddit-analyzer bookmark show 2025-01-17

        reddit-analyzer bookmark show latest
    """
    import json

    web_dir = settings.output_dir / 'web'

    if date == 'latest':
        json_path = web_dir / 'latest.json'
    else:
        json_path = web_dir / f'{date}.json'

    if not json_path.exists():
        rprint(f"[red]Digest not found: {json_path}[/red]")
        rprint(f"[dim]Run 'reddit-analyzer digest --format json' first[/dim]")
        raise typer.Exit(1)

    # Read JSON
    data = json.loads(json_path.read_text())

    rprint(f"\n[bold cyan]📰 Digest: {data['digest_id']}[/bold cyan]")
    rprint(f"[dim]{data['story_count']} stories | Generated: {data['generated_at']}[/dim]\n")

    for story in data['stories']:
        # Format tags
        topic_tags = ','.join(story.get('topic_tags', [])) or 'none'
        format_tag = story.get('format_tag') or ''

        # Category color
        cat = story.get('category', '')
        cat_color = "green" if cat in ['technical', 'troubleshooting', 'research_verified'] else "yellow"

        rprint(f"[bold]{story['id']}[/bold]: [{cat_color}][{cat}][/{cat_color}] [cyan][{topic_tags}][/cyan]" +
               (f" [magenta][{format_tag}][/magenta]" if format_tag else ""))
        rprint(f"  {story['title'][:70]}{'...' if len(story['title']) > 70 else ''}")
        rprint(f"  [dim]{story['url']}[/dim]")
        rprint()


@bookmark_app.command("add")
def bookmark_add(
    story_id: str = typer.Argument(
        ...,
        help="Story ID (e.g., '2025-01-17-003')"
    ),
    note: Optional[str] = typer.Option(
        None,
        "--note", "-n",
        help="Optional note for this bookmark"
    ),
    status: str = typer.Option(
        "to_read",
        "--status", "-s",
        help="Initial status: to_read, to_implement, done"
    ),
):
    """
    Add a story to bookmarks.

    Examples:

        reddit-analyzer bookmark add 2025-01-17-003

        reddit-analyzer bookmark add 2025-01-17-003 --note "Interesting MCP server"

        reddit-analyzer bookmark add 2025-01-17-003 --status to_implement
    """
    import json
    from datetime import datetime

    ensure_mysql_configured(settings)

    # Validate status
    if status not in ['to_read', 'to_implement', 'done']:
        rprint(f"[red]Invalid status '{status}'. Use: to_read, to_implement, done[/red]")
        raise typer.Exit(1)

    # Extract date from story_id (format: YYYY-MM-DD-NNN)
    try:
        date_part = '-'.join(story_id.split('-')[:3])
        datetime.strptime(date_part, '%Y-%m-%d')  # Validate format
    except ValueError:
        rprint(f"[red]Invalid story_id format: {story_id}[/red]")
        rprint("[dim]Expected format: YYYY-MM-DD-NNN (e.g., 2025-01-17-003)[/dim]")
        raise typer.Exit(1)

    # Find the JSON file
    json_path = settings.output_dir / 'web' / f'{date_part}.json'
    if not json_path.exists():
        rprint(f"[red]Digest not found: {json_path}[/red]")
        raise typer.Exit(1)

    # Find the story
    data = json.loads(json_path.read_text())
    story = next((s for s in data['stories'] if s['id'] == story_id), None)

    if not story:
        rprint(f"[red]Story not found: {story_id}[/red]")
        rprint(f"[dim]Available IDs in this digest: {', '.join(s['id'] for s in data['stories'][:5])}...[/dim]")
        raise typer.Exit(1)

    # Save to database
    from .db.connection import DatabaseConnection
    from .db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    try:
        repo.add_bookmark(
            story_id=story_id,
            digest_date=date_part,
            story_title=story['title'],
            story_url=story.get('url', ''),
            story_source=story.get('source', ''),
            story_category=story.get('category', ''),
            story_topic_tags=story.get('topic_tags', []),
            story_format_tag=story.get('format_tag'),
            notes=note,
            status=status
        )
        rprint(f"[green]✓ Bookmarked: {story_id}[/green]")
        rprint(f"  {story['title'][:60]}...")
        if note:
            rprint(f"  [dim]Note: {note}[/dim]")
    except Exception as e:
        if 'Duplicate' in str(e):
            rprint(f"[yellow]Already bookmarked: {story_id}[/yellow]")
        else:
            rprint(f"[red]Error adding bookmark: {e}[/red]")
            raise typer.Exit(1)


@bookmark_app.command("list")
def bookmark_list(
    status: Optional[str] = typer.Option(
        None,
        "--status", "-s",
        help="Filter by status: to_read, to_implement, done, all"
    ),
    limit: int = typer.Option(
        20,
        "--limit", "-l",
        help="Maximum number of bookmarks to show"
    ),
):
    """
    List bookmarks from the database.

    Examples:

        reddit-analyzer bookmark list

        reddit-analyzer bookmark list --status to_read

        reddit-analyzer bookmark list --status to_implement --limit 10
    """
    ensure_mysql_configured(settings)

    from .db.connection import DatabaseConnection
    from .db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    # Get bookmarks
    bookmarks = repo.get_bookmarks(status=status if status != 'all' else None, limit=limit)

    if not bookmarks:
        rprint("[yellow]No bookmarks found[/yellow]")
        if status:
            rprint(f"[dim]Try without --status filter or with --status all[/dim]")
        raise typer.Exit(0)

    rprint(f"\n[bold cyan]📚 Bookmarks ({len(bookmarks)})[/bold cyan]\n")

    # Status emoji mapping
    status_emoji = {
        'to_read': '📖',
        'to_implement': '🔧',
        'done': '✅'
    }

    for b in bookmarks:
        emoji = status_emoji.get(b['status'], '❓')
        tags = ','.join(b.get('story_topic_tags') or []) or 'none'
        title = b.get('story_title', '')

        rprint(f"{emoji} [bold]{b['story_id']}[/bold] [{b.get('story_category', '')}] [cyan][{tags}][/cyan]")
        rprint(f"   {title[:65]}{'...' if len(title) > 65 else ''}")
        if b.get('notes'):
            rprint(f"   [dim]📝 {b['notes']}[/dim]")
        rprint(f"   [dim]{b.get('story_url', '')}[/dim]")
        rprint()


@bookmark_app.command("done")
def bookmark_done(
    story_id: str = typer.Argument(
        ...,
        help="Story ID to mark as done"
    ),
):
    """
    Mark a bookmark as done.

    Examples:

        reddit-analyzer bookmark done 2025-01-17-003
    """
    ensure_mysql_configured(settings)

    from .db.connection import DatabaseConnection
    from .db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    updated = repo.update_bookmark_status(story_id, 'done')

    if updated:
        rprint(f"[green]✓ Marked as done: {story_id}[/green]")
    else:
        rprint(f"[yellow]Bookmark not found: {story_id}[/yellow]")
        raise typer.Exit(1)


@bookmark_app.command("status")
def bookmark_status(
    story_id: str = typer.Argument(
        ...,
        help="Story ID to update"
    ),
    new_status: str = typer.Argument(
        ...,
        help="New status: to_read, to_implement, done"
    ),
):
    """
    Change bookmark status.

    Examples:

        reddit-analyzer bookmark status 2025-01-17-003 to_implement
    """
    ensure_mysql_configured(settings)

    if new_status not in ['to_read', 'to_implement', 'done']:
        rprint(f"[red]Invalid status '{new_status}'. Use: to_read, to_implement, done[/red]")
        raise typer.Exit(1)

    from .db.connection import DatabaseConnection
    from .db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    updated = repo.update_bookmark_status(story_id, new_status)

    if updated:
        rprint(f"[green]✓ Updated {story_id} → {new_status}[/green]")
    else:
        rprint(f"[yellow]Bookmark not found: {story_id}[/yellow]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
