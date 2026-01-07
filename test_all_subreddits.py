"""Test scraper with all configured subreddits."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.scraper import create_scraper
from claude_redditor.config import settings
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_all_subreddits():
    """Test the Reddit scraper with all configured subreddits."""

    scraper = create_scraper()
    mode_info = scraper.get_mode_info()

    # Show configuration
    subreddit_list = settings.get_subreddit_list()

    config_text = f"""[cyan]Scraper Mode:[/cyan] {mode_info['mode']}
[cyan]Rate Limit:[/cyan] {mode_info['rate_limit']}
[cyan]Authenticated:[/cyan] {mode_info['authenticated']}
[cyan]Target Subreddits:[/cyan] {', '.join(f'r/{s}' for s in subreddit_list)}"""

    console.print(Panel(config_text, title="Configuration", border_style="blue"))

    # Test each subreddit
    for subreddit in subreddit_list:
        rprint(f"\n[yellow]Testing r/{subreddit}...[/yellow]")

        try:
            posts = scraper.fetch_posts(subreddit, limit=5, sort="hot")

            if posts:
                rprint(f"[green]✓ Successfully fetched {len(posts)} posts from r/{subreddit}[/green]")

                # Show titles
                table = Table(title=f"Sample Posts from r/{subreddit}", show_header=True)
                table.add_column("Title", style="cyan", width=60)
                table.add_column("Author", style="magenta", width=20)

                for post in posts:
                    title = post.title[:57] + "..." if len(post.title) > 60 else post.title
                    author = post.author[:17] + "..." if len(post.author) > 20 else post.author
                    table.add_row(title, author)

                console.print(table)
            else:
                rprint(f"[yellow]⚠ No posts fetched from r/{subreddit}[/yellow]")

        except Exception as e:
            rprint(f"[red]✗ Error with r/{subreddit}: {e}[/red]")

    rprint("\n[green]✓ Subreddit testing complete![/green]")
    rprint(f"[cyan]Total subreddits configured:[/cyan] {len(subreddit_list)}")


if __name__ == "__main__":
    test_all_subreddits()
