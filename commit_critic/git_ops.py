from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List
from urllib.parse import urlparse


@dataclass(frozen=True)
class CommitEntry:
    sha: str
    message: str


@dataclass(frozen=True)
class DiffSummary:
    files_changed: int
    insertions: int
    deletions: int


class GitRepo:
    def __init__(self, path: Path) -> None:
        self.path = path


@contextmanager
def clone_to_temp(url: str, timeout_seconds: int = 120) -> Iterator[Path]:
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name)
    try:
        _run(
            ["git", "clone", "--depth", "200", url, str(path)],
            timeout=timeout_seconds,
        )
    except RuntimeError as exc:
        message = str(exc)
        lowered = message.lower()
        if any(
            token in lowered
            for token in (
                "authentication failed",
                "repository not found",
                "could not read username",
                "permission denied",
                "fatal: could not read from remote repository",
            )
        ):
            raise RuntimeError(
                "Please check the URL and your Git credentials (SSH key or token). "
                "Failed to clone the remote repository."
            ) from exc
        raise
    try:
        yield path
    finally:
        temp_dir.cleanup()


def validate_remote_repo(url: str, timeout_seconds: int = 20) -> None:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        path_parts = [p for p in parsed.path.split("/") if p]
        if not parsed.netloc or len(path_parts) < 2:
            raise RuntimeError(
                "The provided URL is not a valid Git repository URL. "
                "Use a direct repo URL such as https://github.com/<owner>/<repo>."
            )

    try:
        _run(["git", "ls-remote", url], timeout=timeout_seconds)
    except RuntimeError as exc:
        message = str(exc)
        lowered = message.lower()
        auth_tokens = (
            "authentication failed",
            "could not read username",
            "permission denied",
            "fatal: could not read from remote repository",
        )
        invalid_repo_tokens = (
            "not a git repository",
            "repository not found",
            "fatal: repository",
            "requested url returned error: 404",
            "unable to access",
            "could not resolve host",
            "couldn't connect to server",
            "name or service not known",
            "connection timed out",
        )
        if any(token in lowered for token in auth_tokens):
            raise RuntimeError(
                "The repository appears to be private or requires credentials. "
                "Please use a public repo URL or configure Git credentials."
            ) from exc
        if any(
            token in lowered
            for token in invalid_repo_tokens
        ):
            raise RuntimeError(
                "The provided URL does not appear to be a valid public Git repository. "
                "Use a direct repo URL such as https://github.com/<owner>/<repo>."
            ) from exc
        raise RuntimeError(
            "Could not validate the remote repository URL. Please try again."
        ) from exc


def get_commit_log(
    repo: GitRepo, limit: int, include_merges: bool
) -> List[CommitEntry]:
    try:
        output = _run(
            [
                "git",
                "-C",
                str(repo.path),
                "log",
                f"-n{limit}",
                "--pretty=format:%H%x1f%B%x1e",
            ]
            + ([] if include_merges else ["--no-merges"])
        )
    except RuntimeError as exc:
        message = str(exc).lower()
        if "does not have any commits yet" in message:
            return []
        raise
    commits: List[CommitEntry] = []
    for record in output.strip().split("\x1e"):
        if not record.strip():
            continue
        sha, message = record.strip().split("\x1f", 1)
        commits.append(CommitEntry(sha=sha, message=message.strip()))
    return commits


def get_staged_diff(repo: GitRepo) -> str:
    return _run(["git", "-C", str(repo.path), "diff", "--staged", "--no-color"])


def get_staged_summary(repo: GitRepo) -> DiffSummary:
    stats = _run(["git", "-C", str(repo.path), "diff", "--staged", "--numstat"])
    files_changed = 0
    insertions = 0
    deletions = 0
    for line in stats.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        files_changed += 1
        ins, dels = parts[0], parts[1]
        if ins.isdigit():
            insertions += int(ins)
        if dels.isdigit():
            deletions += int(dels)
    return DiffSummary(
        files_changed=files_changed, insertions=insertions, deletions=deletions
    )


def is_git_repo(repo: GitRepo) -> bool:
    try:
        output = _run(["git", "-C", str(repo.path), "rev-parse", "--is-inside-work-tree"])
    except RuntimeError:
        return False
    return output.strip() == "true"


def _run(cmd: List[str], timeout: int | None = None) -> str:
    if not shutil.which(cmd[0]):
        raise RuntimeError(f"{cmd[0]} not found on PATH")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Please try again. The git command timed out."
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout
