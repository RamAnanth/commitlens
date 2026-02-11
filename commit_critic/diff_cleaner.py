from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List


DEFAULT_IGNORES = (
    "package-lock.json",
    "poetry.lock",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pipfile.lock",
    "composer.lock",
)

BINARY_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
    ".zip",
)


@dataclass(frozen=True)
class CleanDiff:
    text: str
    truncated: bool


def clean_diff(diff: str, max_chars: int = 10000) -> CleanDiff:
    blocks = split_diff_blocks(diff)
    kept: List[str] = []
    for block in blocks:
        path = extract_path(block)
        if should_ignore(path):
            continue
        kept.append(block)

    cleaned = "".join(kept)
    truncated = False
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "\n[Diff truncated for brevity]\n"
        truncated = True
    return CleanDiff(text=cleaned, truncated=truncated)


def split_diff_blocks(diff: str) -> List[str]:
    if not diff.strip():
        return []
    blocks = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)
    return [b for b in blocks if b.strip()]


def extract_path(block: str) -> str:
    match = re.search(r"^diff --git a/(.+?) b/(.+)$", block, re.MULTILINE)
    if match:
        return match.group(2)
    return ""


def should_ignore(path: str, ignores: Iterable[str] = DEFAULT_IGNORES) -> bool:
    if not path:
        return False
    lower = path.lower()
    for name in ignores:
        if lower.endswith(name):
            return True
    for ext in BINARY_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False
