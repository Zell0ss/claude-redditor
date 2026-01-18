"""
CLI interface for Reddit Signal/Noise Analyzer.

Organized following Typer best practices:
https://typer.tiangolo.com/tutorial/one-file-per-command/

Structure:
- scan.py: scan, scan-hn, compare commands
- digest_cmd.py: digest command
- bookmark.py: bookmark subcommands (show, add, list, done, status)
- db.py: init-db, history, cache-stats commands
- info.py: config, version commands
- helpers.py: Output formatting and common operations
"""

import typer

from . import scan
from . import digest_cmd
from . import bookmark
from . import db
from . import info

# Main application
app = typer.Typer(
    name="reddit-analyzer",
    help="Analyze Reddit posts and classify them as signal vs noise using Claude AI",
    add_completion=False,
)

# Add scan commands at top level (scan, compare, scan-hn)
app.add_typer(scan.app, name="")  # Empty name = top level commands

# Add digest command at top level
app.add_typer(digest_cmd.app, name="")

# Add bookmark as subcommand group
app.add_typer(bookmark.app, name="bookmark")

# Add database commands at top level
app.add_typer(db.app, name="")

# Add info commands at top level
app.add_typer(info.app, name="")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
