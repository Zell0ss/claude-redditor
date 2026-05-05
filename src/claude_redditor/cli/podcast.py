"""Podcast pipeline commands."""

import json
import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone
from datetime import date as date_type
from pathlib import Path
from typing import Optional

import anthropic
import httpx
import typer
from rich import print as rprint
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..config import settings
from .podcast_helpers import (
    call_and_parse,
    call_deepgram_tts,
    estimate_cost,
    extract_ordered_turns,
    find_dialog,
    find_digest,
    load_podcast_config,
    load_prompt,
)

app = typer.Typer(name="podcast", help="Podcast pipeline commands")
logger = logging.getLogger("clauderedditor")

_LOG_DIR = Path("logs") / "podcast"

VOICE_MAP = {
    "javi": "aura-2-alvaro-es",
    "marta": "aura-2-diana-es",
}


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


def _validate_intro_outro(data: dict) -> list[str]:
    errors = []
    for section in ("intro", "outro"):
        if section not in data:
            errors.append(f"Missing key: '{section}'")
            continue
        turns = data[section].get("turns")
        if not turns:
            errors.append(f"'{section}.turns' is empty or missing")
            continue
        bad = [t.get("speaker") for t in turns if t.get("speaker") not in ("javi", "marta")]
        if bad:
            errors.append(f"Invalid speakers in '{section}': {bad}")
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

    # Intro/outro generation (Etapa 3)
    intro_data: dict | None = None
    outro_data: dict | None = None

    if blocks_arg.strip() == "all":
        rprint("\n[cyan]  Generating intro and outro...[/cyan]")
        intro_outro_cfg = podcast_cfg.get("intro_outro", {})
        io_model = intro_outro_cfg.get("model", "claude-sonnet-4-6")
        io_temperature = float(intro_outro_cfg.get("temperature", 0.7))
        io_max_tokens = int(intro_outro_cfg.get("max_tokens", 4000))
        io_prompt_file = intro_outro_cfg.get("prompt_file", "prompts/podcast_intro_outro.md")

        try:
            io_system_prompt = load_prompt(project, io_prompt_file)
        except FileNotFoundError as exc:
            rprint(f"[yellow]⚠ Intro/outro prompt not found: {exc} — skipping.[/yellow]")
            io_system_prompt = None

        if io_system_prompt:
            intro_outro_input = {
                "episode_title": episode.get("episode_title", ""),
                "episode_thesis": episode.get("episode_thesis", ""),
                "cold_open_hook": episode.get("cold_open_hook", ""),
                "closing_themes": episode.get("closing_themes", []),
                "block_summaries": [b["block_summary"] for b in processed_blocks],
            }
            t_io = time.monotonic()
            try:
                io_result, io_usage, io_msg_id = call_and_parse(
                    client,
                    io_system_prompt,
                    json.dumps(intro_outro_input, ensure_ascii=False),
                    io_model, io_temperature, io_max_tokens,
                    _validate_intro_outro,
                )
                io_elapsed = time.monotonic() - t_io
                io_intro: dict = io_result["intro"]
                io_outro: dict = io_result["outro"]
                intro_data = io_intro
                outro_data = io_outro
                total_input += io_usage.input_tokens
                total_output += io_usage.output_tokens
                _write_log(log_file, {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project": project, "date": date_str, "block": "intro_outro",
                    "model": io_model, "msg_id": io_msg_id,
                    "input_tokens": io_usage.input_tokens,
                    "output_tokens": io_usage.output_tokens,
                    "intro_turns": len(io_intro["turns"]),
                    "outro_turns": len(io_outro["turns"]),
                    "elapsed_s": round(io_elapsed, 2),
                })
                rprint(
                    f"[green]  ✓ Intro ({len(io_intro['turns'])} turns) + "
                    f"Outro ({len(io_outro['turns'])} turns)[/green]"
                )
            except (anthropic.APIError, json.JSONDecodeError, ValueError) as exc:
                logger.error(
                    "podcast_intro_outro failed project=%s date=%s error=%s",
                    project, date_str, exc,
                )
                rprint(f"[yellow]⚠ Intro/outro failed after 3 attempts — writing null: {exc}[/yellow]")
    else:
        rprint("[yellow]⚠ Intro/outro generation skipped: --blocks is not 'all'.[/yellow]")

    elapsed = time.monotonic() - t0
    total_words = sum(
        len(t["text"].split()) for b in processed_blocks for t in b["turns"]
    )
    total_est_min = round(total_words / 150, 1)
    cost_str = estimate_cost(total_input, total_output, model)

    # Assemble dialog
    dialog = {
        "episode_id": digest_path.stem,
        "episode_title": episode.get("episode_title", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intro": intro_data,
        "blocks": processed_blocks,
        "outro": outro_data,
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

    io_status = (
        f"Intro:   {len(intro_data['turns'])} turns | Outro: {len(outro_data['turns'])} turns"
        if intro_data and outro_data
        else "Intro/Outro: not generated"
    )

    _write_log(log_file, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project, "date": date_str, "summary": True,
        "total_input_tokens": total_input, "total_output_tokens": total_output,
        "total_est_min": total_est_min, "elapsed_s": round(elapsed, 2),
        "output": str(dialog_path), "success": True,
        "intro": intro_data is not None, "outro": outro_data is not None,
    })
    logger.info(
        "podcast_script success project=%s date=%s blocks=%d intro=%s tokens=%d+%d",
        project, date_str, len(processed_blocks),
        intro_data is not None, total_input, total_output,
    )

    rprint(per_block_table)
    rprint(Panel(
        f"[green]✓ Dialog saved[/green]\n\n"
        f"File:    {dialog_path}\n"
        f"Blocks:  {len(processed_blocks)} | ~{total_est_min} min estimated\n"
        f"{io_status}\n"
        f"Tokens:  {cost_str}\n"
        f"Time:    {elapsed:.1f}s",
        title="[bold green]podcast script — done[/bold green]",
        expand=False,
    ))


@app.command("audio")
def audio(
    project: str = typer.Option(..., "--project", "-p", help="Project name (e.g. 'claudeia')"),
    date: Optional[str] = typer.Option(None, "--date", help="Digest date YYYY-MM-DD (default: today)"),
    digest_id: Optional[str] = typer.Option(None, "--digest-id", help="Sequence ID e.g. '01' if multiple episodes per day"),
    force: bool = typer.Option(False, "--force", help="Overwrite output if it already exists"),
    speed: Optional[float] = typer.Option(None, "--speed", help="TTS speed override (0.5–1.5, default from config)"),
):
    """
    Run the Audio stage: read dialog.json → Deepgram TTS per turn → MP3 via ffmpeg.

    Generates outputs/podcast/{digest_stem}_audio.mp3.
    Requires DEEPGRAM_API_KEY in .env and ffmpeg installed.

    \\b
    Examples:

        reddit-analyzer podcast audio --project claudeia

        reddit-analyzer podcast audio --project claudeia --date 2026-04-27

        reddit-analyzer podcast audio --project claudeia --date 2026-04-27 --digest-id 01
    """
    date_str = date or date_type.today().isoformat()

    # Load config for audio section
    try:
        podcast_cfg = load_podcast_config(project)
    except (FileNotFoundError, ValueError) as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)
    audio_cfg = podcast_cfg.get("audio", {})
    effective_speed = speed if speed is not None else float(audio_cfg.get("speed", 1.0))

    # Preflight checks — fail before spending any credit
    if not shutil.which("ffmpeg"):
        rprint("[red]✗ ffmpeg not found. Install ffmpeg before running this command.[/red]")
        raise typer.Exit(1)

    if not settings.deepgram_api_key:
        rprint("[red]✗ DEEPGRAM_API_KEY not set. Add it to .env.[/red]")
        raise typer.Exit(1)

    # Find dialog.json
    try:
        dialog_path = find_dialog(project, date_str, digest_id)
    except FileNotFoundError as exc:
        rprint(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    # Derive output path: claudeia_2026-04-27_01_dialog.json → _audio.mp3
    output_stem = dialog_path.stem.replace("_dialog", "")
    output_path = dialog_path.parent / f"{output_stem}_audio.mp3"

    if output_path.exists() and not force:
        rprint(f"[red]✗ Audio already exists: {output_path}[/red]")
        rprint("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    # Load dialog and extract turns
    dialog = json.loads(dialog_path.read_text(encoding="utf-8"))
    turns = extract_ordered_turns(dialog)
    if not turns:
        rprint(f"[red]✗ dialog.json has no turns: {dialog_path}[/red]")
        raise typer.Exit(1)

    total_chars = sum(len(t.get("text", "")) for t in turns)
    est_seconds = total_chars / 15
    est_min = int(est_seconds // 60)
    est_sec = int(est_seconds % 60)

    rprint(f"\n[bold cyan]Podcast Audio — {project} / {date_str}[/bold cyan]")
    rprint(f"[dim]Dialog: {dialog_path.name} | {len(turns)} turns | ~{est_min}m {est_sec}s estimated[/dim]")
    rprint(f"[dim]Speed:  {effective_speed}x | Output: {output_path}[/dim]")
    rprint()

    tmp_files: list[Path] = []
    t0 = time.monotonic()

    try:
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TextColumn("[dim]{task.fields[info]}[/dim]"),
        ) as progress:
            task_id = progress.add_task("Generating audio...", total=len(turns), info="")

            for idx, turn in enumerate(turns):
                speaker = turn.get("speaker", "javi")
                text = turn.get("text", "")
                voice = VOICE_MAP.get(speaker, VOICE_MAP["javi"])
                preview = text[:40].replace("\n", " ")
                progress.update(task_id, info=f"({speaker}) {preview}…")

                audio_bytes = b""
                for attempt in range(1, 3):
                    try:
                        audio_bytes = call_deepgram_tts(text, voice, settings.deepgram_api_key, effective_speed)
                        break
                    except httpx.HTTPError as exc:
                        if attempt == 2:
                            raise RuntimeError(
                                f"Turn {idx} failed after 2 attempts "
                                f"[{speaker}] \"{text[:50]}\": {exc}"
                            ) from exc
                        time.sleep(2)

                tmp_path = Path(f"/tmp/clauderedditor_turn_{idx:04d}.mp3")
                tmp_path.write_bytes(audio_bytes)
                tmp_files.append(tmp_path)
                progress.advance(task_id)

        # Concatenate
        rprint("[cyan]  Concatenating with ffmpeg...[/cyan]")
        concat_txt = dialog_path.parent / "concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.absolute()}'" for p in tmp_files),
            encoding="utf-8",
        )
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(concat_txt), "-c", "copy", str(output_path)],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace")[:300]
            raise RuntimeError(f"ffmpeg failed: {stderr}") from exc
        finally:
            concat_txt.unlink(missing_ok=True)

    except RuntimeError as exc:
        rprint(f"\n[red]✗ {exc}[/red]")
        raise typer.Exit(1)
    finally:
        for tmp in tmp_files:
            tmp.unlink(missing_ok=True)

    elapsed = time.monotonic() - t0
    size_mb = output_path.stat().st_size / (1024 * 1024)

    logger.info(
        "podcast_audio success project=%s date=%s turns=%d size_mb=%.1f",
        project, date_str, len(turns), size_mb,
    )

    rprint(Panel(
        f"[green]✓ Audio saved[/green]\n\n"
        f"File:    {output_path}\n"
        f"Turns:   {len(turns)} | ~{est_min}m {est_sec}s estimated\n"
        f"Size:    {size_mb:.1f} MB\n"
        f"Time:    {elapsed:.1f}s",
        title="[bold green]podcast audio — done[/bold green]",
        expand=False,
    ))
