import pytest

from eng_insights.ingestion.gitlog import parse_git_log, parse_numstat_line, parse_rename_path
from eng_insights.models import FileChange


@pytest.mark.parametrize(
    "raw,old,new",
    [
        ("old.py => new.py", "old.py", "new.py"),
        ("src/{old => new}/file.py", "src/old/file.py", "src/new/file.py"),
        ("{old => new}/file.py", "old/file.py", "new/file.py"),
        ("src/{ => sub}/file.py", "src/file.py", "src/sub/file.py"),
        ("src/{sub => }/file.py", "src/sub/file.py", "src/file.py"),
        ("{ => sub}/file.py", "file.py", "sub/file.py"),
        ("{sub => }/file.py", "sub/file.py", "file.py"),
        ("src/dir/{a.py => b.py}", "src/dir/a.py", "src/dir/b.py"),
        ("a/b/c.py => d/e/f.py", "a/b/c.py", "d/e/f.py"),
    ],
)
def test_parse_rename_path(raw, old, new):
    assert parse_rename_path(raw) == (old, new)


def test_parse_rename_path_without_arrow_raises():
    with pytest.raises(ValueError):
        parse_rename_path("plain.py")


def test_parse_numstat_line_plain():
    assert parse_numstat_line("10\t2\tsrc/a.py") == FileChange(
        path="src/a.py", added=10, deleted=2
    )


def test_parse_numstat_line_path_with_spaces():
    fc = parse_numstat_line("1\t1\tdocs/my file.md")
    assert fc.path == "docs/my file.md"


def test_parse_numstat_line_binary():
    fc = parse_numstat_line("-\t-\tassets/logo.png")
    assert fc.path == "assets/logo.png"
    assert fc.added is None and fc.deleted is None
    assert fc.is_binary is True
    assert fc.is_generated is True


def test_parse_numstat_line_lockfile_is_generated():
    fc = parse_numstat_line("500\t3\tpackage-lock.json")
    assert fc == FileChange(path="package-lock.json", added=500, deleted=3, is_generated=True)


def test_parse_numstat_line_rename():
    fc = parse_numstat_line("0\t0\tsrc/{old => new}/a.py")
    assert fc == FileChange(
        path="src/new/a.py", old_path="src/old/a.py", added=0, deleted=0, is_rename=True
    )


def test_parse_numstat_line_invalid_raises():
    with pytest.raises(ValueError):
        parse_numstat_line("garbage")


def _record(sha, parents, name, email, date, message, stats=""):
    # Mirrors the shape of real `git log --numstat --format=LOG_FORMAT` output.
    return f"\x1e{sha}\x1f{parents}\x1f{name}\x1f{email}\x1f{date}\x1f{message}\n\x1f\n\n{stats}"


def test_parse_git_log_empty_output():
    assert parse_git_log("") == []


def test_parse_git_log_two_commits():
    c, p = "c" * 40, "p" * 40
    output = _record(
        c,
        p,
        "Alice Example",
        "alice@example.com",
        "2026-01-01T21:00:00+11:00",
        "Add thing\n\nLonger body",
        "3\t1\tsrc/a.py\n-\t-\timg/x.png\n\n",
    ) + _record(p, "", "Bob", "bob@example.com", "2026-01-01T09:00:00+00:00", "Initial", "1\t0\tREADME.md\n")
    commits = parse_git_log(output)

    assert [x.sha for x in commits] == [c, p]
    first, second = commits
    assert first.parents == (p,)
    assert first.author_name == "Alice Example"
    assert first.author_email == "alice@example.com"
    assert first.authored_at == "2026-01-01T10:00:00+00:00"
    assert first.message == "Add thing\n\nLonger body"
    assert [f.path for f in first.files] == ["src/a.py", "img/x.png"]
    assert first.files[0].added == 3 and first.files[0].deleted == 1
    assert first.files[1].is_binary is True
    assert first.is_merge is False

    assert second.parents == ()
    assert second.authored_at == "2026-01-01T09:00:00+00:00"
    assert [f.path for f in second.files] == ["README.md"]


def test_parse_git_log_merge_commit_has_two_parents_and_no_files():
    a, b = "a" * 40, "b" * 40
    output = _record("m" * 40, f"{a} {b}", "Alice", "alice@example.com", "2026-01-02T00:00:00+00:00", "Merge x")
    (merge,) = parse_git_log(output)
    assert merge.parents == (a, b)
    assert merge.is_merge is True
    assert merge.files == ()
