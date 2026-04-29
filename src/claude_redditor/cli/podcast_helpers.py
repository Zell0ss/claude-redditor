"""Shared helpers for podcast pipeline commands."""

import json
import time
from pathlib import Path
from typing import Callable

import anthropic
from anthropic.types import TextBlock, Usage
import yaml
from rich import print as rprint

from ..config import settings
from ..projects import project_loader

PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}


def find_digest(project: str, date_str: str, digest_id: str | None = None) -> Path:
    """Find digest JSON for a project and date.

    If digest_id given (e.g. '01'), looks for the exact file.
    Otherwise returns the latest match for that date.
    """
    web_dir = settings.output_dir / "web"
    if digest_id:
        path = web_dir / f"{project}_{date_str}_{digest_id}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Digest not found: {path}. "
                f"Run 'digest --project {project}' first."
            )
        return path
    matches = sorted(web_dir.glob(f"{project}_{date_str}_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No digest found for {project}/{date_str}. "
            f"Run 'digest --project {project}' first."
        )
    return matches[-1]


def load_podcast_config(project: str) -> dict:
    """Load the full podcast section from the project's config.yaml."""
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
        raise ValueError(f"No 'podcast' section in config for project '{project}'.")
    return cfg


def load_prompt(project: str, prompt_file: str) -> str:
    """Load a system prompt from the project's prompts directory."""
    path = project_loader.projects_dir / project / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> str:
    """Return human-readable cost estimate string."""
    pricing = PRICING.get(model)
    if not pricing:
        for key, val in PRICING.items():
            if model.startswith(key):
                pricing = val
                break
    if not pricing:
        return f"{input_tokens:,} in + {output_tokens:,} out (pricing unknown)"
    total = (input_tokens / 1_000_000) * pricing["input"] + \
            (output_tokens / 1_000_000) * pricing["output"]
    return f"~${total:.4f} ({input_tokens:,} in + {output_tokens:,} out)"


def call_and_parse(
    client: anthropic.Anthropic,
    system_prompt: str,
    content: str,
    model: str,
    temperature: float,
    max_tokens: int,
    validate_fn: Callable[[dict], list[str]],
) -> tuple[dict, Usage, str]:
    """Call the API, parse JSON response, validate; retry up to 3 times on any failure.

    validate_fn(data) → list of error strings (empty list = valid).
    Returns (parsed_dict, usage, message_id).
    Retries on: API errors, JSON parse errors, validation failures.
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(1, 4):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            content_block = resp.content[0]
            if not isinstance(content_block, TextBlock):
                raise ValueError(f"Unexpected block type: {type(content_block).__name__}")
            data = json.loads(strip_fences(content_block.text))
            errors = validate_fn(data)
            if errors:
                raise ValueError(f"Validation failed: {errors}")
            return data, resp.usage, resp.id
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
