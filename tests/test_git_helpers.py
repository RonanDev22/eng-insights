import base64

import pytest

from eng_insights.git import GitError, git_env, redact, run_git


def _b64(token: str) -> str:
    return base64.b64encode(f"x-access-token:{token}".encode()).decode()


def test_git_env_without_token_has_no_auth_config():
    env = git_env(None, base_env={"PATH": "/usr/bin"})
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["PATH"] == "/usr/bin"
    assert not any(key.startswith("GIT_CONFIG_") for key in env)


def test_git_env_with_token_sets_header_through_environment():
    env = git_env("tok123", base_env={})
    assert env["GIT_CONFIG_COUNT"] == "1"
    assert env["GIT_CONFIG_KEY_0"] == "http.extraHeader"
    assert env["GIT_CONFIG_VALUE_0"] == f"Authorization: Basic {_b64('tok123')}"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_git_env_does_not_mutate_base_env():
    base = {"A": "1"}
    git_env("tok", base_env=base)
    assert base == {"A": "1"}


def test_git_env_defaults_to_os_environ(monkeypatch):
    monkeypatch.setenv("EI_MARKER", "yes")
    assert git_env(None)["EI_MARKER"] == "yes"


def test_redact_replaces_token_and_base64_form():
    text = f"url=https://x:SECRET@h/r header={_b64('SECRET')} end"
    out = redact(text, "SECRET")
    assert "SECRET" not in out
    assert _b64("SECRET") not in out
    assert out.count("***") == 2


def test_redact_without_token_returns_text_unchanged():
    assert redact("hello", None) == "hello"
    assert redact("hello", "") == "hello"


def test_run_git_returns_stdout(tmp_path):
    run_git(["init", "-b", "main"], cwd=tmp_path)
    out = run_git(["rev-parse", "--is-inside-work-tree"], cwd=tmp_path)
    assert out.strip() == "true"


def test_run_git_failure_raises_giterror(tmp_path):
    with pytest.raises(GitError) as exc:
        run_git(["rev-parse", "HEAD"], cwd=tmp_path)
    assert exc.value.returncode != 0
    assert "rev-parse HEAD" in str(exc.value)


def test_run_git_error_message_never_contains_token(tmp_path):
    with pytest.raises(GitError) as exc:
        run_git(["clone", "/nonexistent/SECRETTOKEN", str(tmp_path / "d")], token="SECRETTOKEN")
    assert "SECRETTOKEN" not in str(exc.value)
    assert "***" in str(exc.value)
