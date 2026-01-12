"""Report generation and output formatting using Rich."""

import json
from pathlib import Path
from typing import List
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box

from .core.models import AnalysisReport
from .core.enums import CategoryEnum
from .config import settings


class ReportRenderer:
    """Renders analysis reports to terminal and exports to files."""

    def __init__(self):
        """Initialize renderer with Rich console."""
        self.console = Console()

    def render_terminal(self, report: AnalysisReport, show_details: bool = True) -> None:
        """
        Render analysis report to terminal using Rich.

        Args:
            report: AnalysisReport to render
            show_details: Show detailed tables and lists
        """
        # Header
        self._render_header(report)

        # Main metrics
        self._render_metrics_summary(report)

        if show_details:
            # Category distribution
            self._render_category_table(report)

            # Red flags
            if report.red_flags_distribution:
                self._render_red_flags_table(report)

            # Top posts
            if report.top_signal:
                self._render_top_posts(report.top_signal, "Top Signal Posts", "green")

            if report.top_noise:
                self._render_top_posts(report.top_noise, "Top Noise Posts", "red")

        # Add unrelated summary if applicable
        if report.unrelated_count > 0:
            from rich import print as rprint
            rprint()  # Blank line before
            rprint(
                f"[dim]🔍 Unrelated:[/dim] [dim]{report.unrelated_count} "
                f"post{'s' if report.unrelated_count != 1 else ''} filtered (off-topic)[/dim]"
            )

    def render_comparison(self, reports: List[AnalysisReport]) -> None:
        """
        Render comparison of multiple subreddit reports.

        Args:
            reports: List of AnalysisReport objects to compare
        """
        table = Table(
            title="Subreddit Comparison",
            box=box.ROUNDED,
            show_header=True,
        )

        table.add_column("Subreddit", style="cyan", width=20)
        table.add_column("Posts", justify="right", style="white")
        table.add_column("Signal %", justify="right", style="green")
        table.add_column("Grade", justify="center", style="yellow")
        table.add_column("Red Flags", justify="right", style="red")

        for report in sorted(reports, key=lambda r: r.signal_ratio, reverse=True):
            grade = self._calculate_health_grade(report.signal_ratio)
            red_flags_count = sum(report.red_flags_distribution.values())

            # Color signal ratio based on value
            signal_color = "green" if report.signal_ratio >= 0.6 else "yellow" if report.signal_ratio >= 0.4 else "red"

            table.add_row(
                f"r/{report.subreddit}",
                str(report.total_posts),
                f"[{signal_color}]{report.signal_ratio:.1%}[/{signal_color}]",
                grade,
                str(red_flags_count) if red_flags_count > 0 else "-",
            )

        self.console.print(table)

    def export_json(self, report: AnalysisReport, output_path: Path = None) -> Path:
        """
        Export report to JSON file.

        Args:
            report: AnalysisReport to export
            output_path: Optional custom path (default: outputs/reports/)

        Returns:
            Path to exported file
        """
        if output_path is None:
            settings.ensure_directories()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = settings.reports_dir / f"{report.subreddit}_{timestamp}.json"

        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        return output_path

    def _render_header(self, report: AnalysisReport) -> None:
        """Render report header."""
        grade = self._calculate_health_grade(report.signal_ratio)
        grade_color = "green" if grade in ["A+", "A"] else "yellow" if grade in ["B", "C"] else "red"

        header_text = f"""[bold cyan]Subreddit:[/bold cyan] r/{report.subreddit}
[bold cyan]Period:[/bold cyan] {report.period}
[bold cyan]Total Posts Analyzed:[/bold cyan] {report.total_posts}
[bold cyan]Health Grade:[/bold cyan] [{grade_color}]{grade}[/{grade_color}]"""

        self.console.print(Panel(header_text, title="📊 Analysis Report", border_style="blue", expand=False))
        self.console.print()

    def _render_metrics_summary(self, report: AnalysisReport) -> None:
        """Render key metrics summary."""
        signal_categories = CategoryEnum.signal_categories()
        noise_categories = CategoryEnum.noise_categories()

        signal_count = sum(
            count for cat, count in report.category_counts.items()
            if CategoryEnum(cat) in signal_categories
        )

        noise_count = sum(
            count for cat, count in report.category_counts.items()
            if CategoryEnum(cat) in noise_categories
        )

        meta_count = sum(
            count for cat, count in report.category_counts.items()
            if cat in [CategoryEnum.COMMUNITY.value, CategoryEnum.MEME.value]
        )

        # Signal ratio bar
        signal_pct = report.signal_ratio * 100
        bar_length = 30
        filled = int((signal_pct / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        color = "green" if report.signal_ratio >= 0.6 else "yellow" if report.signal_ratio >= 0.4 else "red"

        metrics_text = f"""[bold]Signal Ratio:[/bold] [{color}]{report.signal_ratio:.1%}[/{color}]
[{color}]{bar}[/{color}]

[bold green]Signal Posts:[/bold green] {signal_count} ({signal_count/report.total_posts*100:.1f}%)
[bold red]Noise Posts:[/bold red] {noise_count} ({noise_count/report.total_posts*100:.1f}%)
[bold yellow]Meta Posts:[/bold yellow] {meta_count} ({meta_count/report.total_posts*100:.1f}%)"""

        self.console.print(Panel(metrics_text, title="Key Metrics", border_style=color, expand=False))
        self.console.print()

    def _render_category_table(self, report: AnalysisReport) -> None:
        """Render category distribution table."""
        table = Table(title="Category Distribution", box=box.ROUNDED)
        table.add_column("Category", style="yellow")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right", style="white")
        table.add_column("Percentage", justify="right", style="green")

        # Filter out UNRELATED from table
        visible_categories = {
            cat: count for cat, count in report.category_counts.items()
            if cat != CategoryEnum.UNRELATED.value
        }

        for category, count in sorted(visible_categories.items(), key=lambda x: x[1], reverse=True):
            cat_enum = CategoryEnum(category)
            percentage = (count / report.total_posts) * 100

            # Determine type
            if CategoryEnum.is_signal(cat_enum):
                cat_type = "[green]Signal[/green]"
            elif cat_enum in CategoryEnum.noise_categories():
                cat_type = "[red]Noise[/red]"
            else:
                cat_type = "[yellow]Meta/Other[/yellow]"

            table.add_row(category, cat_type, str(count), f"{percentage:.1f}%")

        self.console.print(table)
        self.console.print()

    def _render_red_flags_table(self, report: AnalysisReport) -> None:
        """Render red flags distribution table."""
        table = Table(title="🚩 Red Flags Detected", box=box.ROUNDED)
        table.add_column("Red Flag", style="red")
        table.add_column("Count", justify="right", style="yellow")
        table.add_column("Posts Affected", justify="right", style="white")

        for flag, count in sorted(report.red_flags_distribution.items(), key=lambda x: x[1], reverse=True):
            pct = (count / report.total_posts) * 100
            table.add_row(flag.replace("_", " ").title(), str(count), f"{pct:.1f}%")

        self.console.print(table)
        self.console.print()

    def _render_top_posts(self, posts: List, title: str, color: str) -> None:
        """Render top posts list."""
        if not posts:
            return

        table = Table(title=title, box=box.ROUNDED, show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="white", width=50)
        table.add_column("Category", style="yellow", width=18)
        table.add_column("Conf.", justify="right", style=color, width=6)

        for i, post in enumerate(posts[:5], 1):
            title_text = post.title[:47] + "..." if len(post.title) > 50 else post.title
            table.add_row(
                str(i),
                title_text,
                post.category.value,
                f"{post.confidence:.0%}"
            )

        self.console.print(table)
        self.console.print()

    def _calculate_health_grade(self, signal_ratio: float) -> str:
        """Calculate health grade from signal ratio."""
        if signal_ratio >= 0.8:
            return "A+"
        elif signal_ratio >= 0.7:
            return "A"
        elif signal_ratio >= 0.6:
            return "B"
        elif signal_ratio >= 0.5:
            return "C"
        elif signal_ratio >= 0.4:
            return "D"
        else:
            return "F"


def create_reporter() -> ReportRenderer:
    """Factory function to create a ReportRenderer instance."""
    return ReportRenderer()
