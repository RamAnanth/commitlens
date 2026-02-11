from __future__ import annotations

import unittest
from unittest.mock import patch

from commit_critic.git_ops import validate_remote_repo


class ValidateRemoteRepoTests(unittest.TestCase):
    def test_invalid_url_shape_fails_fast(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            validate_remote_repo("https://github.com")
        self.assertIn("not a valid Git repository URL", str(ctx.exception))

    @patch("commit_critic.git_ops._run")
    def test_private_repo_error_message(self, mock_run) -> None:
        mock_run.side_effect = RuntimeError(
            "fatal: could not read from remote repository"
        )
        with self.assertRaises(RuntimeError) as ctx:
            validate_remote_repo("https://github.com/org/private-repo")
        self.assertIn("requires credentials", str(ctx.exception))

    @patch("commit_critic.git_ops._run")
    def test_invalid_public_repo_message(self, mock_run) -> None:
        mock_run.side_effect = RuntimeError("fatal: repository 'x' not found")
        with self.assertRaises(RuntimeError) as ctx:
            validate_remote_repo("https://github.com/org/not-a-repo")
        self.assertIn("valid public Git repository", str(ctx.exception))

    @patch("commit_critic.git_ops._run")
    def test_successful_validation(self, mock_run) -> None:
        mock_run.return_value = "ok"
        validate_remote_repo("https://github.com/org/repo")
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
