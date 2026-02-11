from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import CommitCritique, SuggestionResponse
from .scoring import Stats


def render_commit_sections(
    console: Console,
    needs_work: list[CommitCritique],
    well_written: list[CommitCritique],
    needs_work_total: int,
    well_written_total: int,
) -> None:
    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold]💩 COMMITS THAT NEED WORK[/bold]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not needs_work:
        console.print("[green]No weak commits found.[/green]\n")
    else:
        if needs_work_total > len(needs_work):
            console.print(
                f"[dim]Showing {len(needs_work)} of {needs_work_total} commits.[/dim]"
            )
        for critique in needs_work:
            _render_critique(console, critique, show_issue=True)

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold]💎 WELL-WRITTEN COMMITS[/bold]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not well_written:
        console.print("[yellow]No strong commits found.[/yellow]\n")
    else:
        if well_written_total > len(well_written):
            console.print(
                f"[dim]Showing {len(well_written)} of {well_written_total} commits.[/dim]"
            )
        for critique in well_written:
            _render_critique(console, critique, show_issue=False)


def render_stats(console: Console, stats: Stats) -> None:
    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold]📊 YOUR STATS[/bold]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    table = Table(show_header=False)
    table.add_row("Average score", f"{stats.average_score}/10")
    table.add_row(
        "Vague commits", f"{stats.vague_commits} ({stats.vague_percent}%)"
    )
    table.add_row(
        "One-word commits", f"{stats.one_word_commits} ({stats.one_word_percent}%)"
    )
    console.print(table)


def render_suggestion(console: Console, suggestion: SuggestionResponse) -> None:
    console.print("\nChanges detected:")
    for item in suggestion.summary_bullets:
        console.print(f"- {item}")

    console.print("\nSuggested commit message:")
    panel = Panel.fit(suggestion.full_message)
    console.print(panel)


def _render_critique(
    console: Console, critique: CommitCritique, show_issue: bool
) -> None:
    lines = [
        f"Commit: \"{critique.commit}\"",
        f"Score: {critique.score}/10",
    ]
    if show_issue:
        if critique.issue:
            lines.append(f"Issue: {critique.issue}")
        if critique.better:
            lines.append(f"Better: {critique.better}")
    else:
        if critique.why_good:
            lines.append(f"Why it's good: {critique.why_good}")
    panel = Panel.fit("\n".join(lines))
    console.print(panel)
