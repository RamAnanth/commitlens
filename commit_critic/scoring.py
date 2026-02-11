from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from .models import CommitCritique


NEEDS_WORK_THRESHOLD = 5
WELL_WRITTEN_THRESHOLD = 8


@dataclass(frozen=True)
class Stats:
    average_score: float
    total: int
    vague_commits: int
    vague_percent: float
    one_word_commits: int
    one_word_percent: float


def split_commits(
    critiques: List[CommitCritique],
    needs_work_threshold: int = NEEDS_WORK_THRESHOLD,
    well_written_threshold: int = WELL_WRITTEN_THRESHOLD,
) -> Tuple[List[CommitCritique], List[CommitCritique]]:
    needs_work = [c for c in critiques if c.score < needs_work_threshold]
    well_written = [c for c in critiques if c.score >= well_written_threshold]
    return needs_work, well_written


def compute_stats(
    critiques: List[CommitCritique], needs_work_threshold: int = NEEDS_WORK_THRESHOLD
) -> Stats:
    if not critiques:
        return Stats(
            average_score=0.0,
            total=0,
            vague_commits=0,
            vague_percent=0.0,
            one_word_commits=0,
            one_word_percent=0.0,
        )

    total = sum(c.score for c in critiques)
    average = round(total / len(critiques), 1)

    vague = 0
    one_word = 0

    vague_patterns = re.compile(
        r"\b(wip|fix|fixed|update|updates|misc|changes|stuff|tmp)\b",
        flags=re.IGNORECASE,
    )

    for critique in critiques:
        words = critique.commit.strip().split()
        if len(words) == 1:
            one_word += 1
        if critique.score <= needs_work_threshold and (
            len(critique.commit) < 12 or vague_patterns.search(critique.commit)
        ):
            vague += 1

    total_commits = len(critiques)
    vague_percent = round((vague / total_commits) * 100, 1)
    one_word_percent = round((one_word / total_commits) * 100, 1)

    return Stats(
        average_score=average,
        total=total_commits,
        vague_commits=vague,
        vague_percent=vague_percent,
        one_word_commits=one_word,
        one_word_percent=one_word_percent,
    )
