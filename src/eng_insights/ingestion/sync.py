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
    repo = db.get_repo(conn, repo_id)
    if repo is None:
        raise ValueError(f"unknown repo id {repo_id}")
    token = token or os.environ.get("GITHUB_TOKEN")
    clone_path = Path(repo["local_path"])
    ensure_clone(repo["url"], clone_path, token)

    try:
        head = run_git(["rev-parse", "--verify", "HEAD"], cwd=clone_path).strip()
    except GitError as exc:
        log.info("%s has no commits yet: %s", repo["name"], exc)
        return SyncResult(0, 0, False)

    last = repo["last_synced_sha"]
    full_resync = False
    if last is not None:
        try:
            run_git(["merge-base", "--is-ancestor", last, "HEAD"], cwd=clone_path)
        except GitError:
            full_resync = True
            last = None

    commits = read_commits(clone_path, f"{last}..HEAD" if last else "HEAD")

    inserted = 0
    with conn:
        if full_resync:
            db.delete_repo_commits(conn, repo_id)
        for commit in commits:
            if db.insert_commit(conn, repo_id, commit):
                inserted += 1
        db.mark_synced(conn, repo_id, head)

    total = db.count_commits(conn, repo_id)
    log.info(
        "synced %s: %d new commits (%d total)%s",
        repo["name"],
        inserted,
        total,
        " [full resync]" if full_resync else "",
    )
    return SyncResult(new_commits=inserted, total_commits=total, full_resync=full_resync)
