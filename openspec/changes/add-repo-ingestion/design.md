## Context

First vertical slice of eng-insights. Output of this change is a populated
SQLite database that later changes (identity mapping, reports, complexity
scoring) read from. Implementation is done by a small local model, so every
module is small and has an explicit interface and tests written up front.

## Goals / Non-Goals

**Goals**
- Reliable, repeatable, incremental ingestion of commit and per-file data.
- Safe credential handling.
- Data shaped so that later size metrics can exclude merges, generated files and binaries.

**Non-Goals**
- Identity resolution (multiple emails per engineer, bots, co-authors). Stored raw here.
- PRs, reviews, and GitHub API data.
- Complexity scoring, reports, web UI.
- Ingesting non-default branches.
- A history window (for example last 6 months). Full history is ingested; revisit if repos are huge.

## Decisions

1. **Bare clone, not shallow.** `git clone --bare` gives full history for `git log`
   and later `git show <sha>:<path>` for complexity analysis, without a working
   tree. Updates use `git fetch origin +refs/heads/*:refs/heads/* --prune` so
   force-pushed branches are followed.
2. **stdlib sqlite3, no ORM.** No dependencies, trivial to test with `:memory:`,
   and less framework surface for a small model. The schema is defined as a SQL
   constant in `db.py`. Mutating helpers do not commit; callers wrap work in
   `with conn:` so a sync is one transaction.
3. **Parsing `git log --numstat` without `-z`.** Format string
   `%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%B%x1f` puts a record separator before each
   commit and unit separators between fields; the numstat block is whatever follows
   the final separator. Use `-M` for rename detection and `-c core.quotepath=false`
   so non-ASCII paths are not escaped. Renames appear as `old => new` or
   `dir/{old => new}/file`; `parse_rename_path` handles both forms, including empty
   sides like `{ => sub}`.
4. **Merge commits** show no numstat by default, so they naturally have zero file
   rows. `is_merge` is derived from having more than one parent.
5. **Timestamps** are the author date converted to UTC and stored as ISO-8601
   strings with `+00:00`.
6. **Generated files.** `is_generated` is true for binary files, lockfiles,
   minified/sourcemap files, protobuf output, and anything under `node_modules`,
   `vendor`, `dist`, `build`, `__pycache__`, `.venv`, `.next`. The lists live as
   constants in `ingestion/classify.py`.
7. **Credentials** travel via `GIT_CONFIG_COUNT/KEY_0/VALUE_0` environment
   variables setting `http.extraHeader` to a Basic auth header. This keeps the token out of
   URLs, `.git/config` and process arguments. `GIT_TERMINAL_PROMPT=0` prevents
   interactive prompts. All command logging and error text goes through `redact`.
8. **Rewrite detection.** Before an incremental sync, run
   `git merge-base --is-ancestor <last_sha> HEAD`. Non-zero means history changed,
   so delete the repository's commits and ingest everything. Orphaned commits are
   removed rather than kept, because keeping them would double-count squashed work.
9. **Empty repositories**: `git rev-parse --verify HEAD` failing means no commits;
   return a zero result without error.

## Risks / Trade-offs

- Squash-merge workflows credit the merger rather than the original authors; that
  is a later identity-mapping concern.
- Very large repositories make full resync slow. Acceptable for a first slice.
- Commits on non-default branches are invisible until a later change adds them.
- Parsing human-oriented `--numstat` output is more fragile than `-z`; tests cover
  the rename forms we know about.

## Open Questions

- How many repositories and how much history? This decides whether a history
  window is needed.
- Should the sync later fetch PR metadata in the same pass?
