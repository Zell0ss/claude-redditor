"""Bookmark commands for managing interesting stories."""

import json
import typer
from typing import Optional
from datetime import datetime
from rich import print as rprint

from ..config import settings
from .helpers import ensure_mysql_configured, render_bookmarks_list, render_digest_stories

app = typer.Typer(
    name="bookmark",
    help="Manage bookmarks for interesting stories from digests"
)


@app.command("show")
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
    render_digest_stories(data['stories'], data['digest_id'], data['generated_at'])


@app.command("add")
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
    from ..db.connection import DatabaseConnection
    from ..db.repository import Repository

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
            post_id=story.get('post_id'),  # Link to original post
            notes=note,
            status=status
        )
        rprint(f"[green]✓ Bookmarked: {story_id}[/green]")
        rprint(f"  {story['title'][:60]}...")
        if story.get('post_id'):
            rprint(f"  [dim]Post: {story['post_id']}[/dim]")
        if note:
            rprint(f"  [dim]Note: {note}[/dim]")
    except Exception as e:
        if 'Duplicate' in str(e):
            rprint(f"[yellow]Already bookmarked: {story_id}[/yellow]")
        else:
            rprint(f"[red]Error adding bookmark: {e}[/red]")
            raise typer.Exit(1)


@app.command("list")
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

    from ..db.connection import DatabaseConnection
    from ..db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    # Get bookmarks
    bookmarks = repo.get_bookmarks(status=status if status != 'all' else None, limit=limit)

    if not bookmarks:
        rprint("[yellow]No bookmarks found[/yellow]")
        if status:
            rprint(f"[dim]Try without --status filter or with --status all[/dim]")
        raise typer.Exit(0)

    render_bookmarks_list(bookmarks)


@app.command("done")
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

    from ..db.connection import DatabaseConnection
    from ..db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    updated = repo.update_bookmark_status(story_id, 'done')

    if updated:
        rprint(f"[green]✓ Marked as done: {story_id}[/green]")
    else:
        rprint(f"[yellow]Bookmark not found: {story_id}[/yellow]")
        raise typer.Exit(1)


@app.command("status")
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

    from ..db.connection import DatabaseConnection
    from ..db.repository import Repository

    db = DatabaseConnection(settings)
    repo = Repository(db)

    updated = repo.update_bookmark_status(story_id, new_status)

    if updated:
        rprint(f"[green]✓ Updated {story_id} → {new_status}[/green]")
    else:
        rprint(f"[yellow]Bookmark not found: {story_id}[/yellow]")
        raise typer.Exit(1)
