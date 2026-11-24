"""Thin, safe wrapper around the `git` executable.

Implement `redact`, `git_env` and `run_git`. `GitError` is already done.
Tests: tests/test_git_helpers.py
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

log = logging.getLogger("eng_insights.git")


class GitError(RuntimeError):
    """A git command failed. `str(error)` is already redacted."""

    def __init__(self, message: str, returncode: int) -> None:
        super().__init__(message)
        self.returncode = returncode


def redact(text: str, token: str | None) -> str:
    """Replace every occurrence of the token, and of its base64 form, with '***'.

    The base64 form is base64(f"x-access-token:{token}") as produced in `git_env`.
    If `token` is None or empty, return `text` unchanged.
    """
    if not token:
        return text

    b64_token = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    text = text.replace(token, "***")
    text = text.replace(b64_token, "***")
    return text


def git_env(token: str | None, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment dict for running git.

    - Start from a COPY of `base_env` (or of os.environ when base_env is None).
      Never mutate the input mapping.
    - Always set GIT_TERMINAL_PROMPT to "0".
    - If `token` is truthy, also set:
        GIT_CONFIG_COUNT   = "1"
        GIT_CONFIG_KEY_0   = "http.extraHeader"
        GIT_CONFIG_VALUE_0 = "Authorization: Basic " + base64(f"x-access-token:{token}")
      (base64 of the UTF-8 bytes, decoded to str).
    - If `token` is falsy, do not add any GIT_CONFIG_* keys.
    """
    env = dict(base_env) if base_env else os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if token:
        b64_token = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
        env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {b64_token}"

    return env


def run_git(args: Sequence[str], cwd: Path | None = None, token: str | None = None) -> str:
    """Run `git <args>` and return stdout as text (not stripped).

    - Use subprocess.run with ["git", *args], cwd=cwd, env=git_env(token),
      capture_output=True, text=True, encoding="utf-8", errors="replace".
    - Log the command at DEBUG on logger `log`, passed through redact().
    - On a non-zero exit code raise GitError whose message is
      redact(f"git {' '.join(args)} failed ({returncode}): {stderr.strip()}", token)
      and whose returncode is the process return code.
    """
    env = git_env(token)
    command = ["git", *args]
    log.debug(redact(f"Running command: {' '.join(command)}", token))

    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise GitError(
            redact(
                f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}",
                token,
            ),
            result.returncode,
        )

    return result.stdout
