"""Podcast generation command using Google NotebookLM."""

import asyncio
import re
import typer
from pathlib import Path
from datetime import date as date_type
from typing import Optional
from rich import print as rprint
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()

DEFAULT_INSTRUCTIONS = (
    "Genera un podcast resumen diario de noticias de inteligencia artificial. "
    "Tono: informativo pero accesible. "
    "Audiencia: profesionales tech hispanohablantes. "
    "Presenta los temas más importantes del día de forma clara y entretenida."
)


def _find_digest(project: str, date_str: str, outputs_root: Path) -> Path:
    """Find the latest digest file for a given project and date."""
    digests_dir = outputs_root / "digests"
    pattern = f"digest_{project}_{date_str}_*.md"
    matches = sorted(digests_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No se encontró digest para {project}/{date_str}. "
            f"¿Has ejecutado 'digest --project {project}' primero?"
        )
    return matches[-1]  # Latest one


async def _generate_podcast(
    digest_path: Path,
    output_path: Path,
    notebook_title: str,
    instructions: str,
    cleanup: bool,
) -> str:
    """Core async logic: upload digest to NotebookLM, generate audio, download."""
    try:
        from notebooklm import NotebookLMClient
        from notebooklm.exceptions import AuthError, NotebookLMError
    except ImportError:
        raise RuntimeError(
            "notebooklm-py no está instalado. Ejecuta: pip install notebooklm-py"
        )

    content = digest_path.read_text(encoding="utf-8")
    notebook_id = None

    try:
        async with await NotebookLMClient.from_storage() as client:
            # Step 1: Create notebook
            rprint(f"[cyan]Creando notebook temporal: {notebook_title!r}...[/cyan]")
            nb = await client.notebooks.create(notebook_title)
            notebook_id = nb.id

            # Step 2: Upload digest as text source
            rprint(f"[cyan]Subiendo digest como fuente ({len(content):,} caracteres)...[/cyan]")
            await client.sources.add_text(
                notebook_id,
                "Digest diario",
                content,
                wait=True,
            )

            # Step 3: Generate audio
            rprint("[cyan]Generando audio... (esto puede tardar 2-5 minutos)[/cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("Generando podcast...", total=None)
                status = await client.artifacts.generate_audio(
                    notebook_id,
                    language="es",
                    instructions=instructions,
                )
                await client.artifacts.wait_for_completion(
                    notebook_id, status.task_id, timeout=600.0
                )

            # Step 4: Download MP3
            output_path.parent.mkdir(parents=True, exist_ok=True)
            rprint(f"[cyan]Descargando podcast → {output_path}[/cyan]")
            await client.artifacts.download_audio(notebook_id, str(output_path))

            # Step 5: Cleanup
            if cleanup:
                await client.notebooks.delete(notebook_id)
                notebook_id = None
                rprint("[dim]Notebook temporal borrado[/dim]")

    except AuthError:
        raise RuntimeError(
            "Autenticación de NotebookLM expirada. "
            "Ejecuta 'notebooklm login' en tu máquina local y copia "
            "storage_state.json a ~/.notebooklm/"
        )
    except NotebookLMError as e:
        if notebook_id:
            rprint(f"[yellow]Error durante generación. Notebook ID para cleanup manual: {notebook_id}[/yellow]")
        raise RuntimeError(f"Error de NotebookLM: {e}") from e

    return str(output_path)


@app.command()
def podcast(
    project: str = typer.Option(
        ...,
        "--project", "-p",
        help="Nombre del proyecto (ej: 'claudeia')",
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Fecha del digest YYYY-MM-DD (default: hoy)",
    ),
    cleanup: bool = typer.Option(
        True,
        "--cleanup/--no-cleanup",
        help="Borrar notebook de NotebookLM después de descargar",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Mostrar plan sin ejecutar",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directorio de salida (default: outputs/podcasts)",
    ),
    focus: Optional[str] = typer.Option(
        None,
        "--focus",
        help="Instrucción adicional de enfoque para el audio",
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        help="Path directo al fichero digest .md (alternativa a --date)",
    ),
):
    """
    Genera un podcast a partir de un digest usando Google NotebookLM.

    Sube el digest del día a NotebookLM, genera un Audio Overview
    conversacional en español y descarga el MP3 resultante.

    Examples:

        reddit-analyzer podcast --project claudeia

        reddit-analyzer podcast --project claudeia --date 2026-03-03

        reddit-analyzer podcast --project claudeia --file /data/.../digest_claudeia_2026-03-04_02.md
    """
    outputs_root = Path("outputs")
    resolved_output_dir = output_dir or outputs_root / "podcasts"

    # Resolve digest path and output filename
    if file:
        digest_path = Path(file)
        if not digest_path.exists():
            rprint(f"[red]✗ Fichero no encontrado: {file}[/red]")
            raise typer.Exit(1)
        # Extract date from filename for notebook title
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", digest_path.name)
        date_str = date_match.group() if date_match else "unknown"
        # Mirror input name: digest_claudeia_2026-03-04_02 → podcast_claudeia_2026-03-04_02
        output_stem = digest_path.stem.replace("digest_", "podcast_", 1)
        output_path = resolved_output_dir / f"{output_stem}.mp3"
    else:
        date_str = date or date_type.today().isoformat()
        # Validate project exists (only needed when auto-discovering digest)
        try:
            from ..projects import project_loader
            project_loader.load(project)
        except FileNotFoundError:
            rprint(f"[red]✗ Proyecto '{project}' no encontrado.[/red]")
            rprint("[dim]Usa 'reddit-analyzer config' para ver proyectos disponibles.[/dim]")
            raise typer.Exit(1)
        try:
            digest_path = _find_digest(project, date_str, outputs_root)
        except FileNotFoundError as e:
            rprint(f"[red]✗ {e}[/red]")
            raise typer.Exit(1)
        output_path = resolved_output_dir / f"podcast_{project}_{date_str}.mp3"

    notebook_title = f"Podcast IA - {project} {date_str}"

    # Build instructions
    instructions = DEFAULT_INSTRUCTIONS
    if focus:
        instructions += f" Enfoque especial: {focus}"

    if dry_run:
        rprint(Panel(
            f"[bold]Plan de ejecución[/bold]\n\n"
            f"Digest: {digest_path}\n"
            f"Output: {output_path}\n"
            f"Notebook: {notebook_title!r}\n"
            f"Cleanup: {'Sí' if cleanup else 'No'}\n"
            f"Instrucciones: {instructions[:80]}...",
            title="[cyan]Podcast - Dry Run[/cyan]",
            expand=False,
        ))
        raise typer.Exit(0)

    # Execute
    rprint(f"\n[bold cyan]Generando podcast para {project} ({date_str})[/bold cyan]")
    rprint(f"[dim]Digest: {digest_path}[/dim]\n")

    try:
        asyncio.run(_generate_podcast(
            digest_path=digest_path,
            output_path=output_path,
            notebook_title=notebook_title,
            instructions=instructions,
            cleanup=cleanup,
        ))
    except RuntimeError as e:
        rprint(f"\n[red]✗ {e}[/red]\n")
        raise typer.Exit(1)

    rprint(Panel(
        f"[green]✓ Podcast generado exitosamente[/green]\n\n"
        f"Fecha: {date_str}\n"
        f"Proyecto: {project}\n"
        f"Archivo: {output_path}\n"
        f"Notebook: {'borrado' if cleanup else 'mantenido'}",
        title="[bold green]Podcast listo[/bold green]",
        expand=False,
    ))
    # Print path for N8N to capture
    print(f"\n{output_path}")
