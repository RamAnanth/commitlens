from __future__ import annotations

import unittest

from commit_critic.models import CommitCritique
from commit_critic.scoring import compute_stats, split_commits


class ScoringTests(unittest.TestCase):
    def test_split_commits_uses_thresholds(self) -> None:
        critiques = [
            CommitCritique(id="1", commit="wip", score=1),
            CommitCritique(id="2", commit="chore: bump deps", score=5),
            CommitCritique(id="3", commit="feat(api): add cache", score=8),
        ]
        needs_work, well_written = split_commits(critiques)
        self.assertEqual([c.commit for c in needs_work], ["wip"])
        self.assertEqual([c.commit for c in well_written], ["feat(api): add cache"])

    def test_compute_stats_counts_vague_and_one_word(self) -> None:
        critiques = [
            CommitCritique(id="1", commit="wip", score=1),
            CommitCritique(id="2", commit="fix", score=5),
            CommitCritique(id="3", commit="feat(auth): add refresh flow", score=9),
        ]
        stats = compute_stats(critiques)
        self.assertEqual(stats.average_score, 5.0)
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.one_word_commits, 2)
        self.assertEqual(stats.vague_commits, 2)


if __name__ == "__main__":
    unittest.main()
