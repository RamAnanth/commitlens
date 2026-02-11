from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from commit_critic.git_ops import GitRepo, get_commit_log, get_staged_summary


class GitOpsParsingTests(unittest.TestCase):
    @patch("commit_critic.git_ops._run")
    def test_get_commit_log_parses_multiline_messages(self, mock_run) -> None:
        mock_run.return_value = (
            "abc123\x1ffix(auth): handle expiry\n\n- add retry\n\x1e"
            "def456\x1fchore: bump deps\x1e"
        )
        repo = GitRepo(Path("."))

        commits = get_commit_log(repo, limit=2, include_merges=False)

        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0].sha, "abc123")
        self.assertEqual(
            commits[0].message, "fix(auth): handle expiry\n\n- add retry"
        )
        called_args = mock_run.call_args.args[0]
        self.assertIn("--no-merges", called_args)

    @patch("commit_critic.git_ops._run")
    def test_get_commit_log_empty_repo_returns_empty_list(self, mock_run) -> None:
        mock_run.side_effect = RuntimeError("this branch does not have any commits yet")
        repo = GitRepo(Path("."))
        self.assertEqual(get_commit_log(repo, limit=50, include_merges=False), [])

    @patch("commit_critic.git_ops._run")
    def test_get_staged_summary_ignores_binary_numstat_values(self, mock_run) -> None:
        mock_run.return_value = "-\t-\timage.png\n10\t2\tsrc/app.py\n"
        repo = GitRepo(Path("."))

        summary = get_staged_summary(repo)

        self.assertEqual(summary.files_changed, 2)
        self.assertEqual(summary.insertions, 10)
        self.assertEqual(summary.deletions, 2)


if __name__ == "__main__":
    unittest.main()
