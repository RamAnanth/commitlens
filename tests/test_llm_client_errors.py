from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from commit_critic.config import AppConfig
from commit_critic.git_ops import CommitEntry
from commit_critic.llm_client import LLMClient


class LLMClientErrorTests(unittest.TestCase):
    def test_critique_commits_invalid_json_raises_runtime_error(self) -> None:
        with (
            patch("commit_critic.llm_client.require_api_key", return_value="test"),
            patch("commit_critic.llm_client.OpenAI"),
        ):
            client = LLMClient(AppConfig(model="gpt-4.1-mini"))
        client._call_model_json = Mock(return_value="{not-json")

        with self.assertRaises(RuntimeError) as ctx:
            client.critique_commits([CommitEntry(sha="1", message="wip")])
        self.assertIn("invalid response while analyzing commits", str(ctx.exception))

    def test_critique_commits_schema_error_raises_runtime_error(self) -> None:
        with (
            patch("commit_critic.llm_client.require_api_key", return_value="test"),
            patch("commit_critic.llm_client.OpenAI"),
        ):
            client = LLMClient(AppConfig(model="gpt-4.1-mini"))
        client._call_model_json = Mock(return_value='{"critiques":[{"commit":"wip"}]}')

        with self.assertRaises(RuntimeError) as ctx:
            client.critique_commits([CommitEntry(sha="1", message="wip")])
        self.assertIn("invalid response while analyzing commits", str(ctx.exception))

    def test_call_model_json_maps_rate_limit_error(self) -> None:
        class FakeRateLimitError(Exception):
            pass

        client = LLMClient.__new__(LLMClient)
        client.cfg = AppConfig(model="gpt-4.1-mini")
        client.client = Mock()
        client.client.responses.create.side_effect = FakeRateLimitError("rate")

        with patch("commit_critic.llm_client.RateLimitError", FakeRateLimitError):
            with self.assertRaises(RuntimeError) as ctx:
                client._call_model_json("sys", "user")
        self.assertIn("rate limited", str(ctx.exception))

    def test_call_model_json_maps_timeout_error(self) -> None:
        class FakeTimeoutError(Exception):
            pass

        client = LLMClient.__new__(LLMClient)
        client.cfg = AppConfig(model="gpt-4.1-mini")
        client.client = Mock()
        client.client.responses.create.side_effect = FakeTimeoutError("timeout")

        with patch("commit_critic.llm_client.APITimeoutError", FakeTimeoutError):
            with self.assertRaises(RuntimeError) as ctx:
                client._call_model_json("sys", "user")
        self.assertIn("timed out", str(ctx.exception))

    def test_call_model_json_maps_connection_error(self) -> None:
        class FakeConnectionError(Exception):
            pass

        client = LLMClient.__new__(LLMClient)
        client.cfg = AppConfig(model="gpt-4.1-mini")
        client.client = Mock()
        client.client.responses.create.side_effect = FakeConnectionError("conn")

        with patch("commit_critic.llm_client.APIConnectionError", FakeConnectionError):
            with self.assertRaises(RuntimeError) as ctx:
                client._call_model_json("sys", "user")
        self.assertIn("network connection", str(ctx.exception))

    def test_call_model_json_maps_status_error(self) -> None:
        class FakeStatusError(Exception):
            def __init__(self, status_code: int) -> None:
                super().__init__("status")
                self.status_code = status_code

        client = LLMClient.__new__(LLMClient)
        client.cfg = AppConfig(model="gpt-4.1-mini")
        client.client = Mock()
        client.client.responses.create.side_effect = FakeStatusError(503)

        with patch("commit_critic.llm_client.APIStatusError", FakeStatusError):
            with self.assertRaises(RuntimeError) as ctx:
                client._call_model_json("sys", "user")
        self.assertIn("status 503", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
