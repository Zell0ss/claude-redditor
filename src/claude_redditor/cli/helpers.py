"""CLI helper functions for output formatting and common operations."""

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from typing import Dict, List

from ..config import Settings

console = Console()


def ensure_mysql_configured(settings: Settings) -> None:
    """
    Verify MySQL is configured or exit with error.

    Args:
        settings: Application settings instance

    Raises:
        typer.Exit: If MySQL is not configured
    """
    if not settings.is_mysql_configured():
        rprint("[yellow]⚠ Database cache not configured[/yellow]")
        rprint("[dim]Add MYSQL_* variables to .env file[/dim]\n")
        raise typer.Exit(1)


def render_cache_stats_table(cache_stats: Dict) -> Table:
    """
    Create Rich table displaying cache statistics.

    Args:
        cache_stats: Dictionary with keys:
            - total: Total posts processed
            - cached: Posts retrieved from cache
            - new: Posts newly classified
            - cache_hit_rate: Hit rate as decimal (0.0-1.0)
            - api_cost_saved: Optional cost savings

    Returns:
        Rich Table ready to print
    """
    table = Table(title="💾 Cache Stats", show_header=False, box=None)
    table.add_row("Total posts", str(cache_stats['total']))
    table.add_row(
        "Cached",
        f"[green]{cache_stats['cached']}[/green] ({cache_stats['cache_hit_rate']:.1%})"
    )
    table.add_row("New classified", f"[cyan]{cache_stats['new']}[/cyan]")

    if cache_stats.get('api_cost_saved', 0) > 0:
        table.add_row("API cost saved", f"~${cache_stats['api_cost_saved']:.3f}")

    return table


def handle_scan_error(error: Exception, source: str = "scan") -> None:
    """
    Standard error handling for scan commands.

    Args:
        error: Exception that occurred
        source: Name of the command/source for context

    Raises:
        typer.Exit: Always exits with code 1
    """
    rprint(f"[red]✗ Error during {source}: {error}[/red]\n")
    raise typer.Exit(1)


def render_classifications_with_tags(classifications, posts_dict: Dict[str, str]) -> None:
    """
    Print classification results with tags in a compact format.

    Args:
        classifications: List of Classification objects
        posts_dict: Dict mapping post_id to title
    """
    rprint()
    rprint(f"[bold]Classified {len(classifications)} posts:[/bold]")

    for c in classifications:
        # Category with color
        category_color = "green" if c.category.value in ['technical', 'troubleshooting', 'research_verified'] else \
                        "red" if c.category.value in ['mystical', 'unverified_claim', 'engagement_bait'] else \
                        "yellow"

        # Format topic tags
        topic_str = f"[cyan]{','.join(c.topic_tags)}[/cyan]" if c.topic_tags else "[dim]none[/dim]"

        # Format format tag
        format_str = f"[magenta]{c.format_tag}[/magenta]" if c.format_tag else ""

        # Title (truncated)
        title = posts_dict.get(c.post_id, c.post_id)
        title_short = title[:50] + "..." if len(title) > 50 else title

        # Output line: ✓ [category] [topic_tags] [format_tag] "title"
        line_parts = [
            "✓",
            f"[{category_color}][{c.category.value}][/{category_color}]",
            f"[{topic_str}]",
        ]
        if format_str:
            line_parts.append(f"[{format_str}]")
        line_parts.append(f'"{title_short}"')

        rprint(" ".join(line_parts))

    rprint()


def render_bookmarks_list(bookmarks: List[Dict]) -> None:
    """
    Print bookmarks list with status emojis.

    Args:
        bookmarks: List of bookmark dicts from repository
    """
    rprint(f"\n[bold cyan]📚 Bookmarks ({len(bookmarks)})[/bold cyan]\n")

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


def render_digest_stories(stories: List[Dict], digest_id: str, generated_at: str) -> None:
    """
    Print digest stories for bookmark show command.

    Args:
        stories: List of story dicts from JSON
        digest_id: Digest identifier (date)
        generated_at: Generation timestamp
    """
    rprint(f"\n[bold cyan]📰 Digest: {digest_id}[/bold cyan]")
    rprint(f"[dim]{len(stories)} stories | Generated: {generated_at}[/dim]\n")

    for story in stories:
        topic_tags = ','.join(story.get('topic_tags', [])) or 'none'
        format_tag = story.get('format_tag') or ''

        cat = story.get('category', '')
        cat_color = "green" if cat in ['technical', 'troubleshooting', 'research_verified'] else "yellow"

        rprint(f"[bold]{story['id']}[/bold]: [{cat_color}][{cat}][/{cat_color}] [cyan][{topic_tags}][/cyan]" +
               (f" [magenta][{format_tag}][/magenta]" if format_tag else ""))
        rprint(f"  {story['title'][:70]}{'...' if len(story['title']) > 70 else ''}")
        rprint(f"  [dim]{story['url']}[/dim]")
        rprint()
