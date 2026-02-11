from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt

from .config import AppConfig, load_env, require_api_key
from .git_ops import (
    GitRepo,
    clone_to_temp,
    get_commit_log,
    get_staged_diff,
    get_staged_summary,
    is_git_repo,
    validate_remote_repo,
)
from .llm_client import LLMClient
from .scoring import compute_stats, split_commits
from .ui import render_commit_sections, render_stats, render_suggestion

app = typer.Typer(add_completion=False, help="AI commit message critic")
console = Console()


@app.command()
def main(
    analyze: bool = typer.Option(
        False, "--analyze", help="Analyze recent commit messages"
    ),
    write: bool = typer.Option(
        False, "--write", help="Suggest a commit message for staged changes"
    ),
    url: Optional[str] = typer.Option(
        None, "--url", help="Analyze a remote repository"
    ),
    include_merges: bool = typer.Option(
        False, "--include-merges", help="Include merge commits in analysis"
    ),
    limit: int = typer.Option(
        50, "--limit", min=1, help="Number of commits to analyze"
    ),
    model: str = typer.Option(
        "gpt-4.1-mini", "--model", help="LLM model to use"
    ),
) -> None:
    if analyze and write:
        console.print(
            "[red]Error:[/red] Please choose exactly one mode: --analyze or --write."
        )
        raise typer.Exit(code=2)

    if not analyze and not write:
        console.print("[red]Error:[/red] Please choose a mode: --analyze or --write.")
        raise typer.Exit(code=2)

    load_env()

    cfg = AppConfig(model=model)

    try:
        if analyze:
            run_analysis(cfg, url=url, limit=limit, include_merges=include_merges)
            return

        if write:
            run_write(cfg)
            return
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    except ValidationError:
        console.print(
            "[red]Error:[/red] The AI returned an unexpected response format. "
            "Please try again."
        )
        raise typer.Exit(code=1)
    except Exception:
        console.print(
            "[red]Error:[/red] Unexpected failure. Please try again."
        )
        raise typer.Exit(code=1)


def run_analysis(
    cfg: AppConfig, url: Optional[str], limit: int, include_merges: bool
) -> None:
    console.print(f"Analyzing last {limit} commits...")

    if url:
        with console.status("Validating remote repository URL..."):
            validate_remote_repo(url)
        require_api_key()
        with console.status("Cloning remote repository..."):
            with clone_to_temp(url) as repo_path:
                repo = GitRepo(Path(repo_path))
                _run_analysis_on_repo(cfg, repo, limit, include_merges)
    else:
        repo = GitRepo(Path.cwd())
        if not is_git_repo(repo):
            raise RuntimeError(
                "Please run inside a git repository, or use --url to analyze a remote repo."
            )
        require_api_key()
        _run_analysis_on_repo(cfg, repo, limit, include_merges)


def _run_analysis_on_repo(
    cfg: AppConfig, repo: GitRepo, limit: int, include_merges: bool
) -> None:
    commits = get_commit_log(repo, limit=limit, include_merges=include_merges)
    if not commits:
        console.print(
            "[yellow]No commits found. Please add at least one commit to analyze.[/yellow]"
        )
        return

    client = LLMClient(cfg)
    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    ]
    with Progress(*progress_columns, console=console) as progress:
        task = progress.add_task("Analyzing commits...", total=1)
        critique_data = client.critique_commits(commits)
        progress.update(task, advance=1)

    if len(critique_data.critiques) != len(commits):
        raise RuntimeError(
            "The AI returned an incomplete analysis. "
            f"Expected {len(commits)} critiques, got {len(critique_data.critiques)}. "
            "Please try again."
        )
    expected_ids = {c.sha for c in commits}
    returned_ids = {c.id for c in critique_data.critiques}
    if returned_ids != expected_ids:
        raise RuntimeError(
            "The AI returned mismatched commit ids in analysis output. "
            "Please try again."
        )

    needs_work, well_written = split_commits(critique_data.critiques)
    stats = compute_stats(critique_data.critiques)

    needs_work_sorted = sorted(needs_work, key=lambda c: c.score)[:5]
    well_written_sorted = sorted(
        well_written, key=lambda c: c.score, reverse=True
    )[:5]

    render_commit_sections(
        console,
        needs_work_sorted,
        well_written_sorted,
        needs_work_total=len(needs_work),
        well_written_total=len(well_written),
    )
    render_stats(console, stats)


def run_write(cfg: AppConfig) -> None:
    require_api_key()
    repo = GitRepo(Path.cwd())
    if not is_git_repo(repo):
        raise RuntimeError(
            "Please run inside a git repository to analyze staged changes."
        )
    diff = get_staged_diff(repo)
    if not diff:
        console.print(
            "[yellow]No staged changes found. Please stage files before running --write.[/yellow]"
        )
        return

    summary = get_staged_summary(repo)
    console.print(
        f"Analyzing staged changes... ({summary.files_changed} files changed, "
        f"+{summary.insertions} -{summary.deletions} lines)"
    )

    client = LLMClient(cfg)
    streamed_text = ""
    with Live(Panel.fit("Drafting commit message..."), console=console, refresh_per_second=12) as live:
        for delta in client.suggest_commit_stream(diff=diff, summary=summary):
            streamed_text += delta
            live.update(Panel.fit(streamed_text or "Drafting commit message..."))

    suggestion = client.parse_suggestion_text(streamed_text)
    render_suggestion(console, suggestion)

    user_input = Prompt.ask("Press Enter to accept, or type your own message", default="")
    final_message = suggestion.full_message if user_input.strip() == "" else user_input

    console.print("\n[bold]Commit Message (copy/paste):[/bold]")
    console.print(final_message)


if __name__ == "__main__":
    main()
