"""Sync one registered repository into the database.

Implement `sync_repo`. Tests: tests/test_sync.py
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from eng_insights import db
from eng_insights.git import GitError, run_git
from eng_insights.ingestion.clone import ensure_clone
from eng_insights.ingestion.gitlog import read_commits
from eng_insights.models import SyncResult

log = logging.getLogger("eng_insights.sync")


def sync_repo(conn: sqlite3.Connection, repo_id: int, token: str | None = None) -> SyncResult:
    """Clone/fetch the repo and ingest new commits. Return a SyncResult.

    Steps:
    1. repo = db.get_repo(conn, repo_id); raise ValueError(f"unknown repo id {repo_id}") if None.
    2. token = token or os.environ.get("GITHUB_TOKEN").
    3. clone_path = Path(repo["local_path"]); ensure_clone(repo["url"], clone_path, token).
    4. Empty repo check: try run_git(["rev-parse", "--verify", "HEAD"], cwd=clone_path);
       on GitError log it at INFO and return SyncResult(0, 0, False).
       Leave last_synced_sha untouched.
    5. head = that rev-parse output, stripped.
    6. last = repo["last_synced_sha"]; full_resync = False.
       If last is not None: check ancestry with
       run_git(["merge-base", "--is-ancestor", last, "HEAD"], cwd=clone_path).
       A GitError (any non-zero exit) means history was rewritten: set full_resync = True
       and last = None.
    7. rev_range = f"{last}..HEAD" if last else "HEAD"; commits = read_commits(clone_path, rev_range).
    8. Inside ONE transaction (`with conn:`): if full_resync call db.delete_repo_commits;
       insert every commit with db.insert_commit and count how many returned True;
       call db.mark_synced(conn, repo_id, head).
    9. Log one INFO line summarising the result (never log the token).
    10. Return SyncResult(new_commits=<inserted>, total_commits=db.count_commits(...),
        full_resync=full_resync).
    """
    raise NotImplementedError
