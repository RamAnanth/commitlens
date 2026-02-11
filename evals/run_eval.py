from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commit_critic.config import AppConfig, load_env, require_api_key
from commit_critic.git_ops import CommitEntry
from commit_critic.llm_client import LLMClient
from commit_critic.scoring import NEEDS_WORK_THRESHOLD, WELL_WRITTEN_THRESHOLD

SCORE_TOLERANCE = 1


@dataclass(frozen=True)
class EvalCase:
    commit: str
    expected_score: int
    expected_bucket: str
    rationale: str


def score_bucket(score: int) -> str:
    if score < NEEDS_WORK_THRESHOLD:
        return "needs_work"
    if score >= WELL_WRITTEN_THRESHOLD:
        return "well_written"
    return "mid"


def compact_commit(text: str) -> str:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    first = lines[0]
    extra = len(lines) - 1
    if extra > 0:
        return f"{first} (+{extra} lines)"
    return first


def main() -> None:
    load_env()
    require_api_key()

    path = Path(__file__).with_name("commits.json")
    cases_raw = json.loads(path.read_text())
    cases = [EvalCase(**c) for c in cases_raw]

    console = Console()
    repeats = 5
    console.print(
        f"Running eval on {len(cases)} commits using model gpt-4.1-mini (repeats={repeats})..."
    )
    console.print(
        f"Bucket thresholds: needs_work < {NEEDS_WORK_THRESHOLD}, "
        f"mid {NEEDS_WORK_THRESHOLD}-{WELL_WRITTEN_THRESHOLD-1}, "
        f"well_written >= {WELL_WRITTEN_THRESHOLD}"
    )
    console.print(f"Score tolerance: +/- {SCORE_TOLERANCE}")

    client = LLMClient(AppConfig(model="gpt-4.1-mini"))

    table = Table(title="CommitLens Eval")
    table.add_column("Commit", overflow="fold")
    table.add_column("Expected")
    table.add_column("Expected Score")
    table.add_column("Pass %")
    table.add_column("Score μ")
    table.add_column("Score σ")
    table.add_column("Tolerance %")

    overall_passes = 0
    total_runs = len(cases) * repeats
    tolerance_pass = 0
    low_agreement_notes: list[tuple[str, str, float, float]] = []

    for idx, case in enumerate(cases, start=1):
        console.print(f"Evaluating {idx}/{len(cases)}: {compact_commit(case.commit)}")
        scores: list[int] = []
        pass_count = 0
        tolerance_count = 0

        for _ in range(repeats):
            commit = CommitEntry(sha=f"eval-{idx}", message=case.commit)
            response = client.critique_commits([commit])
            critique = response.critiques[0]
            scores.append(critique.score)

            bucket = score_bucket(critique.score)
            if bucket == case.expected_bucket:
                pass_count += 1
                overall_passes += 1
            if abs(critique.score - case.expected_score) <= SCORE_TOLERANCE:
                tolerance_count += 1
                tolerance_pass += 1

        avg = statistics.mean(scores)
        std = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        pass_pct = round((pass_count / repeats) * 100, 1)

        tolerance_pct = f"{round((tolerance_count / repeats) * 100, 1)}%"
        tolerance_pct_value = round((tolerance_count / repeats) * 100, 1)

        table.add_row(
            compact_commit(case.commit),
            case.expected_bucket,
            str(case.expected_score),
            f"{pass_pct}%",
            f"{avg:.2f}",
            f"{std:.2f}",
            tolerance_pct,
        )
        if pass_pct < 100.0 or tolerance_pct_value < 100.0:
            low_agreement_notes.append(
                (compact_commit(case.commit), case.rationale, pass_pct, tolerance_pct_value)
            )

    console.print(table)
    console.print(
        f"Overall bucket accuracy: {overall_passes}/{total_runs} ({round((overall_passes/total_runs)*100,1)}%)"
    )
    console.print(
        f"Overall tolerance accuracy (+/- {SCORE_TOLERANCE}): "
        f"{tolerance_pass}/{total_runs} ({round((tolerance_pass/total_runs)*100,1)}%)"
    )
    if low_agreement_notes:
        console.print("\nRationale (low-agreement cases):")
        for commit_text, rationale, bucket_pct, tol_pct in low_agreement_notes:
            console.print(
                f"- {commit_text} | bucket={bucket_pct}% tolerance={tol_pct}% | {rationale}"
            )


if __name__ == "__main__":
    main()
