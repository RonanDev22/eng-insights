"""Plain data types shared across the ingestion pipeline.

This file is fully implemented. Do not change it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileChange:
    """One changed file inside one commit.

    added/deleted are None for binary files. For a rename, `path` is the NEW
    path and `old_path` is the previous path.
    """

    path: str
    added: int | None
    deleted: int | None
    is_binary: bool = False
    is_generated: bool = False
    is_rename: bool = False
    old_path: str | None = None


@dataclass(frozen=True)
class CommitRecord:
    """One commit as read from `git log`. `authored_at` is UTC ISO-8601."""

    sha: str
    parents: tuple[str, ...]
    author_name: str
    author_email: str
    authored_at: str
    message: str
    files: tuple[FileChange, ...] = ()

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


@dataclass(frozen=True)
class SyncResult:
    """Outcome of syncing one repository."""

    new_commits: int
    total_commits: int
    full_resync: bool = False
