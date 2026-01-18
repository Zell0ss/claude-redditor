"""Info commands: config, version."""

import typer
from rich import print as rprint

from ..config import settings
from ..projects import project_loader

app = typer.Typer()


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

    # Projects (auto-discovered)
    rprint(f"\n[bold]Configured Projects:[/bold]")
    projects = project_loader.list_projects()
    if projects:
        for project_name in projects:
            proj = project_loader.load(project_name)
            rprint(f"  [cyan]{project_name}[/cyan]: {proj.description}")
            if proj.subreddits:
                rprint(f"    Subreddits: {', '.join(f'r/{s}' for s in proj.subreddits)}")
            if proj.hn_keywords:
                rprint(f"    HN Keywords: {', '.join(proj.hn_keywords)}")
    else:
        rprint(f"  [yellow]No projects found[/yellow]")
        rprint(f"  [dim]Create projects/ directory with project folders[/dim]")

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


@app.command()
def version():
    """Show version information."""
    rprint("\n[bold cyan]Reddit Signal/Noise Analyzer[/bold cyan]")
    rprint("Version: 0.1.0")
    rprint("Powered by Claude AI (Anthropic)")
    rprint("\nGitHub: https://github.com/Zell0ss/claude-redditor\n")
