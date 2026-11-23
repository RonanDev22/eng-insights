"""Maintain bare local clones of registered repositories.

Implement `cache_path_for` and `ensure_clone`. Tests: tests/test_clone.py
"""

from __future__ import annotations

from pathlib import Path

from eng_insights.db import repo_name_from_url
from eng_insights.git import run_git


def cache_path_for(cache_dir: Path, url: str) -> Path:
    """Return cache_dir / (<name with "/" replaced by "__"> + ".git").

    name = repo_name_from_url(url), e.g.
      "https://github.com/acme/widgets.git" -> cache_dir / "acme__widgets.git"
    """
    raise NotImplementedError


def ensure_clone(url: str, dest: Path, token: str | None = None) -> Path:
    """Make sure `dest` is an up-to-date bare clone of `url`. Return `dest`.

    - If `dest / "HEAD"` does not exist: create dest.parent (parents=True,
      exist_ok=True) and run run_git(["clone", "--bare", url, str(dest)], token=token).
    - If it exists: run
        run_git(["fetch", "origin", "+refs/heads/*:refs/heads/*", "--prune"],
                cwd=dest, token=token)
      The leading "+" forces updates so rewritten branches are followed.
    - Never put the token in the URL. GitError propagates to the caller.
    """
    raise NotImplementedError
