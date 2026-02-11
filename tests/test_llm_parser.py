from __future__ import annotations

import unittest

from commit_critic.llm_client import _parse_suggestion_text


class LLMParserTests(unittest.TestCase):
    def test_parses_structured_sections(self) -> None:
        text = (
            "SUMMARY:\n"
            "- update auth flow\n"
            "SUBJECT:\n"
            "fix(auth): handle token expiry\n"
            "BODY:\n"
            "- add retry guard\n"
        )
        parsed = _parse_suggestion_text(text)
        self.assertEqual(parsed.subject, "fix(auth): handle token expiry")
        self.assertEqual(parsed.summary_bullets, ["update auth flow"])
        self.assertEqual(parsed.body_bullets, ["add retry guard"])

    def test_fallback_subject_skips_headers_and_bullets(self) -> None:
        text = "SUMMARY:\n- touched files\nBODY:\n- add tests\nfix(ui): handle null"
        parsed = _parse_suggestion_text(text)
        self.assertEqual(parsed.subject, "fix(ui): handle null")


if __name__ == "__main__":
    unittest.main()
