"""Scan commands for Reddit and HackerNews."""

import typer
from typing import Optional, List
from rich import print as rprint

from ..scrapers import create_reddit_scraper, create_hn_scraper
from ..classifier import create_classifier
from ..analyzer import create_analyzer, create_cached_engine
from ..reporter import create_reporter
from ..config import settings
from .helpers import (
    console,
    render_cache_stats_table,
    handle_scan_error,
    render_classifications_with_tags,
)

app = typer.Typer()


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
            scraper = create_reddit_scraper()
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
            scraper = create_reddit_scraper()
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


@app.command(name="scan-hn")
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
