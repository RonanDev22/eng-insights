"""Command line entry point.

Implement `main`. Tests: tests/test_cli.py

Usage:
  eng-insights [--db PATH] [--cache-dir PATH] add-repo URL
  eng-insights [--db PATH] [--cache-dir PATH] sync [--repo URL]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from eng_insights import db
from eng_insights.git import GitError
from eng_insights.ingestion.clone import cache_path_for
from eng_insights.ingestion.sync import sync_repo


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser.

    Global options (before the subcommand):
      --db         default "eng_insights.db"
      --cache-dir  default ".cache/repos"
    Subcommands (required): `add-repo URL` and `sync [--repo URL]`.
    """
    raise NotImplementedError


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code (0 ok, 1 if anything failed).

    Always: conn = db.connect(args.db); db.init_schema(conn); close conn at the end.

    add-repo URL:
      local_path = cache_path_for(Path(args.cache_dir), URL)
      Inside `with conn:` call db.register_repo(conn, URL, str(local_path)).
      Print f"registered {name}" (name = db.repo_name_from_url(URL)). Return 0.
      Registering an already-registered URL is fine and also returns 0.

    sync [--repo URL]:
      - With --repo: look it up with db.find_repo_by_url. If missing print
        f"error: repository not registered: {URL}" to stderr and return 1.
      - Without --repo: db.list_repos(conn). If none, print "no repositories registered" and return 0.
      - For each repo call sync_repo(conn, repo["id"]).
        On success print f"synced {name}: {r.new_commits} new commits ({r.total_commits} total)"
        and append " [full resync]" when r.full_resync is true.
        On GitError (or any Exception) print f"error: {name}: {exc}" to stderr, remember the
        failure, and CONTINUE with the next repo.
      - Return 1 if any repo failed, otherwise 0.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
