from datetime import datetime, timedelta, timezone

from eng_insights.ingestion.gitlog import read_commits

SYDNEY = timezone(timedelta(hours=11))
UTC = timezone.utc


def test_read_commits_newest_first_with_stats(make_repo):
    r = make_repo()
    s1 = r.commit(
        {"src/a.py": "one\ntwo\nthree\n"},
        "First",
        author=("Alice Example", "alice@example.com"),
        when=datetime(2026, 1, 5, 21, 0, tzinfo=SYDNEY),
    )
    s2 = r.commit(
        {"src/a.py": "one\nTWO\nthree\nfour\n", "README.md": "hi\n"},
        "Second\n\nwith body",
        author=("Bob Builder", "bob@example.com"),
        when=datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
    )

    commits = read_commits(r.path)

    assert [c.sha for c in commits] == [s2, s1]
    newest, oldest = commits
    assert newest.author_name == "Bob Builder"
    assert newest.author_email == "bob@example.com"
    assert newest.authored_at == "2026-01-06T12:00:00+00:00"
    assert newest.message == "Second\n\nwith body"
    assert newest.parents == (s1,)
    assert {f.path: (f.added, f.deleted) for f in newest.files} == {
        "README.md": (1, 0),
        "src/a.py": (2, 1),
    }
    assert oldest.parents == ()
    assert oldest.authored_at == "2026-01-05T10:00:00+00:00"
    assert [(f.path, f.added, f.deleted) for f in oldest.files] == [("src/a.py", 3, 0)]


def test_read_commits_with_range_returns_only_newer_commits(make_repo):
    r = make_repo()
    s1 = r.commit({"a.txt": "1\n"}, "one")
    s2 = r.commit({"a.txt": "2\n"}, "two")
    s3 = r.commit({"a.txt": "3\n"}, "three")
    assert [c.sha for c in read_commits(r.path, f"{s1}..HEAD")] == [s3, s2]
    assert read_commits(r.path, f"{s3}..HEAD") == []


def test_read_commits_flags_merge_commits(make_repo):
    r = make_repo()
    r.commit({"base.txt": "base\n"}, "base")
    merge_sha = r.merge_feature({"feature.txt": "f\n"})
    commits = {c.sha: c for c in read_commits(r.path)}
    assert commits[merge_sha].is_merge is True
    assert commits[merge_sha].files == ()
    assert all(not c.is_merge for sha, c in commits.items() if sha != merge_sha)
    assert len(commits) == 3


def test_read_commits_flags_binary_lockfile_and_normal_files(make_repo):
    r = make_repo()
    r.commit(
        {
            "package-lock.json": "{}\n{}\n",
            "assets/logo.png": b"\x89PNG\x00\x01\x02binary",
            "src/app.py": "print('hi')\n",
        },
        "mixed",
    )
    (commit,) = read_commits(r.path)
    files = {f.path: f for f in commit.files}
    assert files["package-lock.json"].is_generated is True
    assert files["package-lock.json"].is_binary is False
    assert files["assets/logo.png"].is_binary is True
    assert files["assets/logo.png"].is_generated is True
    assert files["assets/logo.png"].added is None
    assert files["src/app.py"].is_generated is False
    assert files["src/app.py"].added == 1


def test_read_commits_detects_renames_even_if_user_config_disables_them(make_repo, monkeypatch):
    # A developer's own ~/.gitconfig may set diff.renames=false; ingestion must not depend on it.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.renames")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")
    r = make_repo()
    body = "".join(f"line {i}\n" for i in range(20))
    r.commit({"a/mod.py": body}, "add")
    r.rename("a/mod.py", "b/mod.py", "move it")
    (change,) = read_commits(r.path)[0].files
    assert change.is_rename is True
    assert (change.old_path, change.path) == ("a/mod.py", "b/mod.py")


def test_read_commits_detects_renames(make_repo):
    r = make_repo()
    body = "".join(f"line {i}\n" for i in range(20))
    r.commit({"src/old/module.py": body}, "add")
    sha = r.rename("src/old/module.py", "src/new/module.py", "move it")
    newest = read_commits(r.path)[0]
    assert newest.sha == sha
    (change,) = newest.files
    assert change.is_rename is True
    assert change.path == "src/new/module.py"
    assert change.old_path == "src/old/module.py"
    assert (change.added, change.deleted) == (0, 0)
