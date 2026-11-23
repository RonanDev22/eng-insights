import base64
import logging

import pytest

from eng_insights import db
from eng_insights.ingestion.sync import sync_repo


@pytest.fixture
def setup(make_repo, db_conn, tmp_path):
    source = make_repo()
    repo_id = db.register_repo(db_conn, str(source.path), str(tmp_path / "cache" / "source.git"))
    return source, repo_id, db_conn, tmp_path


def _shas(conn):
    return [r["sha"] for r in conn.execute("SELECT sha FROM commits ORDER BY id")]


def test_first_sync_stores_all_commits(setup):
    source, repo_id, conn, _ = setup
    authors = [("Alice Example", "alice@example.com"), ("Bob Builder", "bob@example.com")]
    source.commit({"a.py": "1\n2\n3\n"}, "c1", author=authors[0])
    source.commit({"a.py": "1\nX\n3\n"}, "c2", author=authors[1])
    source.commit({"b.py": "b\n"}, "c3", author=authors[0])
    source.commit({"c.py": "c\n"}, "c4", author=authors[1])
    source.commit({"d.py": "d\n"}, "c5\n\nbody text", author=authors[0])

    result = sync_repo(conn, repo_id)

    assert (result.new_commits, result.total_commits, result.full_resync) == (5, 5, False)
    assert set(_shas(conn)) == set(source.shas())
    row = conn.execute("SELECT * FROM commits WHERE message = 'c5\n\nbody text'").fetchone()
    assert row["author_name"] == "Alice Example"
    assert row["author_email"] == "alice@example.com"
    assert row["authored_at"].endswith("+00:00")
    assert row["is_merge"] == 0
    c2 = conn.execute("SELECT id FROM commits WHERE message = 'c2'").fetchone()["id"]
    f = conn.execute("SELECT * FROM commit_files WHERE commit_id = ?", (c2,)).fetchone()
    assert (f["path"], f["added"], f["deleted"]) == ("a.py", 1, 1)
    assert db.get_repo(conn, repo_id)["last_synced_sha"] == source.head()


def test_incremental_sync_adds_only_new_commits(setup):
    source, repo_id, conn, _ = setup
    for i in range(5):
        source.commit({f"f{i}.txt": "x\n"})
    assert sync_repo(conn, repo_id).new_commits == 5

    for i in range(3):
        source.commit({f"g{i}.txt": "y\n"})
    result = sync_repo(conn, repo_id)

    assert (result.new_commits, result.total_commits, result.full_resync) == (3, 8, False)
    shas = _shas(conn)
    assert len(shas) == len(set(shas)) == 8


def test_sync_with_nothing_new_reports_zero(setup):
    source, repo_id, conn, _ = setup
    source.commit({"a.txt": "1\n"})
    sync_repo(conn, repo_id)
    result = sync_repo(conn, repo_id)
    assert (result.new_commits, result.total_commits, result.full_resync) == (0, 1, False)


def test_merge_commit_is_flagged_and_has_no_files(setup):
    source, repo_id, conn, _ = setup
    source.commit({"base.txt": "base\n"})
    merge_sha = source.merge_feature({"feature.txt": "f\n"})

    sync_repo(conn, repo_id)

    row = conn.execute("SELECT id, is_merge FROM commits WHERE sha = ?", (merge_sha,)).fetchone()
    assert row["is_merge"] == 1
    assert conn.execute("SELECT COUNT(*) FROM commit_files WHERE commit_id = ?", (row["id"],)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM commits WHERE is_merge = 1").fetchone()[0] == 1


def test_binary_lockfile_and_vendor_files_are_flagged(setup):
    source, repo_id, conn, _ = setup
    source.commit(
        {
            "package-lock.json": "{}\n",
            "node_modules/dep/index.js": "x\n",
            "logo.png": b"\x89PNG\x00\x01\x02",
            "src/app.py": "print()\n",
        }
    )
    sync_repo(conn, repo_id)
    rows = {r["path"]: r for r in conn.execute("SELECT * FROM commit_files")}
    assert rows["package-lock.json"]["is_generated"] == 1
    assert rows["node_modules/dep/index.js"]["is_generated"] == 1
    assert rows["logo.png"]["is_binary"] == 1 and rows["logo.png"]["added"] is None
    assert rows["src/app.py"]["is_generated"] == 0


def test_rename_is_recorded_as_rename(setup):
    source, repo_id, conn, _ = setup
    source.commit({"old/mod.py": "".join(f"l{i}\n" for i in range(20))})
    source.rename("old/mod.py", "new/mod.py")
    sync_repo(conn, repo_id)
    row = conn.execute("SELECT * FROM commit_files WHERE is_rename = 1").fetchone()
    assert (row["path"], row["old_path"]) == ("new/mod.py", "old/mod.py")


def test_rewritten_history_triggers_clean_full_resync(setup):
    source, repo_id, conn, _ = setup
    for i in range(3):
        source.commit({"a.txt": f"{i}\n"}, f"c{i}")
    sync_repo(conn, repo_id)
    dropped = source.head()

    source.reset_hard("HEAD~1")
    source.commit({"b.txt": "replacement\n"}, "replacement")
    result = sync_repo(conn, repo_id)

    assert result.full_resync is True
    assert result.total_commits == 3
    assert set(_shas(conn)) == set(source.shas())
    assert dropped not in _shas(conn)
    assert db.get_repo(conn, repo_id)["last_synced_sha"] == source.head()


def test_empty_repository_syncs_with_zero_commits(setup):
    _, repo_id, conn, _ = setup
    result = sync_repo(conn, repo_id)
    assert (result.new_commits, result.total_commits, result.full_resync) == (0, 0, False)
    assert db.get_repo(conn, repo_id)["last_synced_sha"] is None


def test_unknown_repo_id_raises_value_error(db_conn):
    with pytest.raises(ValueError):
        sync_repo(db_conn, 12345)


def test_token_is_never_logged_or_persisted(setup, monkeypatch, caplog):
    source, repo_id, conn, tmp_path = setup
    source.commit({"a.txt": "1\n"})
    token = "ghp_SECRET123"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    caplog.set_level(logging.DEBUG)

    sync_repo(conn, repo_id)
    source.commit({"a.txt": "2\n"})
    sync_repo(conn, repo_id)

    assert caplog.records, "sync should log something"
    assert token not in caplog.text
    assert base64.b64encode(f"x-access-token:{token}".encode()).decode() not in caplog.text
    assert token not in (tmp_path / "cache" / "source.git" / "config").read_text()
