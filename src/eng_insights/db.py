from __future__ import annotations

import re
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
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def repo_name_from_url(url: str) -> str:
    parts = [p for p in re.split(r"[/:]", url) if p]
    if parts and parts[-1].endswith(".git"):
        parts[-1] = parts[-1][: -len(".git")]
    return "/".join(parts[-2:])


def find_repo_by_url(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM repos WHERE url = ?", (url,)).fetchone()


def register_repo(conn: sqlite3.Connection, url: str, local_path: str) -> int:
    existing = find_repo_by_url(conn, url)
    if existing is not None:
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO repos (url, name, local_path) VALUES (?, ?, ?)",
        (url, repo_name_from_url(url), local_path),
    )
    return int(cur.lastrowid)


def get_repo(conn: sqlite3.Connection, repo_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM repos WHERE id = ?", (repo_id,)).fetchone()


def list_repos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM repos ORDER BY id").fetchall()


def insert_commit(conn: sqlite3.Connection, repo_id: int, commit: CommitRecord) -> bool:
    cur = conn.execute(
        "INSERT OR IGNORE INTO commits "
        "(repo_id, sha, author_name, author_email, authored_at, message, is_merge) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            repo_id,
            commit.sha,
            commit.author_name,
            commit.author_email,
            commit.authored_at,
            commit.message,
            int(commit.is_merge),
        ),
    )
    if cur.rowcount == 0:
        return False
    conn.executemany(
        "INSERT INTO commit_files "
        "(commit_id, path, old_path, added, deleted, is_binary, is_rename, is_generated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                cur.lastrowid,
                f.path,
                f.old_path,
                f.added,
                f.deleted,
                int(f.is_binary),
                int(f.is_rename),
                int(f.is_generated),
            )
            for f in commit.files
        ],
    )
    return True


def count_commits(conn: sqlite3.Connection, repo_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM commits WHERE repo_id = ?", (repo_id,)).fetchone()
    return int(row[0])


def delete_repo_commits(conn: sqlite3.Connection, repo_id: int) -> None:
    conn.execute("DELETE FROM commits WHERE repo_id = ?", (repo_id,))
    conn.execute(
        "UPDATE repos SET last_synced_sha = NULL, last_synced_at = NULL WHERE id = ?", (repo_id,)
    )


def mark_synced(
    conn: sqlite3.Connection, repo_id: int, sha: str | None, at: str | None = None
) -> None:
    when = at or datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE repos SET last_synced_sha = ?, last_synced_at = ? WHERE id = ?",
        (sha, when, repo_id),
    )
