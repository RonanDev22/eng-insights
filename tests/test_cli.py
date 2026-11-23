from eng_insights import db
from eng_insights.cli import main


def _args(tmp_path, *rest):
    return ["--db", str(tmp_path / "ei.db"), "--cache-dir", str(tmp_path / "cache"), *rest]


def test_add_repo_then_sync_reports_new_commits(make_repo, tmp_path, capsys):
    source = make_repo()
    source.commit({"a.txt": "1\n"})
    source.commit({"a.txt": "2\n"})

    assert main(_args(tmp_path, "add-repo", str(source.path))) == 0
    assert "registered" in capsys.readouterr().out

    assert main(_args(tmp_path, "sync")) == 0
    assert "2 new commits (2 total)" in capsys.readouterr().out

    source.commit({"a.txt": "3\n"})
    assert main(_args(tmp_path, "sync")) == 0
    assert "1 new commits (3 total)" in capsys.readouterr().out

    assert main(_args(tmp_path, "sync")) == 0
    assert "0 new commits (3 total)" in capsys.readouterr().out


def test_add_repo_twice_is_fine(make_repo, tmp_path):
    source = make_repo()
    assert main(_args(tmp_path, "add-repo", str(source.path))) == 0
    assert main(_args(tmp_path, "add-repo", str(source.path))) == 0
    conn = db.connect(tmp_path / "ei.db")
    assert len(db.list_repos(conn)) == 1
    conn.close()


def test_sync_with_no_repositories(tmp_path, capsys):
    assert main(_args(tmp_path, "sync")) == 0
    assert "no repositories registered" in capsys.readouterr().out


def test_sync_reports_full_resync(make_repo, tmp_path, capsys):
    source = make_repo()
    for i in range(3):
        source.commit({"a.txt": f"{i}\n"})
    main(_args(tmp_path, "add-repo", str(source.path)))
    main(_args(tmp_path, "sync"))
    capsys.readouterr()

    source.reset_hard("HEAD~1")
    source.commit({"b.txt": "new\n"})
    assert main(_args(tmp_path, "sync")) == 0
    assert "[full resync]" in capsys.readouterr().out


def test_failing_repo_does_not_stop_others(make_repo, tmp_path, capsys):
    good = make_repo()
    good.commit({"a.txt": "1\n"})
    bad = str(tmp_path / "does-not-exist")
    main(_args(tmp_path, "add-repo", bad))
    main(_args(tmp_path, "add-repo", str(good.path)))
    capsys.readouterr()

    assert main(_args(tmp_path, "sync")) == 1

    captured = capsys.readouterr()
    assert "1 new commits (1 total)" in captured.out
    assert "error:" in captured.err


def test_sync_unknown_repo_selected(tmp_path, capsys):
    assert main(_args(tmp_path, "sync", "--repo", "https://github.com/no/such")) == 1
    err = capsys.readouterr().err
    assert "not registered" in err
    assert "https://github.com/no/such" in err


def test_sync_single_repo_selected(make_repo, tmp_path, capsys):
    one, two = make_repo(), make_repo()
    one.commit({"a.txt": "1\n"})
    two.commit({"b.txt": "1\n"})
    main(_args(tmp_path, "add-repo", str(one.path)))
    main(_args(tmp_path, "add-repo", str(two.path)))
    capsys.readouterr()

    assert main(_args(tmp_path, "sync", "--repo", str(two.path))) == 0
    out = capsys.readouterr().out
    assert out.count("synced") == 1
