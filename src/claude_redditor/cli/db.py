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
