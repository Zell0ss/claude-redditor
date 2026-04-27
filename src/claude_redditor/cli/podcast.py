"""Podcast pipeline commands."""

import json
import logging
import time
from datetime import datetime, timezone
from datetime import date as date_type
from pathlib import Path
from typing import Optional

import anthropic
from anthropic.types import TextBlock, Usage
import typer
import yaml
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from ..config import settings
from ..projects import project_loader

app = typer.Typer(
    name="podcast",
    help="Podcast pipeline commands",
)

logger = logging.getLogger("clauderedditor")

# Approximate pricing per million tokens
_PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}


def _find_digest(project: str, date_str: str) -> Path:
    """Find the latest digest JSON for a given project and date."""
    web_dir = settings.output_dir / "web"
    matches = sorted(web_dir.glob(f"{project}_{date_str}_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No digest found for {project}/{date_str}. "
            f"Run 'digest --project {project}' first."
        )
    return matches[-1]


def _load_podcast_config(project: str) -> dict:
    """Load podcast section from project config.yaml."""
    config_path = project_loader.projects_dir / project / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Project '{project}' not found. "
            f"Use 'reddit-analyzer config' to list available projects."
        )
    with open(config_path) as f:
        data = yaml.safe_load(f)
    cfg = data.get("podcast")
    if not cfg:
        raise ValueError(
            f"No 'podcast' section in config for project '{project}'."
        )
    return cfg


def _load_prompt(project: str, prompt_file: str) -> str:
    """Load system prompt from project's prompts directory."""
    path = project_loader.projects_dir / project / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Editor prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


def _validate_episode(data: dict) -> list[str]:
    """Return list of missing required top-level keys."""
    return sorted({"episode_title", "blocks", "discarded"} - set(data.keys()))


def _call_and_parse(
    client: anthropic.Anthropic,
    system_prompt: str,
    digest_content: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, Usage, str]:
    """Call API and parse/validate, retrying up to 3 times on any failure.

    Returns (episode_dict, usage, message_id).
    Retries on: API errors, JSON parse errors, missing required keys.
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(1, 4):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": digest_content}],
            )
            block = resp.content[0]
            if not isinstance(block, TextBlock):
                raise ValueError(f"Unexpected response block type: {type(block).__name__}")
            episode = json.loads(_strip_fences(block.text))
            missing = _validate_episode(episode)
            if missing:
                raise ValueError(f"Response missing required keys: {missing}")
            return episode, resp.usage, resp.id
        except (anthropic.APIError, json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            if attempt < 3:
                wait = 2 ** attempt
                rprint(
                    f"[yellow]Attempt {attempt}/3 failed "
                    f"({type(exc).__name__}), retrying in {wait}s: {exc}[/yellow]"
                )
                time.sleep(wait)
    raise last_exc


def _estimate_cost(usage: Usage, model: str) -> str:
    """Return human-readable cost estimate string."""
    pricing = _PRICING.get(model)
    if not pricing:
        for key, val in _PRICING.items():
            if model.startswith(key):
                pricing = val
                break
    if not pricing:
        return f"{usage.input_tokens:,} in + {usage.output_tokens:,} out (pricing unknown)"
    total = (
        (usage.input_tokens / 1_000_000) * pricing["input"]
        + (usage.output_tokens / 1_000_000) * pricing["output"]
    )
    return f"~${total:.4f} ({usage.input_tokens:,} in + {usage.output_tokens:,} out)"


@app.command("edit")
def edit(
    project: str = typer.Option(..., "--project", "-p", help="Project name (e.g. 'claudeia')"),
    date: Optional[str] = typer.Option(None, "--date", help="Digest date YYYY-MM-DD (default: today)"),
    force: bool = typer.Option(False, "--force", help="Overwrite output if it already exists"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run everything but don't save the file"),
):
    """
    Run the Editor stage: read digest JSON → call Claude → save episode plan.

    Reads the day's digest, applies the editor system prompt, and writes
    outputs/podcast/{digest_stem}_episode.json.

    \\b
    Examples:

        reddit-analyzer podcast edit --project claudeia

        reddit-analyzer podcast edit --project claudeia --date 2026-04-24

        reddit-analyzer podcast edit --project claudeia --dry-run
    """
    date_str = date or date_type.today().isoformat()
    t0 = time.monotonic()

    # Load project podcast config
    try:
        podcast_cfg = _load_podcast_config(project)
    except (FileNotFoundError, ValueError) as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    editor_cfg = podcast_cfg.get("editor", {})
    model = editor_cfg.get("model", "claude-sonnet-4-6")
    temperature = float(editor_cfg.get("temperature", 0.4))
    max_tokens = int(editor_cfg.get("max_tokens", 8000))
    prompt_file = editor_cfg.get("prompt_file", "prompts/podcast_editor.md")

    # Find digest
    try:
        digest_path = _find_digest(project, date_str)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    # Output path mirrors digest name
    output_dir = settings.output_dir / "podcast"
    output_path = output_dir / f"{digest_path.stem}_episode.json"

    # Guard: don't overwrite unless --force (irrelevant in dry-run)
    if not dry_run and output_path.exists() and not force:
        rprint(f"[red]✗ Episode plan already exists for this date: {output_path}[/red]")
        rprint("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    # Load prompt
    try:
        system_prompt = _load_prompt(project, prompt_file)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    # Read digest
    digest_data = json.loads(digest_path.read_text(encoding="utf-8"))
    story_count = len(digest_data.get("stories", []))
    digest_str = json.dumps(digest_data, ensure_ascii=False)

    rprint(f"\n[bold cyan]Podcast Editor — {project} / {date_str}[/bold cyan]")
    rprint(f"[dim]Digest: {digest_path.name} ({story_count} stories)[/dim]")
    rprint(f"[dim]Model:  {model}[/dim]")
    if dry_run:
        rprint(f"[dim]Output: {output_path} (dry run — will not be saved)[/dim]")
    rprint()

    # Call Claude
    rprint("[cyan]Calling Claude editor...[/cyan]")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        episode, usage, msg_id = _call_and_parse(
            client, system_prompt, digest_str, model, temperature, max_tokens
        )
    except (anthropic.APIError, json.JSONDecodeError, ValueError) as exc:
        logger.error(
            "podcast_edit failed project=%s date=%s error=%s", project, date_str, exc
        )
        rprint(f"\n[red]✗ Failed after 3 attempts: {exc}[/red]")
        raise typer.Exit(1)

    elapsed = time.monotonic() - t0
    cost_str = _estimate_cost(usage, model)
    blocks = episode.get("blocks", [])
    discarded = episode.get("discarded", [])

    # Dry run: print JSON and exit without saving
    if dry_run:
        rprint(Panel(
            json.dumps(episode, indent=2, ensure_ascii=False),
            title="[cyan]Episode plan (dry run — not saved)[/cyan]",
            expand=False,
        ))
        rprint(f"[dim]Tokens: {cost_str} | {elapsed:.1f}s[/dim]")
        raise typer.Exit(0)

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(episode, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Structured log
    log_dir = Path("logs") / "podcast"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "date": date_str,
        "digest": digest_path.name,
        "model": model,
        "msg_id": msg_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "elapsed_s": round(elapsed, 2),
        "blocks": len(blocks),
        "discarded": len(discarded),
        "output": str(output_path),
        "success": True,
    }
    log_file = log_dir / f"edit_{date_str}.log"
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    logger.info(
        "podcast_edit success project=%s date=%s blocks=%d tokens=%d+%d",
        project, date_str, len(blocks), usage.input_tokens, usage.output_tokens,
    )

    # Summary table
    table = Table(
        title=f"[bold]{episode.get('episode_title', '')}[/bold]",
        show_header=True,
    )
    table.add_column("Block", style="cyan", no_wrap=True)
    table.add_column("Theme")
    table.add_column("Stories", justify="center")
    table.add_column("Min", justify="right")
    for block in blocks:
        table.add_row(
            block.get("id", ""),
            block.get("theme", ""),
            str(len(block.get("story_ids", []))),
            str(block.get("target_minutes", "")),
        )
    rprint(table)

    if discarded:
        disc_summary = ", ".join(
            f"{d['story_id']} [{d.get('reason', '')}]" for d in discarded[:6]
        )
        if len(discarded) > 6:
            disc_summary += f" … +{len(discarded) - 6} more"
        rprint(f"\n[dim]Discarded ({len(discarded)}): {disc_summary}[/dim]")

    rprint(Panel(
        f"[green]✓ Episode plan saved[/green]\n\n"
        f"File:    {output_path}\n"
        f"Blocks:  {len(blocks)} | Discarded: {len(discarded)}\n"
        f"Thesis:  {episode.get('episode_thesis', '')[:80]}\n"
        f"Tokens:  {cost_str}\n"
        f"Time:    {elapsed:.1f}s",
        title="[bold green]podcast edit — done[/bold green]",
        expand=False,
    ))
