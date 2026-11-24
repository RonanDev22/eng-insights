#!/usr/bin/env bash
# Run one implementation task through Aider against a local Ollama model.
# usage: scripts/aider-task.sh <source-file> <test-file> [pytest -k expression]
#
# Model: export AIDER_MODEL=ollama_chat/<tag> (tag exactly as `ollama list` shows it),
# or leave it unset and the script picks the installed model with "coder" in its name,
# provided there is exactly one. Context window: NUM_CTX (default 16384).
set -euo pipefail

SRC="${1:?source file required}"
TEST="${2:?test file required}"
K="${3:-}"

export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
PY="${PYTHON:-python3}"

# Installed Ollama model names, one per line (empty if Ollama is not reachable).
INSTALLED="$(curl -fsS "$OLLAMA_API_BASE/api/tags" 2>/dev/null \
  | "$PY" -c 'import json,sys; print("\n".join(m["name"] for m in json.load(sys.stdin)["models"]))' \
  2>/dev/null || true)"
if [ -z "$INSTALLED" ]; then
  echo "Cannot list models from Ollama at $OLLAMA_API_BASE. Is Ollama running? Try: ollama list" >&2
  exit 1
fi

if [ -n "${AIDER_MODEL:-}" ]; then
  TAG="${AIDER_MODEL#ollama_chat/}"
else
  CODERS="$(printf '%s\n' "$INSTALLED" | grep -i coder || true)"
  if [ "$(printf '%s\n' "$CODERS" | grep -c .)" -eq 1 ]; then
    TAG="$CODERS"
  else
    echo "Could not pick a model automatically. Installed models:" >&2
    printf '  %s\n' $INSTALLED >&2
    echo "Run: export AIDER_MODEL=ollama_chat/<name>" >&2
    exit 1
  fi
fi
if ! printf '%s\n' "$INSTALLED" | grep -qxF "$TAG"; then
  echo "Model '$TAG' is not installed in Ollama. Installed models:" >&2
  printf '  %s\n' $INSTALLED >&2
  exit 1
fi
echo "Using model: ollama_chat/$TAG (context ${NUM_CTX:-16384})"

# Per-run model settings so the context window matches whichever model is in use.
SETTINGS="$(mktemp "${TMPDIR:-/tmp}/aider-settings.XXXXXX")"
trap 'rm -f "$SETTINGS"' EXIT
cat > "$SETTINGS" <<EOF
- name: ollama_chat/$TAG
  extra_params:
    num_ctx: ${NUM_CTX:-16384}
EOF

CMD="$PY -m pytest $TEST -x -q"
if [ -n "$K" ]; then
  CMD="$CMD -k \"$K\""
fi

aider \
  --model "ollama_chat/$TAG" \
  --model-settings-file "$SETTINGS" \
  --edit-format whole \
  --map-tokens 0 \
  --read CONVENTIONS.md \
  --read openspec/changes/add-repo-ingestion/design.md \
  --read "$TEST" \
  --test-cmd "$CMD" --auto-test \
  --message "Implement the stubs in $SRC so that this passes: $CMD. Follow the docstrings exactly. Do not edit tests." \
  "$SRC"
