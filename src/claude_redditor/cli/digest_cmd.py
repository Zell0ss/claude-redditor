"""Digest command for generating daily newsletters."""

import typer
from typing import Optional
from pathlib import Path
from rich import print as rprint
from rich.table import Table

from ..config import settings
from .helpers import console, ensure_mysql_configured

app = typer.Typer()


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
        "both",
        "--format", "-f",
        help="Output format: 'markdown', 'json' (for web), or 'both' (default)"
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
        from ..db.connection import DatabaseConnection
        from ..db.repository import Repository
        from ..digest import DigestGenerator

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

        generator = DigestGenerator(repo, project=project)

        output_paths = []

        if format == 'both':
            # Use generate_both() to ensure same posts in same order for both formats
            md_path, json_path = generator.generate_both(
                project=project,
                limit=limit,
                output_dir=output_dir,
                show_progress=True
            )
            output_paths.append(('markdown', md_path))
            output_paths.append(('json', json_path))
        elif format == 'markdown':
            md_path = generator.generate(
                project=project,
                limit=limit,
                output_dir=output_dir,
                show_progress=True
            )
            output_paths.append(('markdown', md_path))
        elif format == 'json':
            json_path = generator.generate_json(
                project=project,
                limit=limit,
                show_progress=True
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
