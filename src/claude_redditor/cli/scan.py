"""Scan commands for Reddit and HackerNews."""

import typer
from typing import Optional, List, Tuple, Any
from rich import print as rprint

from ..scrapers import create_reddit_scraper, create_hn_scraper
from ..classifier import create_classifier
from ..analyzer import create_analyzer, create_cached_engine
from ..reporter import create_reporter
from ..config import settings
from ..projects import project_loader
from .helpers import (
    console,
    render_cache_stats_table,
    handle_scan_error,
    render_classifications_with_tags,
)

app = typer.Typer()


# Helper Functions

def _scan_reddit_source(
    subreddit: str,
    limit: int,
    sort: str,
    time_filter: str,
    project: str,
    no_cache: bool,
    no_details: bool,
    export_json: bool,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[dict]]:
    """
    Scan a single Reddit subreddit source.

    Returns: (posts, classifications, report, cache_stats) or (None, None, None, None) on failure
    """
    rprint(f"[bold cyan]Analyzing r/{subreddit}[/bold cyan]")
    rprint(f"[dim]Fetching {limit} {sort} posts...[/dim]\n")

    try:
        # Scrape
        scraper = create_reddit_scraper()
        posts = scraper.fetch_posts(subreddit, limit=limit, sort=sort, time_filter=time_filter)

        if not posts:
            rprint(f"[yellow]⚠ No posts found for r/{subreddit}[/yellow]\n")
            return None, None, None, None

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
            classifications, cache_stats = cached_engine.analyze_with_cache(
                posts_dicts, classifier, source='reddit', project=project
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
            subreddit=subreddit,
            period=f"{limit} {sort} posts ({time_filter if sort == 'top' else 'recent'})",
        )

        # Save scan history if cache is enabled
        if not no_cache and settings.is_mysql_configured():
            cached_engine.save_scan_result(
                subreddit, cache_stats, report.signal_ratio, source='reddit', project=project
            )

        # Report
        reporter = create_reporter()
        rprint()  # Blank line before report
        reporter.render_terminal(report, show_details=not no_details)

        # Export JSON if requested
        if export_json:
            json_path = reporter.export_json(report)
            rprint(f"[green]✓[/green] Report exported to: {json_path}\n")

        return posts, classifications, report, cache_stats

    except Exception as e:
        rprint(f"[red]✗ Error analyzing r/{subreddit}: {e}[/red]\n")
        return None, None, None, None


def _scan_hackernews_source(
    keywords: List[str],
    limit: int,
    sort: str,
    project: str,
    no_cache: bool,
    no_details: bool,
    export_json: bool,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[dict]]:
    """
    Scan HackerNews with keywords.

    Returns: (posts, classifications, report, cache_stats) or (None, None, None, None) on failure
    """
    rprint(f"[bold cyan]Analyzing HackerNews[/bold cyan]")
    rprint(f"[dim]Keywords: {', '.join(keywords)} | Limit: {limit} | Sort: {sort}[/dim]\n")

    try:
        # Scrape
        scraper = create_hn_scraper(keywords=keywords)
        posts = scraper.fetch_posts(limit=limit, sort=sort)

        if not posts:
            rprint(f"[yellow]⚠ No HackerNews posts found matching keywords[/yellow]\n")
            return None, None, None, None

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
                posts_dicts, classifier, source='hackernews', project=project
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

        # Report
        reporter = create_reporter()
        rprint()  # Blank line before report
        reporter.render_terminal(report, show_details=not no_details)

        # Export JSON if requested
        if export_json:
            json_path = reporter.export_json(report)
            rprint(f"[green]✓[/green] Report exported to: {json_path}\n")

        return posts, classifications, report, cache_stats

    except Exception as e:
        rprint(f"[red]✗ Error scanning HackerNews: {e}[/red]\n")
        return None, None, None, None


# Commands

@app.command()
def scan(
    project: str = typer.Argument(
        ...,
        help="Project name (e.g., 'claudeia', 'wineworld')"
    ),
    source: str = typer.Option(
        "all",
        "--source", "-s",
        help="Source to scan: all, reddit, hackernews"
    ),
    limit: int = typer.Option(
        50,
        "--limit", "-l",
        help="Number of posts per source"
    ),
    sort: str = typer.Option(
        "hot",
        "--sort",
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
    Scan and analyze posts from configured sources for a project.

    Examples:

        # Scan all sources (Reddit + HackerNews)
        reddit-analyzer scan claudeia

        # Scan only Reddit subreddits
        reddit-analyzer scan claudeia --source reddit

        # Scan only HackerNews
        reddit-analyzer scan claudeia --source hackernews

        # Scan with custom limit and sort
        reddit-analyzer scan claudeia --source reddit --limit 100 --sort top

        # Export results to JSON
        reddit-analyzer scan claudeia --export-json
    """
    # Validate source parameter
    valid_sources = ["all", "reddit", "hackernews"]
    if source not in valid_sources:
        rprint(f"[red]✗ Invalid source '{source}'. Must be: {', '.join(valid_sources)}[/red]")
        raise typer.Exit(1)

    # Load project configuration
    try:
        proj = project_loader.load(project)
    except FileNotFoundError:
        # Get available projects for suggestion
        try:
            available = project_loader.discover_projects()
            project_names = [p.name for p in available]
            rprint(f"[red]✗ Project '{project}' not found[/red]")
            rprint(f"[yellow]Available projects: {', '.join(project_names)}[/yellow]")
        except Exception:
            rprint(f"[red]✗ Project '{project}' not found[/red]")
        raise typer.Exit(1)

    # Validate source configuration
    has_reddit = proj.subreddits and len(proj.subreddits) > 0
    has_hn = proj.hn_keywords and len(proj.hn_keywords) > 0

    if source == "reddit" and not has_reddit:
        rprint(f"[red]✗ No subreddits configured for project '{project}'[/red]")
        rprint(f"[yellow]Add subreddits to src/claude_redditor/projects/{project}/config.yaml[/yellow]")
        raise typer.Exit(1)

    if source == "hackernews" and not has_hn:
        rprint(f"[red]✗ No HackerNews keywords configured for project '{project}'[/red]")
        rprint(f"[yellow]Add keywords to src/claude_redditor/projects/{project}/config.yaml[/yellow]")
        raise typer.Exit(1)

    if source == "all" and not has_reddit and not has_hn:
        rprint(f"[red]✗ No sources configured for project '{project}'[/red]")
        rprint(f"[yellow]Add subreddits and/or keywords to src/claude_redditor/projects/{project}/config.yaml[/yellow]")
        raise typer.Exit(1)

    # Warn if "all" selected but only one source is configured
    if source == "all":
        if not has_reddit:
            rprint(f"[yellow]⚠ Project '{project}' has no subreddits configured. Scanning HackerNews only.[/yellow]\n")
        elif not has_hn:
            rprint(f"[yellow]⚠ Project '{project}' has no HackerNews keywords configured. Scanning Reddit only.[/yellow]\n")
        else:
            rprint(f"\n[cyan]Scanning all sources for project '{project}':[/cyan]")
            rprint(f"[dim]Reddit: {', '.join(f'r/{s}' for s in proj.subreddits)}[/dim]")
            rprint(f"[dim]HackerNews: {', '.join(proj.hn_keywords)}[/dim]\n")

    # Scan sources
    reports = []

    # Scan Reddit subreddits
    if source in ["all", "reddit"] and has_reddit:
        for sub in proj.subreddits:
            _, _, report, _ = _scan_reddit_source(
                subreddit=sub,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                project=project,
                no_cache=no_cache,
                no_details=no_details,
                export_json=export_json,
            )
            if report:
                reports.append(report)

    # Scan HackerNews
    if source in ["all", "hackernews"] and has_hn:
        _, _, report, _ = _scan_hackernews_source(
            keywords=proj.hn_keywords,
            limit=limit,
            sort="top",  # HN always uses "top" sort
            project=project,
            no_cache=no_cache,
            no_details=no_details,
            export_json=export_json,
        )
        if report:
            reports.append(report)

    # Show comparison if multiple sources
    if len(reports) > 1:
        rprint("\n[bold cyan]Source Comparison[/bold cyan]\n")
        reporter = create_reporter()
        reporter.render_comparison(reports)

    if reports:
        rprint(f"\n[bold green]✓ Analysis complete![/bold green]\n")
    else:
        rprint(f"\n[yellow]⚠ No reports generated[/yellow]\n")


@app.command()
def compare(
    project: str = typer.Argument(
        ...,
        help="Project name to compare subreddits for"
    ),
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
    Compare signal/noise ratio across all configured subreddits for a project.

    This command analyzes all subreddits defined in the project's
    config.yaml and shows a comparison table. Does not use cache
    for quick comparative analysis.

    Examples:

        reddit-analyzer compare claudeia

        reddit-analyzer compare claudeia --limit 30 --sort top
    """
    # Load project configuration
    try:
        proj = project_loader.load(project)
        subreddits = proj.subreddits
    except FileNotFoundError:
        # Get available projects for suggestion
        try:
            available = project_loader.discover_projects()
            project_names = [p.name for p in available]
            rprint(f"[red]✗ Project '{project}' not found[/red]")
            rprint(f"[yellow]Available projects: {', '.join(project_names)}[/yellow]")
        except Exception:
            rprint(f"[red]✗ Project '{project}' not found[/red]")
        raise typer.Exit(1)

    if not subreddits:
        rprint(f"\n[red]✗ No subreddits configured for project '{project}'[/red]")
        rprint(f"[yellow]Add subreddits to src/claude_redditor/projects/{project}/config.yaml[/yellow]")
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
