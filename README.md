# eng-insights

Internal tool that surfaces git activity per engineer and team as **conversation
starters, not a leaderboard**. This repo currently contains the first OpenSpec
change, `add-repo-ingestion`: specs, interface stubs, and failing tests. A local
model fills in the stubs one task at a time.

## Layout

```
openspec/
  config.yaml                         project context for OpenSpec
  changes/add-repo-ingestion/         proposal, spec scenarios, design, tasks
src/eng_insights/                     stubs (raise NotImplementedError) + models.py
tests/                                114 tests encoding the spec scenarios
CONVENTIONS.md                        rules the local model must follow
scripts/aider-task.sh                 runs one task through Aider + Ollama
.aider.model.settings.yml             sets the Ollama context window for Aider
```

## One-time setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest ruff
git init && git add -A && git commit -m "Planner: spec, stubs, tests"

# OpenSpec: run init first, then merge in this repo's config and change folder.
# If init already created openspec/config.yaml, merge the `context:` and `rules:`
# blocks from this repo's copy into it instead of overwriting.
openspec init --tools claude
openspec validate add-repo-ingestion
```

`pytest` works without installing the package (`pythonpath = src` in `pyproject.toml`).
Requires Python 3.11+ and git 2.32+.

## The implementation loop (local model)

Make sure Ollama is running with the model pulled, then work through
`openspec/changes/add-repo-ingestion/tasks.md` in order, one task per session:

| Task | Source file | Test command |
|---|---|---|
| 2.1 | `src/eng_insights/ingestion/classify.py` | `pytest tests/test_classify.py` |
| 3.1 | `src/eng_insights/git.py` | `pytest tests/test_git_helpers.py` |
| 4.1 | `src/eng_insights/ingestion/gitlog.py` | `pytest tests/test_gitlog_parse.py -k "rename_path or numstat_line"` |
| 4.2 | `src/eng_insights/ingestion/gitlog.py` | `pytest tests/test_gitlog_parse.py` |
| 4.3 | `src/eng_insights/ingestion/gitlog.py` | `pytest tests/test_gitlog_read.py` |
| 5.1 | `src/eng_insights/db.py` | `pytest tests/test_db.py` |
| 6.1 | `src/eng_insights/ingestion/clone.py` | `pytest tests/test_clone.py` |
| 7.1 | `src/eng_insights/ingestion/sync.py` | `pytest tests/test_sync.py` |
| 8.1 | `src/eng_insights/cli.py` | `pytest tests/test_cli.py` |

Example (task 2.1):

```bash
scripts/aider-task.sh src/eng_insights/ingestion/classify.py tests/test_classify.py
# task 4.1 (optional third argument is a pytest -k expression):
scripts/aider-task.sh src/eng_insights/ingestion/gitlog.py tests/test_gitlog_parse.py "rename_path or numstat_line"
```

Or run Aider by hand:

```bash
export OLLAMA_API_BASE=http://127.0.0.1:11434
aider --model ollama_chat/qwen2.5-coder:14b --edit-format whole \
  --read CONVENTIONS.md --read openspec/changes/add-repo-ingestion/design.md \
  --read tests/test_classify.py \
  --test-cmd "python3 -m pytest tests/test_classify.py -x -q" --auto-test \
  src/eng_insights/ingestion/classify.py
```

(Flags are from Aider's docs as of writing; confirm with `aider --help`.)

### Rules of the loop

1. After each task run the task's tests yourself. Do not trust the model's "done".
2. Commit when green: `git commit -am "task 2.1"`.
3. If the model fails the same task three times, stop and send the failing output
   to the frontier model instead of letting it thrash. Usually the fix is a
   clearer docstring, not a bigger model.
4. Never let the local model edit `tests/`, `models.py`, or the `SCHEMA` constant.
   `git diff --stat -- tests` should always be empty.

## Review and archive

When `pytest` is fully green and `ruff check src` is clean, hand the diff to the
frontier model to review against the scenarios in
`openspec/changes/add-repo-ingestion/specs/repo-ingestion/spec.md`. Then:

```bash
openspec validate add-repo-ingestion
openspec archive add-repo-ingestion
```

## Using it

```bash
export GITHUB_TOKEN=...          # only needed for private repos
python3 -m eng_insights add-repo https://github.com/your-org/your-repo.git
python3 -m eng_insights sync
sqlite3 eng_insights.db "select author_email, count(*) from commits group by 1 order by 2 desc"
```

Run these from the repo root with `PYTHONPATH=src` (or `pip install -e .`).

## Not in this change

Identity mapping (multiple emails per engineer, bots), teams, reports, complexity
scoring, PR and review data, and non-default branches. Author emails are stored raw.
