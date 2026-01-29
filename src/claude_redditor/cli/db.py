"""Database commands: init-db, history, cache-stats."""

import typer
from typing import Optional
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel

from ..config import settings
from .helpers import console, ensure_mysql_configured

app = typer.Typer()


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

    from ..db.connection import DatabaseConnection

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
        from ..db.connection import DatabaseConnection
        from ..db.repository import Repository

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
        from ..db.connection import DatabaseConnection
        from ..db.repository import Repository

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


@app.command(name="regenerate-json")
def regenerate_json(
    project: str = typer.Option(
        "claudeia",
        "--project", "-p",
        help="Project to regenerate JSONs for"
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date", "-d",
        help="Specific date (YYYY-MM-DD) or 'all' for all dates"
    ),
):
    """
    Regenerate JSON digests from database.

    Reconstructs JSON files for the web viewer from historical data.
    Useful for backfilling after enabling JSON output.

    Examples:

        reddit-analyzer regenerate-json --project claudeia --date all

        reddit-analyzer regenerate-json -p claudeia -d 2026-01-18
    """
    ensure_mysql_configured(settings)

    import json
    from datetime import datetime
    from pathlib import Path
    from sqlalchemy import text

    try:
        from ..db.connection import DatabaseConnection

        db = DatabaseConnection(settings)

        with db.get_session() as session:
            # Get available digest dates
            result = session.execute(text("""
                SELECT DISTINCT DATE(sent_in_digest_at) as digest_date
                FROM classifications
                WHERE sent_in_digest_at IS NOT NULL
                AND project = :project
                ORDER BY digest_date DESC
            """), {"project": project})

            available_dates = [row.digest_date for row in result]

            if not available_dates:
                rprint(f"[yellow]No digest data found for project '{project}'[/yellow]\n")
                raise typer.Exit(0)

            # Determine which dates to process
            if date == "all":
                dates_to_process = available_dates
            elif date:
                from datetime import datetime as dt
                try:
                    target_date = dt.strptime(date, "%Y-%m-%d").date()
                    if target_date not in available_dates:
                        rprint(f"[yellow]No digest found for {date}[/yellow]")
                        rprint(f"[dim]Available dates: {', '.join(str(d) for d in available_dates[:5])}...[/dim]\n")
                        raise typer.Exit(0)
                    dates_to_process = [target_date]
                except ValueError:
                    rprint(f"[red]Invalid date format. Use YYYY-MM-DD[/red]\n")
                    raise typer.Exit(1)
            else:
                # Show available dates and ask
                rprint(f"\n[cyan]Available digest dates for '{project}':[/cyan]")
                for d in available_dates:
                    rprint(f"  • {d}")
                rprint(f"\n[dim]Use --date YYYY-MM-DD or --date all[/dim]\n")
                raise typer.Exit(0)

            # Process each date
            output_dir = settings.output_dir / 'web'
            output_dir.mkdir(parents=True, exist_ok=True)

            rprint(f"\n[cyan]Regenerating {len(dates_to_process)} JSON digest(s)...[/cyan]\n")

            for digest_date in dates_to_process:
                # Get posts for this digest date
                result = session.execute(text("""
                    SELECT
                        p.id, p.title, p.author, p.url, p.score, p.num_comments, p.subreddit,
                        c.category, c.confidence, c.topic_tags, c.format_tag,
                        c.red_flags, c.reasoning, c.sent_in_digest_at
                    FROM posts p
                    JOIN classifications c ON p.id = c.post_id
                    WHERE DATE(c.sent_in_digest_at) = :digest_date
                    AND c.project = :project
                    ORDER BY c.sent_in_digest_at ASC
                """), {"digest_date": digest_date, "project": project})

                rows = list(result)

                if not rows:
                    continue

                # Use sequence number 01 for regenerated historical data
                seq_num = 1
                digest_id = f"{digest_date}_{seq_num:02d}"

                # Build stories array
                stories = []
                for idx, row in enumerate(rows, 1):
                    # Determine source from post ID
                    if row.id.startswith('reddit_'):
                        source = f"r/{row.subreddit}" if row.subreddit else "Reddit"
                    elif row.id.startswith('hn_'):
                        source = "HackerNews"
                    else:
                        source = "Unknown"

                    # Parse JSON fields if they're strings
                    topic_tags = row.topic_tags
                    if isinstance(topic_tags, str):
                        topic_tags = json.loads(topic_tags) if topic_tags else []
                    topic_tags = topic_tags or []

                    red_flags = row.red_flags
                    if isinstance(red_flags, str):
                        red_flags = json.loads(red_flags) if red_flags else []
                    red_flags = red_flags or []

                    story = {
                        "id": f"{digest_id}_{idx:03d}",
                        "post_id": row.id,  # Original post ID for traceability
                        "title": row.title or "",
                        "source": source,
                        "author": row.author or "unknown",
                        "url": row.url or "",
                        "score": row.score or 0,
                        "num_comments": row.num_comments or 0,
                        "category": row.category or "technical",
                        "confidence": float(row.confidence) if row.confidence else 0.0,
                        "topic_tags": topic_tags,
                        "format_tag": row.format_tag,
                        "red_flags": red_flags,
                        "reasoning": row.reasoning or ""
                    }
                    stories.append(story)

                # Build digest JSON
                digest_data = {
                    "digest_id": digest_id,
                    "generated_at": datetime.combine(digest_date, datetime.min.time()).isoformat() + "Z",
                    "project": project,
                    "story_count": len(stories),
                    "stories": stories
                }

                # Write file with sequence number
                output_path = output_dir / f"{project}_{digest_date}_{seq_num:02d}.json"
                output_path.write_text(
                    json.dumps(digest_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )

                rprint(f"  [green]✓[/green] {output_path.name} ({len(stories)} stories)")

            # Update latest.json symlink to most recent
            if dates_to_process:
                latest_date = max(dates_to_process)
                latest_path = output_dir / "latest.json"
                if latest_path.exists() or latest_path.is_symlink():
                    latest_path.unlink()
                latest_path.symlink_to(f"{project}_{latest_date}_01.json")

            rprint(f"\n[bold green]✓ Done! Regenerated {len(dates_to_process)} JSON file(s)[/bold green]\n")

    except typer.Exit:
        raise
    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command(name="regenerate-tiers")
def regenerate_tiers(
    project: str = typer.Option("claudeia", help="Project to backfill"),
    category_filter: str = typer.Option("SIGNAL", help="Category filter: SIGNAL, ALL"),
    limit: int = typer.Option(0, help="Max posts to process (0 = all)"),
    dry_run: bool = typer.Option(False, help="Show what would be done without executing"),
):
    """
    Regenerate tier classifications for historical posts.

    This command backfills the tier tagging system for posts that already have
    category classifications but lack tier data (tier_tags, tier_clusters, tier_scoring).

    Useful for:
    - Adding tier data to historical posts after implementing the tier system
    - Re-classifying posts with updated tier prompts

    Examples:

        # Dry run to see what would be processed
        reddit-analyzer regenerate-tiers --project claudeia --dry-run

        # Backfill SIGNAL posts (technical, troubleshooting, research_verified)
        reddit-analyzer regenerate-tiers --project claudeia --category-filter SIGNAL

        # Backfill first 50 posts only
        reddit-analyzer regenerate-tiers --project claudeia --limit 50

        # Backfill all categories except UNRELATED
        reddit-analyzer regenerate-tiers --project claudeia --category-filter ALL
    """
    ensure_mysql_configured(settings)

    from ..db.connection import DatabaseConnection
    from ..db.repository import Repository
    from ..classifier import create_classifier
    from ..core.models import RedditPost

    try:
        rprint(f"\n[cyan]Regenerating tier tags for project: {project}[/cyan]\n")

        db = DatabaseConnection(settings)
        repo = Repository(db)
        classifier = create_classifier()

        # Determine category filter
        if category_filter.upper() == "SIGNAL":
            categories = ['technical', 'troubleshooting', 'research_verified']
            rprint(f"[yellow]→[/yellow] Category filter: SIGNAL (technical, troubleshooting, research_verified)")
        elif category_filter.upper() == "ALL":
            categories = None
            rprint(f"[yellow]→[/yellow] Category filter: ALL (except UNRELATED)")
        else:
            rprint(f"[red]✗ Invalid category filter: {category_filter}[/red]")
            rprint("[yellow]Valid options: SIGNAL, ALL[/yellow]\n")
            raise typer.Exit(1)

        # Get posts without tier tags
        rprint(f"[yellow]→[/yellow] Querying database for posts without tier tags...")
        posts_data = repo.get_posts_without_tiers(
            project=project,
            categories=categories,
            limit=limit
        )

        if not posts_data:
            rprint(f"\n[green]✓ No posts found without tier tags[/green]\n")
            return

        rprint(f"[bold cyan]Found {len(posts_data)} posts without tier tags[/bold cyan]\n")

        if dry_run:
            rprint("[yellow]DRY RUN - No changes will be made[/yellow]")
            rprint(f"\n[dim]Would process {len(posts_data)} posts with tier classification[/dim]\n")
            return

        # Convert to RedditPost objects for classifier
        posts = [
            RedditPost(
                id=p['id'],
                title=p['title'],
                selftext=p['selftext'],
                author=p['author'],
                score=p['score'],
                num_comments=p['num_comments'],
                created_utc=p['created_utc'],
                url=p['url'],
                subreddit=p['subreddit'] or '',
                flair=p.get('flair')
            )
            for p in posts_data
        ]

        # Process in batches
        batch_size = 20
        total_processed = 0

        for i in range(0, len(posts), batch_size):
            batch = posts[i:i+batch_size]

            try:
                # Call tier classification directly
                tier_results = classifier._classify_tiers_batch(batch, project=project)

                # Update DB with tier data
                for tier_data in tier_results:
                    repo.update_classification_tiers(
                        post_id=tier_data['post_id'],
                        project=project,
                        tier_tags=tier_data.get('tier_tags'),
                        tier_clusters=tier_data.get('clusters', []),
                        tier_scoring=tier_data.get('scoring')
                    )

                total_processed += len(tier_results)
                rprint(f"  [green]✓[/green] Processed {total_processed}/{len(posts)} posts")

            except Exception as e:
                rprint(f"  [red]✗[/red] Error processing batch: {e}")
                continue

        rprint(f"\n[bold green]✓ Tier backfill complete! Processed {total_processed} posts[/bold green]\n")

    except typer.Exit:
        raise
    except Exception as e:
        rprint(f"[red]✗ Error: {e}[/red]\n")
        raise typer.Exit(1)
