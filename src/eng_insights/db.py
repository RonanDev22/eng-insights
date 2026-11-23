"""SQLite persistence using the stdlib `sqlite3` module (no ORM).

Implement every function below. The SCHEMA constant is already written.
Tests: tests/test_db.py

Rules:
- Mutating functions here NEVER call conn.commit(). Callers wrap work in `with conn:`.
- Booleans are stored as 0/1 integers.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from eng_insights.models import CommitRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    local_path TEXT NOT NULL,
    last_synced_sha TEXT,
    last_synced_at TEXT
);
CREATE TABLE IF NOT EXISTS commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    sha TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    authored_at TEXT NOT NULL,
    message TEXT NOT NULL,
    is_merge INTEGER NOT NULL DEFAULT 0,
    UNIQUE (repo_id, sha)
);
CREATE INDEX IF NOT EXISTS idx_commits_repo_authored ON commits (repo_id, authored_at);
CREATE INDEX IF NOT EXISTS idx_commits_author_email ON commits (author_email);
CREATE TABLE IF NOT EXISTS commit_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    old_path TEXT,
    added INTEGER,
    deleted INTEGER,
    is_binary INTEGER NOT NULL DEFAULT 0,
    is_rename INTEGER NOT NULL DEFAULT 0,
    is_generated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_commit_files_commit ON commit_files (commit_id);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection. Set row_factory to sqlite3.Row and run PRAGMA foreign_keys = ON.

    `db_path` may be ":memory:". For a file path, create missing parent directories.
    """
    raise NotImplementedError


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes using SCHEMA (conn.executescript). Safe to call repeatedly."""
    raise NotImplementedError


def repo_name_from_url(url: str) -> str:
    """Return the last two path segments of `url` joined by "/", without a ".git" suffix.

    Split on both "/" and ":" and drop empty parts. If there is only one part, return it.
      "https://github.com/acme/widgets.git" -> "acme/widgets"
      "git@github.com:acme/widgets.git"     -> "acme/widgets"
      "https://github.com/acme/widgets/"    -> "acme/widgets"
      "/tmp/work/source"                    -> "work/source"
    """
    raise NotImplementedError


def register_repo(conn: sqlite3.Connection, url: str, local_path: str) -> int:
    """Insert a repo and return its id. If `url` is already registered, return the
    existing id and change nothing (do not overwrite local_path). name = repo_name_from_url(url)."""
    raise NotImplementedError


def get_repo(conn: sqlite3.Connection, repo_id: int) -> sqlite3.Row | None:
    """Return the repos row for `repo_id`, or None."""
    raise NotImplementedError


def find_repo_by_url(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    """Return the repos row whose url matches exactly, or None."""
    raise NotImplementedError


def list_repos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all repos ordered by id ascending."""
    raise NotImplementedError


def insert_commit(conn: sqlite3.Connection, repo_id: int, commit: CommitRecord) -> bool:
    """Insert the commit and one commit_files row per file. Return True if inserted.

    If (repo_id, commit.sha) already exists, insert nothing (neither commit nor files)
    and return False. Hint: INSERT OR IGNORE and check cursor.rowcount.
    is_merge comes from commit.is_merge.
    """
    raise NotImplementedError


def count_commits(conn: sqlite3.Connection, repo_id: int) -> int:
    """Return the number of commits stored for the repo."""
    raise NotImplementedError


def delete_repo_commits(conn: sqlite3.Connection, repo_id: int) -> None:
    """Delete all commits (and, via cascade, their files) for the repo, and set the
    repo's last_synced_sha and last_synced_at to NULL. The repo row itself stays."""
    raise NotImplementedError


def mark_synced(
    conn: sqlite3.Connection, repo_id: int, sha: str | None, at: str | None = None
) -> None:
    """Set repos.last_synced_sha = sha and last_synced_at = at.

    If `at` is None use the current time as a UTC ISO-8601 string.
    """
    raise NotImplementedError
