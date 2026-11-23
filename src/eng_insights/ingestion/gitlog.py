"""Parse `git log --numstat` output into CommitRecord objects.

Implement the four functions below. Tests: tests/test_gitlog_parse.py and
tests/test_gitlog_read.py
"""

from __future__ import annotations

from pathlib import Path

from eng_insights.git import run_git
from eng_insights.ingestion.classify import is_generated_path
from eng_insights.models import CommitRecord, FileChange

# One record per commit. Fields are separated by \x1f (unit separator), each
# record starts with \x1e (record separator). %B is the raw message body.
# After the last \x1f git prints a newline, a blank line, then numstat lines.
LOG_FORMAT = "%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%B%x1f"


def parse_rename_path(raw: str) -> tuple[str, str]:
    """Split a numstat rename path into (old_path, new_path).

    Two forms exist:
      "old.py => new.py"                 -> ("old.py", "new.py")
      "src/{old => new}/file.py"         -> ("src/old/file.py", "src/new/file.py")
    In the brace form, text before "{" is a shared prefix and text after "}" is a
    shared suffix. Either side inside the braces may be empty:
      "src/{ => sub}/file.py"            -> ("src/file.py", "src/sub/file.py")
      "src/{sub => }/file.py"            -> ("src/sub/file.py", "src/file.py")
    After joining, replace any "//" with "/" and strip a leading "/".
    Raise ValueError if " => " does not appear in `raw`.
    """
    raise NotImplementedError


def parse_numstat_line(line: str) -> FileChange:
    """Parse one numstat line: "<added>\\t<deleted>\\t<path>".

    - Split on tab at most twice so paths containing spaces survive.
    - Raise ValueError if the line does not have three tab-separated parts.
    - Binary files show "-" for both counts: set added=None, deleted=None,
      is_binary=True and is_generated=True.
    - Otherwise added/deleted are ints and is_generated = is_generated_path(path).
    - If the path part contains " => " it is a rename: use parse_rename_path,
      set path=new path, old_path=old path, is_rename=True.
    - is_generated is always judged on the NEW path.
    """
    raise NotImplementedError


def parse_git_log(output: str) -> list[CommitRecord]:
    """Parse the full output of `git log --numstat --format=LOG_FORMAT`.

    - Split `output` on "\\x1e"; ignore chunks that are empty after strip().
    - For each chunk, split on "\\x1f" with maxsplit=6. The seven parts are:
      sha, parents, author_name, author_email, authored_at, message, stats.
    - parents is a space-separated string; empty string means no parents
      -> parents=() (a tuple).
    - authored_at is an ISO-8601 string with offset; convert it to UTC with
      datetime.fromisoformat(...).astimezone(timezone.utc).isoformat()
      e.g. "2026-01-01T21:00:00+11:00" -> "2026-01-01T10:00:00+00:00".
    - message is the message part with surrounding whitespace stripped.
    - stats: every non-empty line (after strip of the line ending only) goes
      through parse_numstat_line, in order. Merge commits normally have none.
    - Return commits in the order they appear in `output`. Empty output -> [].
    """
    raise NotImplementedError


def read_commits(repo_path: Path, rev_range: str | None = None) -> list[CommitRecord]:
    """Run git log in `repo_path` and return parsed commits, newest first.

    Command: run_git(["-c", "core.quotepath=false", "log", "-M", "--numstat",
                      f"--format={LOG_FORMAT}", rev_range or "HEAD"], cwd=repo_path)
    then parse_git_log(...) on the result.
    `rev_range` is anything git accepts, e.g. "abc123..HEAD".
    """
    raise NotImplementedError
