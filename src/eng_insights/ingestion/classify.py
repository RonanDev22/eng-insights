"""Decide whether a changed file is generated or vendored.

Implement `is_generated_path`. Tests: tests/test_classify.py
"""

from __future__ import annotations

LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pipfile.lock",
        "cargo.lock",
        "go.sum",
        "composer.lock",
        "gemfile.lock",
        "uv.lock",
    }
)
GENERATED_DIRS = frozenset(
    {"node_modules", "vendor", "dist", "build", "__pycache__", ".venv", ".next"}
)
GENERATED_SUFFIXES = (".min.js", ".min.css", ".map", "_pb2.py", ".pb.go")


def is_generated_path(path: str) -> bool:
    """Return True if `path` looks generated, vendored, or like a lockfile.

    Rules:
    1. Replace backslashes with forward slashes, then split on "/".
    2. True if the last segment, lowercased, is in LOCKFILE_NAMES.
    3. True if the last segment, lowercased, ends with any of GENERATED_SUFFIXES.
    4. True if any segment EXCEPT the last is in GENERATED_DIRS (case-sensitive).
    5. Otherwise False. A file that is itself named `build` or `dist` is NOT generated,
       and a directory like `src/distribution` is NOT generated.
    """
    # Replace backslashes with forward slashes and split the path
    segments = path.replace("\\", "/").split("/")
    
    # Check if the last segment is in LOCKFILE_NAMES
    if segments[-1].lower() in LOCKFILE_NAMES:
        return True
    
    # Check if the last segment ends with any of GENERATED_SUFFIXES
    if any(segments[-1].lower().endswith(suffix) for suffix in GENERATED_SUFFIXES):
        return True
    
    # Check if any segment except the last is in GENERATED_DIRS
    if any(segment in GENERATED_DIRS for segment in segments[:-1]):
        return True
    
    # Otherwise, return False
    return False
