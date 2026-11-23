import base64
import subprocess

import pytest

from eng_insights.git import GitError
from eng_insights.ingestion.clone import cache_path_for, ensure_clone


def _git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/acme/widgets.git",
        "https://github.com/acme/widgets",
        "git@github.com:acme/widgets.git",
    ],
)
def test_cache_path_for(tmp_path, url):
    assert cache_path_for(tmp_path, url) == tmp_path / "acme__widgets.git"


def test_ensure_clone_creates_bare_clone(make_repo, tmp_path):
    src = make_repo()
    src.commit({"a.txt": "1\n"})
    src.commit({"a.txt": "2\n"})
    dest = tmp_path / "cache" / "x.git"

    assert ensure_clone(str(src.path), dest) == dest

    assert (dest / "HEAD").exists()
    assert not (dest / ".git").exists()
    assert _git(dest, "rev-list", "--count", "HEAD") == "2"


def test_ensure_clone_fetches_new_commits(make_repo, tmp_path):
    src = make_repo()
    src.commit({"a.txt": "1\n"})
    dest = tmp_path / "cache" / "x.git"
    ensure_clone(str(src.path), dest)

    src.commit({"a.txt": "2\n"})
    src.commit({"a.txt": "3\n"})
    ensure_clone(str(src.path), dest)

    assert _git(dest, "rev-parse", "HEAD") == src.head()
    assert _git(dest, "rev-list", "--count", "HEAD") == "3"


def test_ensure_clone_follows_rewritten_history(make_repo, tmp_path):
    src = make_repo()
    for i in range(3):
        src.commit({"a.txt": f"{i}\n"})
    dest = tmp_path / "cache" / "x.git"
    ensure_clone(str(src.path), dest)

    src.reset_hard("HEAD~1")
    new_sha = src.commit({"b.txt": "replacement\n"})
    ensure_clone(str(src.path), dest)

    assert _git(dest, "rev-parse", "HEAD") == new_sha


def test_ensure_clone_prunes_deleted_branches(make_repo, tmp_path):
    src = make_repo()
    src.commit({"a.txt": "1\n"})
    src.git("branch", "feature")
    dest = tmp_path / "cache" / "x.git"
    ensure_clone(str(src.path), dest)
    assert "feature" in _git(dest, "branch", "--format=%(refname:short)").split()

    src.git("branch", "-D", "feature")
    ensure_clone(str(src.path), dest)

    assert "feature" not in _git(dest, "branch", "--format=%(refname:short)").split()


def test_ensure_clone_does_not_persist_token(make_repo, tmp_path):
    src = make_repo()
    src.commit({"a.txt": "1\n"})
    dest = tmp_path / "cache" / "x.git"
    token = "ghp_SECRET123"

    ensure_clone(str(src.path), dest, token=token)
    ensure_clone(str(src.path), dest, token=token)

    config = (dest / "config").read_text()
    assert token not in config
    assert base64.b64encode(f"x-access-token:{token}".encode()).decode() not in config


def test_ensure_clone_empty_remote(make_repo, tmp_path):
    src = make_repo()
    dest = tmp_path / "cache" / "x.git"
    ensure_clone(str(src.path), dest)
    assert (dest / "HEAD").exists()


def test_ensure_clone_bad_url_raises_giterror(tmp_path):
    dest = tmp_path / "cache" / "x.git"
    with pytest.raises(GitError):
        ensure_clone(str(tmp_path / "does-not-exist"), dest)
    assert not dest.exists()
