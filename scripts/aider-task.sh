#!/usr/bin/env bash
# Run one implementation task through Aider against a local Ollama model.
# usage: scripts/aider-task.sh <source-file> <test-file> [pytest -k expression]
set -euo pipefail

SRC="${1:?source file required}"
TEST="${2:?test file required}"
K="${3:-}"

export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
PY="${PYTHON:-python3}"

CMD="$PY -m pytest $TEST -x -q"
if [ -n "$K" ]; then
  CMD="$CMD -k \"$K\""
fi

exec aider \
  --model "${AIDER_MODEL:-ollama_chat/qwen2.5-coder:14b}" \
  --edit-format whole \
  --map-tokens 0 \
  --read CONVENTIONS.md \
  --read openspec/changes/add-repo-ingestion/design.md \
  --read "$TEST" \
  --test-cmd "$CMD" --auto-test \
  --message "Implement the stubs in $SRC so that this passes: $CMD. Follow the docstrings exactly. Do not edit tests." \
  "$SRC"
