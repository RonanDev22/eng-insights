import pytest

from eng_insights import db
from eng_insights.models import CommitRecord, FileChange


def _commit(sha="a" * 40, parents=("b" * 40,), files=()):
    return CommitRecord(
        sha=sha,
        parents=parents,
        author_name="Alice",
        author_email="alice@example.com",
        authored_at="2026-01-05T10:00:00+00:00",
        message="msg",
        files=tuple(files),
    )


def test_init_schema_creates_tables_and_is_idempotent(db_conn):
    db.init_schema(db_conn)
    names = {r["name"] for r in db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"repos", "commits", "commit_files"} <= names


def test_connect_enables_foreign_keys(db_conn):
    assert db_conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_connect_creates_parent_directories(tmp_path):
    conn = db.connect(tmp_path / "nested" / "dir" / "x.db")
    db.init_schema(conn)
    conn.close()
    assert (tmp_path / "nested" / "dir" / "x.db").exists()


@pytest.mark.parametrize(
    "url,name",
    [
        ("https://github.com/acme/widgets.git", "acme/widgets"),
        ("git@github.com:acme/widgets.git", "acme/widgets"),
        ("https://github.com/acme/widgets/", "acme/widgets"),
        ("https://github.com/acme/widgets", "acme/widgets"),
        ("/tmp/work/source", "work/source"),
        ("solo", "solo"),
    ],
)
def test_repo_name_from_url(url, name):
    assert db.repo_name_from_url(url) == name


def test_register_repo_stores_fields(db_conn):
    rid = db.register_repo(db_conn, "https://github.com/acme/widgets.git", "/cache/acme__widgets.git")
    row = db.get_repo(db_conn, rid)
    assert row["url"] == "https://github.com/acme/widgets.git"
    assert row["name"] == "acme/widgets"
    assert row["local_path"] == "/cache/acme__widgets.git"
    assert row["last_synced_sha"] is None
    assert row["last_synced_at"] is None


def test_register_repo_twice_returns_same_id_and_keeps_first_path(db_conn):
    first = db.register_repo(db_conn, "https://github.com/a/b", "/p1")
    second = db.register_repo(db_conn, "https://github.com/a/b", "/p2")
    assert first == second
    assert len(db.list_repos(db_conn)) == 1
    assert db.get_repo(db_conn, first)["local_path"] == "/p1"


def test_get_repo_and_find_repo_missing(db_conn):
    assert db.get_repo(db_conn, 999) is None
    assert db.find_repo_by_url(db_conn, "nope") is None


def test_find_repo_by_url_and_list_order(db_conn):
    a = db.register_repo(db_conn, "https://github.com/a/a", "/a")
    b = db.register_repo(db_conn, "https://github.com/b/b", "/b")
    assert db.find_repo_by_url(db_conn, "https://github.com/b/b")["id"] == b
    assert [r["id"] for r in db.list_repos(db_conn)] == [a, b]


def test_insert_commit_stores_commit_and_files(db_conn):
    rid = db.register_repo(db_conn, "u", "/p")
    files = [
        FileChange(path="src/a.py", added=3, deleted=1),
        FileChange(path="logo.png", added=None, deleted=None, is_binary=True, is_generated=True),
        FileChange(path="new.py", old_path="old.py", added=0, deleted=0, is_rename=True),
    ]
    assert db.insert_commit(db_conn, rid, _commit(files=files)) is True

    row = db_conn.execute("SELECT * FROM commits").fetchone()
    assert row["repo_id"] == rid
    assert row["sha"] == "a" * 40
    assert row["author_name"] == "Alice"
    assert row["author_email"] == "alice@example.com"
    assert row["authored_at"] == "2026-01-05T10:00:00+00:00"
    assert row["message"] == "msg"
    assert row["is_merge"] == 0

    rows = db_conn.execute(
        "SELECT path, old_path, added, deleted, is_binary, is_rename, is_generated "
        "FROM commit_files ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ("src/a.py", None, 3, 1, 0, 0, 0),
        ("logo.png", None, None, None, 1, 0, 1),
        ("new.py", "old.py", 0, 0, 0, 1, 0),
    ]


def test_insert_commit_marks_merge(db_conn):
    rid = db.register_repo(db_conn, "u", "/p")
    db.insert_commit(db_conn, rid, _commit(parents=("1" * 40, "2" * 40)))
    assert db_conn.execute("SELECT is_merge FROM commits").fetchone()[0] == 1


def test_insert_commit_duplicate_returns_false_and_adds_nothing(db_conn):
    rid = db.register_repo(db_conn, "u", "/p")
    commit = _commit(files=[FileChange(path="a.py", added=1, deleted=0)])
    assert db.insert_commit(db_conn, rid, commit) is True
    assert db.insert_commit(db_conn, rid, commit) is False
    assert db.count_commits(db_conn, rid) == 1
    assert db_conn.execute("SELECT COUNT(*) FROM commit_files").fetchone()[0] == 1


def test_same_sha_allowed_in_different_repos(db_conn):
    r1 = db.register_repo(db_conn, "u1", "/p1")
    r2 = db.register_repo(db_conn, "u2", "/p2")
    assert db.insert_commit(db_conn, r1, _commit()) is True
    assert db.insert_commit(db_conn, r2, _commit()) is True
    assert db.count_commits(db_conn, r1) == 1
    assert db.count_commits(db_conn, r2) == 1


def test_delete_repo_commits_removes_data_and_resets_marker_only_for_that_repo(db_conn):
    r1 = db.register_repo(db_conn, "u1", "/p1")
    r2 = db.register_repo(db_conn, "u2", "/p2")
    f = [FileChange(path="a.py", added=1, deleted=0)]
    db.insert_commit(db_conn, r1, _commit(sha="1" * 40, files=f))
    db.insert_commit(db_conn, r2, _commit(sha="2" * 40, files=f))
    db.mark_synced(db_conn, r1, "1" * 40)

    db.delete_repo_commits(db_conn, r1)

    assert db.count_commits(db_conn, r1) == 0
    assert db.count_commits(db_conn, r2) == 1
    assert db_conn.execute("SELECT COUNT(*) FROM commit_files").fetchone()[0] == 1
    row = db.get_repo(db_conn, r1)
    assert row is not None
    assert row["last_synced_sha"] is None and row["last_synced_at"] is None


def test_mark_synced_sets_sha_and_timestamp(db_conn):
    rid = db.register_repo(db_conn, "u", "/p")
    db.mark_synced(db_conn, rid, "abc", at="2026-02-01T00:00:00+00:00")
    row = db.get_repo(db_conn, rid)
    assert row["last_synced_sha"] == "abc"
    assert row["last_synced_at"] == "2026-02-01T00:00:00+00:00"


def test_mark_synced_defaults_to_current_utc_time(db_conn):
    rid = db.register_repo(db_conn, "u", "/p")
    db.mark_synced(db_conn, rid, "abc")
    assert db.get_repo(db_conn, rid)["last_synced_at"].endswith("+00:00")
