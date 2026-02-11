from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from commit_critic.app import _run_analysis_on_repo, run_write
from commit_critic.config import AppConfig
from commit_critic.git_ops import CommitEntry, DiffSummary, GitRepo
from commit_critic.models import CommitCritique, CritiqueResponse, SuggestionResponse


class _DummyLive:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_DummyLive":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def update(self, *args, **kwargs) -> None:
        return None


class AppFlowTests(unittest.TestCase):
    def test_run_analysis_happy_path_renders_output(self) -> None:
        cfg = AppConfig(model="gpt-4.1-mini")
        repo = GitRepo(Path("."))
        commits = [
            CommitEntry(sha="a1", message="wip"),
            CommitEntry(sha="a2", message="feat(api): add cache"),
        ]
        critique_data = CritiqueResponse(
            critiques=[
                CommitCritique(
                    id="a1",
                    commit="wip",
                    score=1,
                    issue="vague",
                    better="fix(api): improve msg",
                ),
                CommitCritique(
                    id="a2",
                    commit="feat(api): add cache",
                    score=9,
                    why_good="clear scope",
                ),
            ]
        )

        with (
            patch("commit_critic.app.get_commit_log", return_value=commits),
            patch("commit_critic.app.LLMClient") as mock_client_cls,
            patch("commit_critic.app.render_commit_sections") as mock_render_sections,
            patch("commit_critic.app.render_stats") as mock_render_stats,
        ):
            mock_client = Mock()
            mock_client.critique_commits.return_value = critique_data
            mock_client_cls.return_value = mock_client

            _run_analysis_on_repo(cfg, repo, limit=2, include_merges=False)

            mock_render_sections.assert_called_once()
            mock_render_stats.assert_called_once()

    def test_run_analysis_raises_on_count_mismatch(self) -> None:
        cfg = AppConfig(model="gpt-4.1-mini")
        repo = GitRepo(Path("."))
        commits = [
            CommitEntry(sha="a1", message="wip"),
            CommitEntry(sha="a2", message="feat(api): add cache"),
        ]
        critique_data = CritiqueResponse(
            critiques=[CommitCritique(id="a1", commit="wip", score=1, issue="vague")]
        )

        with (
            patch("commit_critic.app.get_commit_log", return_value=commits),
            patch("commit_critic.app.LLMClient") as mock_client_cls,
        ):
            mock_client = Mock()
            mock_client.critique_commits.return_value = critique_data
            mock_client_cls.return_value = mock_client

            with self.assertRaises(RuntimeError) as ctx:
                _run_analysis_on_repo(cfg, repo, limit=2, include_merges=False)
            self.assertIn("incomplete analysis", str(ctx.exception))

    def test_run_write_no_staged_diff_prints_warning(self) -> None:
        cfg = AppConfig(model="gpt-4.1-mini")
        with (
            patch("commit_critic.app.require_api_key"),
            patch("commit_critic.app.is_git_repo", return_value=True),
            patch("commit_critic.app.get_staged_diff", return_value=""),
            patch("commit_critic.app.console.print") as mock_print,
        ):
            run_write(cfg)
            printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("No staged changes found", printed)

    def test_run_write_accepts_default_suggestion(self) -> None:
        cfg = AppConfig(model="gpt-4.1-mini")
        suggestion = SuggestionResponse(
            summary_bullets=["updated auth"],
            subject="fix(auth): handle token expiry",
            body_bullets=["add retry guard"],
        )

        with (
            patch("commit_critic.app.require_api_key"),
            patch("commit_critic.app.is_git_repo", return_value=True),
            patch("commit_critic.app.get_staged_diff", return_value="diff --git a/a b/a\n"),
            patch(
                "commit_critic.app.get_staged_summary",
                return_value=DiffSummary(files_changed=1, insertions=1, deletions=1),
            ),
            patch("commit_critic.app.LLMClient") as mock_client_cls,
            patch("commit_critic.app.Live", _DummyLive),
            patch("commit_critic.app.render_suggestion") as mock_render_suggestion,
            patch("commit_critic.app.Prompt.ask", return_value=""),
            patch("commit_critic.app.console.print") as mock_print,
        ):
            mock_client = Mock()
            mock_client.suggest_commit_stream.return_value = iter(
                ["SUMMARY:\n- updated auth\nSUBJECT:\nfix(auth): handle token expiry\n"]
            )
            mock_client.parse_suggestion_text.return_value = suggestion
            mock_client_cls.return_value = mock_client

            run_write(cfg)

            mock_render_suggestion.assert_called_once()
            panels = [
                call.args[0]
                for call in mock_print.call_args_list
                if call.args and getattr(call.args[0], "title", None) is not None
            ]
            self.assertTrue(any(panel.title == "Commit Message" for panel in panels))


if __name__ == "__main__":
    unittest.main()
