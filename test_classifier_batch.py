"""Test classifier with multiple posts to see different categories."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_redditor.scraper import create_scraper
from claude_redditor.classifier import create_classifier
from rich import print as rprint
from rich.console import Console
from rich.table import Table

console = Console()


def test_batch_classification():
    """Fetch and classify 5 posts from r/ClaudeAI."""

    # Step 1: Fetch posts
    rprint("[cyan]Step 1:[/cyan] Fetching 5 posts from r/ClaudeAI...")
    scraper = create_scraper()
    posts = scraper.fetch_posts("ClaudeAI", limit=5, sort="hot")

    if not posts:
        rprint("[red]✗ No posts found![/red]")
        return

    rprint(f"[green]✓ Fetched {len(posts)} posts[/green]\n")

    # Step 2: Classify all posts
    rprint("[cyan]Step 2:[/cyan] Classifying with Claude Haiku...")

    try:
        classifier = create_classifier()
        classifications = classifier.classify_posts(posts)

        # Create results table
        table = Table(title="Classification Results")
        table.add_column("Title", style="cyan", width=40)
        table.add_column("Category", style="yellow", width=18)
        table.add_column("Conf.", justify="right", style="green", width=6)
        table.add_column("Red Flags", style="red", width=25)

        for post, classification in zip(posts, classifications):
            title = post.title[:37] + "..." if len(post.title) > 40 else post.title
            red_flags = ", ".join(classification.red_flags[:2]) if classification.red_flags else "-"
            if len(classification.red_flags) > 2:
                red_flags += f" +{len(classification.red_flags)-2}"

            table.add_row(
                title,
                classification.category.value,
                f"{classification.confidence:.0%}",
                red_flags,
            )

        console.print(table)

        # Show detailed view of one interesting post
        rprint("\n[cyan]Detailed Classification Example:[/cyan]")
        for post, classification in zip(posts, classifications):
            if classification.red_flags:  # Show first post with red flags
                rprint(f"\n[bold]Post:[/bold] {post.title}")
                rprint(f"[bold]Category:[/bold] {classification.category.value}")
                rprint(f"[bold]Confidence:[/bold] {classification.confidence:.0%}")
                rprint(f"[bold]Red Flags:[/bold] {', '.join(classification.red_flags)}")
                rprint(f"[bold]Reasoning:[/bold] {classification.reasoning}")
                break

        # Statistics
        categories = {}
        for c in classifications:
            categories[c.category.value] = categories.get(c.category.value, 0) + 1

        rprint("\n[cyan]Category Distribution:[/cyan]")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            rprint(f"  {cat}: {count}")

        rprint(f"\n[green]✓ Batch classification complete![/green]")

    except Exception as e:
        rprint(f"[red]✗ Error during classification: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_batch_classification()
