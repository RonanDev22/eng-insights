## Why

Every later feature (identity mapping, team views, complexity scoring, flow
metrics) needs a reliable local dataset of commits. GitHub API rate limits and
missing diff detail make API-only ingestion unsuitable, so we ingest from local
clones using `git log --numstat`.

## What Changes

- Register a git repository by URL (stored once, display name derived from URL).
- Keep a bare local clone per repository and update it with forced fetches.
- Parse `git log --numstat` into `commits` and `commit_files` tables in SQLite.
- Record merge commits, renames, binary files and generated/lockfile changes as
  flags so later size metrics can exclude them.
- Incremental sync: only ingest commits added since the last sync; detect
  rewritten history and re-ingest cleanly.
- A small CLI: `add-repo` and `sync`.
- Credentials via the `GITHUB_TOKEN` environment variable, never persisted or logged.

## Capabilities

### New Capabilities
- `repo-ingestion`: registering repositories, maintaining local clones, and
  extracting commit and per-file change data into SQLite.

### Modified Capabilities
- None.

## Impact

- New package `src/eng_insights/` (db, git wrapper, ingestion modules, CLI).
- New SQLite schema: `repos`, `commits`, `commit_files`.
- No UI, no identity resolution, no scoring in this change. Author name and
  email are stored exactly as git reports them.
- Only the default branch (the clone's `HEAD`) is ingested. Commits that exist
  only on other branches are out of scope.
