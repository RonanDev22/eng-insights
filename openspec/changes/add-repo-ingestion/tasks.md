## 1. Skeleton (provided by the planner)

- [x] 1.1 Project layout, `pyproject.toml`, `models.py`, the SQL schema constant in `db.py`, test fixtures, and all tests are provided. Do not edit anything under `tests/`.

## 2. File classification

- [ ] 2.1 Implement `is_generated_path` in `src/eng_insights/ingestion/classify.py`.
  Done when: `pytest tests/test_classify.py` passes.

## 3. Git wrapper

- [ ] 3.1 Implement `redact`, `git_env`, `run_git` in `src/eng_insights/git.py`.
  Done when: `pytest tests/test_git_helpers.py` passes.

## 4. Parsing git log output

- [ ] 4.1 Implement `parse_rename_path` and `parse_numstat_line` in `src/eng_insights/ingestion/gitlog.py`.
  Done when: `pytest tests/test_gitlog_parse.py -k "rename_path or numstat_line"` passes.
- [ ] 4.2 Implement `parse_git_log` in the same file.
  Done when: `pytest tests/test_gitlog_parse.py` passes.
- [ ] 4.3 Implement `read_commits` in the same file (uses `run_git` and `parse_git_log`).
  Done when: `pytest tests/test_gitlog_read.py` passes.

## 5. Persistence

- [ ] 5.1 Implement the functions in `src/eng_insights/db.py` (the `SCHEMA` constant is already written).
  Done when: `pytest tests/test_db.py` passes.

## 6. Clone cache

- [ ] 6.1 Implement `cache_path_for` and `ensure_clone` in `src/eng_insights/ingestion/clone.py`.
  Done when: `pytest tests/test_clone.py` passes.

## 7. Sync

- [ ] 7.1 Implement `sync_repo` in `src/eng_insights/ingestion/sync.py`.
  Done when: `pytest tests/test_sync.py` passes.

## 8. CLI

- [ ] 8.1 Implement `main` in `src/eng_insights/cli.py`.
  Done when: `pytest tests/test_cli.py` passes.

## 9. Wrap-up

- [ ] 9.1 Run the whole suite with `pytest` and `ruff check src` and fix anything that fails in `src/` only.
- [ ] 9.2 Planner (frontier model) reviews the diff against the spec scenarios.
- [ ] 9.3 Run `openspec validate add-repo-ingestion`, then archive the change.
