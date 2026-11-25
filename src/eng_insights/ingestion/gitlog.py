from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from eng_insights.git import run_git
from eng_insights.ingestion.classify import is_generated_path
from eng_insights.models import CommitRecord, FileChange

LOG_FORMAT = "%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%B%x1f"


def _normalise(path: str) -> str:
    return path.replace("//", "/").lstrip("/")


def parse_rename_path(raw: str) -> tuple[str, str]:
    if " => " not in raw:
        raise ValueError(f"not a rename path: {raw!r}")
    if "{" in raw and "}" in raw:
        start = raw.index("{")
        end = raw.index("}", start)
        prefix, inner, suffix = raw[:start], raw[start + 1 : end], raw[end + 1 :]
        old_part, new_part = inner.split(" => ", 1)
        old, new = prefix + old_part + suffix, prefix + new_part + suffix
    else:
        old, new = raw.split(" => ", 1)
    return _normalise(old), _normalise(new)


def parse_numstat_line(line: str) -> FileChange:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        raise ValueError(f"bad numstat line: {line!r}")
    added_s, deleted_s, raw_path = parts
    is_rename = " => " in raw_path
    old_path: str | None = None
    path = raw_path
    if is_rename:
        old_path, path = parse_rename_path(raw_path)
    if added_s == "-" and deleted_s == "-":
        return FileChange(
            path=path,
            added=None,
            deleted=None,
            is_binary=True,
            is_generated=True,
            is_rename=is_rename,
            old_path=old_path,
        )
    return FileChange(
        path=path,
        added=int(added_s),
        deleted=int(deleted_s),
        is_binary=False,
        is_generated=is_generated_path(path),
        is_rename=is_rename,
        old_path=old_path,
    )


def parse_git_log(output: str) -> list[CommitRecord]:
    commits: list[CommitRecord] = []
    for chunk in output.split("\x1e"):
        if not chunk.strip():
            continue
        parts = chunk.split("\x1f", 6)
        if len(parts) != 7:
            raise ValueError(f"malformed git log record: {chunk[:80]!r}")
        sha, parents, name, email, date, message, stats = parts
        authored_at = datetime.fromisoformat(date).astimezone(timezone.utc).isoformat()
        files = tuple(parse_numstat_line(line) for line in stats.splitlines() if line.strip())
        commits.append(
            CommitRecord(
                sha=sha,
                parents=tuple(parents.split()),
                author_name=name,
                author_email=email,
                authored_at=authored_at,
                message=message.strip(),
                files=files,
            )
        )
    return commits


def read_commits(repo_path: Path, rev_range: str | None = None) -> list[CommitRecord]:
    output = run_git(
        [
            "-c",
            "core.quotepath=false",
            "log",
            "-M",
            "--numstat",
            f"--format={LOG_FORMAT}",
            rev_range or "HEAD",
        ],
        cwd=repo_path,
    )
    return parse_git_log(output)
