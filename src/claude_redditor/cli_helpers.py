"""CLI helper functions for reddit-analyzer commands."""

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from typing import Dict

from .config import Settings

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
