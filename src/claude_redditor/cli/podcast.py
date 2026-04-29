"""Podcast pipeline commands."""

import json
import logging
import time
from datetime import datetime, timezone
from datetime import date as date_type
from pathlib import Path
from typing import Optional

import anthropic
import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from ..config import settings
from .podcast_helpers import (
    call_and_parse,
    estimate_cost,
    find_digest,
    load_podcast_config,
    load_prompt,
)

app = typer.Typer(name="podcast", help="Podcast pipeline commands")
logger = logging.getLogger("clauderedditor")

_LOG_DIR = Path("logs") / "podcast"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_episode(data: dict) -> list[str]:
    missing = sorted({"episode_title", "blocks", "discarded"} - set(data.keys()))
    return [f"Missing keys: {missing}"] if missing else []


def _validate_block(data: dict) -> list[str]:
    missing = sorted({"turns", "block_summary"} - set(data.keys()))
    if missing:
        return [f"Missing keys: {missing}"]
    errors = []
    if not data["turns"]:
        errors.append("'turns' is empty")
    if not data.get("block_summary"):
        errors.append("'block_summary' is empty")
    bad_speakers = [
        t.get("speaker") for t in data["turns"]
        if t.get("speaker") not in ("javi", "marta")
    ]
    if bad_speakers:
        errors.append(f"Invalid speakers: {bad_speakers}")
    return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_log(log_file: Path, entry: dict) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _parse_blocks_arg(blocks_arg: str, total: int) -> list[int]:
    """Parse --blocks value to 0-indexed list. 'all' → [0,1,...], '1,3' → [0,2]."""
    if blocks_arg.strip() == "all":
        return list(range(total))
    try:
        indices = [int(x.strip()) - 1 for x in blocks_arg.split(",")]
    except ValueError:
        raise ValueError(
            f"Invalid --blocks value: '{blocks_arg}'. Use 'all' or numbers like '1,3'."
        )
    for idx in indices:
        if idx < 0 or idx >= total:
            raise ValueError(
                f"Block {idx + 1} is out of range (episode has {total} blocks)."
            )
    return indices


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

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

    try:
        podcast_cfg = load_podcast_config(project)
    except (FileNotFoundError, ValueError) as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    editor_cfg = podcast_cfg.get("editor", {})
    model = editor_cfg.get("model", "claude-sonnet-4-6")
    temperature = float(editor_cfg.get("temperature", 0.4))
    max_tokens = int(editor_cfg.get("max_tokens", 8000))
    prompt_file = editor_cfg.get("prompt_file", "prompts/podcast_editor.md")

    try:
        digest_path = find_digest(project, date_str)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    output_dir = settings.output_dir / "podcast"
    output_path = output_dir / f"{digest_path.stem}_episode.json"

    if not dry_run and output_path.exists() and not force:
        rprint(f"[red]✗ Episode plan already exists for this date: {output_path}[/red]")
        rprint("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    try:
        system_prompt = load_prompt(project, prompt_file)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    digest_data = json.loads(digest_path.read_text(encoding="utf-8"))
    story_count = len(digest_data.get("stories", []))

    rprint(f"\n[bold cyan]Podcast Editor — {project} / {date_str}[/bold cyan]")
    rprint(f"[dim]Digest: {digest_path.name} ({story_count} stories)[/dim]")
    rprint(f"[dim]Model:  {model}[/dim]")
    if dry_run:
        rprint(f"[dim]Output: {output_path} (dry run — will not be saved)[/dim]")
    rprint()

    rprint("[cyan]Calling Claude editor...[/cyan]")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        episode, usage, msg_id = call_and_parse(
            client, system_prompt,
            json.dumps(digest_data, ensure_ascii=False),
            model, temperature, max_tokens,
            _validate_episode,
        )
    except (anthropic.APIError, json.JSONDecodeError, ValueError) as exc:
        logger.error("podcast_edit failed project=%s date=%s error=%s", project, date_str, exc)
        rprint(f"\n[red]✗ Failed after 3 attempts: {exc}[/red]")
        raise typer.Exit(1)

    elapsed = time.monotonic() - t0
    cost_str = estimate_cost(usage.input_tokens, usage.output_tokens, model)
    blocks = episode.get("blocks", [])
    discarded = episode.get("discarded", [])

    if dry_run:
        rprint(Panel(
            json.dumps(episode, indent=2, ensure_ascii=False),
            title="[cyan]Episode plan (dry run — not saved)[/cyan]",
            expand=False,
        ))
        rprint(f"[dim]Tokens: {cost_str} | {elapsed:.1f}s[/dim]")
        raise typer.Exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(episode, indent=2, ensure_ascii=False), encoding="utf-8")

    _write_log(
        _LOG_DIR / f"edit_{date_str}.log",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project, "date": date_str,
            "digest": digest_path.name, "model": model, "msg_id": msg_id,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "elapsed_s": round(elapsed, 2),
            "blocks": len(blocks), "discarded": len(discarded),
            "output": str(output_path), "success": True,
        },
    )
    logger.info(
        "podcast_edit success project=%s date=%s blocks=%d tokens=%d+%d",
        project, date_str, len(blocks), usage.input_tokens, usage.output_tokens,
    )

    table = Table(title=f"[bold]{episode.get('episode_title', '')}[/bold]", show_header=True)
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


@app.command("script")
def script(
    project: str = typer.Option(..., "--project", "-p", help="Project name (e.g. 'claudeia')"),
    date: Optional[str] = typer.Option(None, "--date", help="Digest date YYYY-MM-DD (default: today)"),
    digest_id: Optional[str] = typer.Option(None, "--digest-id", help="Digest sequence ID (e.g. '01')"),
    force: bool = typer.Option(False, "--force", help="Overwrite output if it already exists"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run everything but don't save"),
    blocks_arg: str = typer.Option("all", "--blocks", help="Blocks to process: 'all' or '1,3'"),
):
    """
    Run the Script stage: read episode plan → call Claude per block → save dialog.

    Generates the full dialogue block by block and writes
    outputs/podcast/{digest_stem}_dialog.json.

    previous_blocks_summary is accumulated within the run only.
    Use --blocks to regenerate a subset; earlier-block context won't be available.

    \\b
    Examples:

        reddit-analyzer podcast script --project claudeia

        reddit-analyzer podcast script --project claudeia --date 2026-04-24

        reddit-analyzer podcast script --project claudeia --blocks 2,3 --force
    """
    date_str = date or date_type.today().isoformat()
    t0 = time.monotonic()

    # Load config
    try:
        podcast_cfg = load_podcast_config(project)
    except (FileNotFoundError, ValueError) as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    script_cfg = podcast_cfg.get("script", {})
    model = script_cfg.get("model", "claude-sonnet-4-6")
    temperature = float(script_cfg.get("temperature", 0.7))
    max_tokens = int(script_cfg.get("max_tokens", 8000))
    prompt_file = script_cfg.get("prompt_file", "prompts/podcast_script.md")

    # Find digest and derive all paths from its stem
    try:
        digest_path = find_digest(project, date_str, digest_id)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    podcast_dir = settings.output_dir / "podcast"
    episode_path = podcast_dir / f"{digest_path.stem}_episode.json"
    dialog_path = podcast_dir / f"{digest_path.stem}_dialog.json"

    if not episode_path.exists():
        rprint(f"[red]✗ Episode plan not found: {episode_path}[/red]")
        rprint(f"[dim]Run 'podcast edit --project {project}' first.[/dim]")
        raise typer.Exit(1)

    if not dry_run and dialog_path.exists() and not force:
        rprint(f"[red]✗ Dialog already exists: {dialog_path}[/red]")
        rprint("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    # Load prompt
    try:
        system_prompt = load_prompt(project, prompt_file)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    # Load episode plan + digest stories
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    digest_data = json.loads(digest_path.read_text(encoding="utf-8"))
    stories_by_id = {s["id"]: s for s in digest_data.get("stories", [])}

    all_blocks = episode.get("blocks", [])
    if not all_blocks:
        rprint(f"[red]✗ Episode plan has no blocks: {episode_path}[/red]")
        raise typer.Exit(1)

    # Parse --blocks
    try:
        block_indices = _parse_blocks_arg(blocks_arg, len(all_blocks))
    except ValueError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    rprint(f"\n[bold cyan]Podcast Script — {project} / {date_str}[/bold cyan]")
    rprint(f"[dim]Episode: {episode_path.name} | {len(block_indices)}/{len(all_blocks)} blocks[/dim]")
    rprint(f"[dim]Model:   {model}[/dim]")
    if dry_run:
        rprint(f"[dim]Output:  {dialog_path} (dry run — will not be saved)[/dim]")
    rprint()

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    log_file = _LOG_DIR / f"script_{date_str}.log"

    previous_summaries: list[str] = []
    processed_blocks: list[dict] = []
    total_input = 0
    total_output = 0

    per_block_table = Table(show_header=True)
    per_block_table.add_column("Block", style="cyan", no_wrap=True)
    per_block_table.add_column("Theme", max_width=38)
    per_block_table.add_column("Turns", justify="center")
    per_block_table.add_column("~Min", justify="right")
    per_block_table.add_column("Tokens", justify="right")

    for idx in block_indices:
        block_plan = all_blocks[idx]
        block_id = block_plan.get("id", f"block_{idx + 1}")
        theme = block_plan.get("theme", "")

        # Build filtered story list for this block
        block_stories = []
        for sid in block_plan.get("story_ids", []):
            s = stories_by_id.get(sid)
            if s:
                block_stories.append({
                    "id": s["id"],
                    "title": s.get("title", ""),
                    "source": s.get("source", ""),
                    "article_body": s.get("article_body", ""),
                    "tier_clusters": s.get("tier_clusters"),
                    "tier_tags": s.get("tier_tags"),
                    "red_flags": s.get("red_flags", []),
                    "score": s.get("score"),
                    "num_comments": s.get("num_comments"),
                })

        block_input = {
            "theme": theme,
            "angle": block_plan.get("angle", ""),
            "tension_axis": block_plan.get("tension_axis", ""),
            "target_minutes": block_plan.get("target_minutes", 5),
            "stories": block_stories,
            "previous_blocks_summary": previous_summaries.copy(),
        }

        rprint(f"[cyan]  Generating {block_id} ({theme[:50]})...[/cyan]")
        t_block = time.monotonic()

        try:
            block_data, usage, msg_id = call_and_parse(
                client,
                system_prompt,
                json.dumps(block_input, ensure_ascii=False),
                model, temperature, max_tokens,
                _validate_block,
            )
        except (anthropic.APIError, json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "podcast_script failed project=%s date=%s block=%s error=%s",
                project, date_str, block_id, exc,
            )
            rprint(f"\n[red]✗ {block_id} failed after 3 attempts — aborting: {exc}[/red]")
            raise typer.Exit(1)

        block_elapsed = time.monotonic() - t_block
        turns = block_data["turns"]
        words = sum(len(t["text"].split()) for t in turns)
        est_min = round(words / 150, 1)

        # Accumulate context for next block
        previous_summaries.append(
            f"Bloque {idx + 1} ({theme}): {block_data['block_summary']}"
        )
        processed_blocks.append({
            "block_id": block_id,
            "block_summary": block_data["block_summary"],
            "turns": turns,
        })
        total_input += usage.input_tokens
        total_output += usage.output_tokens

        _write_log(log_file, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project, "date": date_str, "block": block_id,
            "model": model, "msg_id": msg_id,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "turns": len(turns), "est_min": est_min,
            "elapsed_s": round(block_elapsed, 2),
        })

        per_block_table.add_row(
            block_id,
            theme[:38],
            str(len(turns)),
            str(est_min),
            f"{usage.input_tokens:,}+{usage.output_tokens:,}",
        )

    elapsed = time.monotonic() - t0
    total_words = sum(
        len(t["text"].split()) for b in processed_blocks for t in b["turns"]
    )
    total_est_min = round(total_words / 150, 1)
    cost_str = estimate_cost(total_input, total_output, model)

    # Assemble dialog
    dialog = {
        "episode_id": digest_path.stem,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blocks": processed_blocks,
    }

    if dry_run:
        rprint(per_block_table)
        rprint(Panel(
            json.dumps(dialog, indent=2, ensure_ascii=False),
            title="[cyan]Dialog (dry run — not saved)[/cyan]",
            expand=False,
        ))
        rprint(f"[dim]Total: ~{total_est_min} min | {cost_str} | {elapsed:.1f}s[/dim]")
        raise typer.Exit(0)

    # Save
    podcast_dir.mkdir(parents=True, exist_ok=True)
    dialog_path.write_text(json.dumps(dialog, indent=2, ensure_ascii=False), encoding="utf-8")

    _write_log(log_file, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project, "date": date_str, "summary": True,
        "total_input_tokens": total_input, "total_output_tokens": total_output,
        "total_est_min": total_est_min, "elapsed_s": round(elapsed, 2),
        "output": str(dialog_path), "success": True,
    })
    logger.info(
        "podcast_script success project=%s date=%s blocks=%d tokens=%d+%d",
        project, date_str, len(processed_blocks), total_input, total_output,
    )

    rprint(per_block_table)
    rprint(Panel(
        f"[green]✓ Dialog saved[/green]\n\n"
        f"File:    {dialog_path}\n"
        f"Blocks:  {len(processed_blocks)} | ~{total_est_min} min estimated\n"
        f"Tokens:  {cost_str}\n"
        f"Time:    {elapsed:.1f}s",
        title="[bold green]podcast script — done[/bold green]",
        expand=False,
    ))
