from __future__ import annotations

from pathlib import Path

from eng_insights.db import repo_name_from_url
from eng_insights.git import run_git


def cache_path_for(cache_dir: Path, url: str) -> Path:
    return cache_dir / (repo_name_from_url(url).replace("/", "__") + ".git")


def ensure_clone(url: str, dest: Path, token: str | None = None) -> Path:
    if not (dest / "HEAD").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        run_git(["clone", "--bare", url, str(dest)], token=token)
    else:
        run_git(["fetch", "origin", "+refs/heads/*:refs/heads/*", "--prune"], cwd=dest, token=token)
    return dest
