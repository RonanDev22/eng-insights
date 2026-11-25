from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from eng_insights import db
from eng_insights.ingestion.clone import cache_path_for
from eng_insights.ingestion.sync import sync_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eng-insights")
    parser.add_argument("--db", default="eng_insights.db")
    parser.add_argument("--cache-dir", default=".cache/repos")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add-repo")
    add.add_argument("url")
    sync = sub.add_parser("sync")
    sync.add_argument("--repo")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = db.connect(args.db)
    try:
        db.init_schema(conn)
        if args.command == "add-repo":
            local_path = cache_path_for(Path(args.cache_dir), args.url)
            with conn:
                db.register_repo(conn, args.url, str(local_path))
            print(f"registered {db.repo_name_from_url(args.url)}")
            return 0

        if args.repo:
            row = db.find_repo_by_url(conn, args.repo)
            if row is None:
                print(f"error: repository not registered: {args.repo}", file=sys.stderr)
                return 1
            repos = [row]
        else:
            repos = db.list_repos(conn)
            if not repos:
                print("no repositories registered")
                return 0

        failed = False
        for repo in repos:
            try:
                r = sync_repo(conn, repo["id"])
            except Exception as exc:  # keep going; report at the end
                print(f"error: {repo['name']}: {exc}", file=sys.stderr)
                failed = True
                continue
            suffix = " [full resync]" if r.full_resync else ""
            print(f"synced {repo['name']}: {r.new_commits} new commits ({r.total_commits} total){suffix}")
        return 1 if failed else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
