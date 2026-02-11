from __future__ import annotations

import unittest

from commit_critic.diff_cleaner import clean_diff


class DiffCleanerTests(unittest.TestCase):
    def test_clean_diff_ignores_lockfiles(self) -> None:
        diff = (
            "diff --git a/package-lock.json b/package-lock.json\n"
            "--- a/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
        )
        cleaned = clean_diff(diff)
        self.assertIn("diff --git a/app.py b/app.py", cleaned.text)
        self.assertNotIn("package-lock.json", cleaned.text)
        self.assertFalse(cleaned.truncated)

    def test_clean_diff_truncates_large_payload(self) -> None:
        block = (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
        )
        cleaned = clean_diff(block * 50, max_chars=120)
        self.assertTrue(cleaned.truncated)
        self.assertIn("[Diff truncated for brevity]", cleaned.text)


if __name__ == "__main__":
    unittest.main()
