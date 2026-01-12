"""Test classifier with a single post from r/ClaudeAI."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.scraper import create_scraper
from claude_redditor.classifier import create_classifier
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def test_single_post_classification():
    """Fetch a post and classify it with Claude."""

    # Step 1: Fetch a post
    rprint("[cyan]Step 1:[/cyan] Fetching a post from r/ClaudeAI...")
    scraper = create_scraper()
    posts = scraper.fetch_posts("ClaudeAI", limit=1, sort="hot")

    if not posts:
        rprint("[red]✗ No posts found![/red]")
        return

    post = posts[0]

    # Display the post
    post_info = f"""[bold]Title:[/bold] {post.title}
[bold]Author:[/bold] {post.author}
[bold]Subreddit:[/bold] r/{post.subreddit}
[bold]Flair:[/bold] {post.flair or 'None'}
[bold]URL:[/bold] {post.url}

[bold]Selftext Preview:[/bold]
{post.selftext[:300]}{'...' if len(post.selftext) > 300 else ''}"""

    console.print(Panel(post_info, title=f"Post to Classify: {post.id}", border_style="cyan"))

    # Step 2: Classify the post
    rprint("\n[cyan]Step 2:[/cyan] Classifying with Claude Haiku...")

    try:
        classifier = create_classifier()
        classifications = classifier.classify_posts([post])

        if not classifications:
            rprint("[red]✗ No classification returned![/red]")
            return

        classification = classifications[0]

        # Display classification result
        result_text = f"""[bold]Category:[/bold] [yellow]{classification.category.value}[/yellow]
[bold]Confidence:[/bold] {classification.confidence:.2%}
[bold]Red Flags:[/bold] {', '.join(classification.red_flags) if classification.red_flags else 'None'}

[bold]Reasoning:[/bold]
{classification.reasoning}"""

        # Choose border color based on category
        from src.claude_redditor.core.enums import CategoryEnum

        signal_cats = [c.value for c in CategoryEnum.signal_categories()]
        noise_cats = [c.value for c in CategoryEnum.noise_categories()]

        if classification.category.value in signal_cats:
            border_style = "green"
            category_type = "SIGNAL ✓"
        elif classification.category.value in noise_cats:
            border_style = "red"
            category_type = "NOISE ✗"
        elif classification.category.value == "unrelated":
            border_style = "dim"
            category_type = "UNRELATED 🔍"
        else:
            border_style = "yellow"
            category_type = "META/OTHER"

        console.print(Panel(result_text, title=f"Classification Result: {category_type}", border_style=border_style))

        # Summary
        rprint("\n[green]✓ Classification test complete![/green]")
        rprint(f"[cyan]Post ID:[/cyan] {post.id}")
        rprint(f"[cyan]Category:[/cyan] {classification.category.value}")
        rprint(f"[cyan]Is Signal?:[/cyan] {classification.category in classification.category.signal_categories()}")

    except Exception as e:
        rprint(f"[red]✗ Error during classification: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_single_post_classification()
