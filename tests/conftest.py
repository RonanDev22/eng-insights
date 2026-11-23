"""Shared fixtures. Do not edit."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

DEFAULT_AUTHOR = ("Alice Example", "alice@example.com")


class RepoBuilder:
    """Builds a throwaway git repository with deterministic authors and dates."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._clock = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
        self.git("init", "-b", "main")

    def _env(self, author: tuple[str, str], when: datetime) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME=author[0],
            GIT_AUTHOR_EMAIL=author[1],
            GIT_COMMITTER_NAME=author[0],
            GIT_COMMITTER_EMAIL=author[1],
            GIT_AUTHOR_DATE=when.isoformat(),
            GIT_COMMITTER_DATE=when.isoformat(),
        )
        return env

    def _tick(self, when: datetime | None) -> datetime:
        if when is not None:
            return when
        self._clock += timedelta(hours=1)
        return self._clock

    def git(
        self,
        *args: str,
        author: tuple[str, str] = DEFAULT_AUTHOR,
        when: datetime | None = None,
    ) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            env=self._env(author, when or self._clock),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def commit(
        self,
        files: dict[str, str | bytes | None],
        message: str = "commit",
        author: tuple[str, str] = DEFAULT_AUTHOR,
        when: datetime | None = None,
    ) -> str:
        """Write files (None deletes), commit them, return the new sha."""
        when = self._tick(when)
        for rel, content in files.items():
            target = self.path / rel
            if content is None:
                target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content)
        self.git("add", "-A", author=author, when=when)
        self.git("commit", "-m", message, author=author, when=when)
        return self.head()

    def rename(
        self,
        old: str,
        new: str,
        message: str = "rename",
        author: tuple[str, str] = DEFAULT_AUTHOR,
        when: datetime | None = None,
    ) -> str:
        when = self._tick(when)
        (self.path / new).parent.mkdir(parents=True, exist_ok=True)
        self.git("mv", old, new, author=author, when=when)
        self.git("commit", "-m", message, author=author, when=when)
        return self.head()

    def merge_feature(
        self,
        files: dict[str, str | bytes | None],
        branch: str = "feature",
        message: str = "Merge feature",
        author: tuple[str, str] = DEFAULT_AUTHOR,
    ) -> str:
        """Create a branch with one commit, merge it into main with --no-ff, return merge sha."""
        self.git("checkout", "-b", branch)
        self.commit(files, message=f"work on {branch}", author=author)
        self.git("checkout", "main")
        when = self._tick(None)
        self.git("merge", "--no-ff", "-m", message, branch, author=author, when=when)
        return self.head()

    def reset_hard(self, rev: str) -> None:
        self.git("reset", "--hard", rev)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def count(self) -> int:
        return int(self.git("rev-list", "--count", "HEAD"))

    def shas(self) -> list[str]:
        return self.git("rev-list", "HEAD").splitlines()


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[..., RepoBuilder]:
    counter = {"n": 0}

    def _make(name: str | None = None) -> RepoBuilder:
        counter["n"] += 1
        return RepoBuilder(tmp_path / "repos" / (name or f"source{counter['n']}"))

    return _make


@pytest.fixture
def db_conn() -> Iterator:
    from eng_insights import db

    conn = db.connect(":memory:")
    db.init_schema(conn)
    yield conn
    conn.close()
