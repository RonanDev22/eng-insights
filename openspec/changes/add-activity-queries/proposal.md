## Why

The goal is a graphical view of contributors and their activity over time, plus leaderboards.
Before any UI exists we need one trusted, tested place that turns commits into those numbers,
so the web UI, the CLI and later exports all agree. This change is that query layer.

## What Changes

- A read-only reports module with four queries: a dense per-engineer time series, a
  leaderboard, a recent-activity feed, and a repository overview.
- Consistent counting rules (merges and bots excluded by default, generated and binary
  files excluded from line counts) defined once.
- Every leaderboard row carries its components (commits, lines, files, active days, median and
  p90 commit size). There is no single composite score.
- A `report` CLI (`leaderboard`, `weekly`, `recent`) so results are visible before the UI exists.

## Capabilities

### New Capabilities
- `activity-queries`: filtered, deterministic activity metrics over ingested commits.

### Modified Capabilities
- None.

## Impact

- New package `src/eng_insights/reports/` and `src/eng_insights/report_cli.py`.
- Depends on the `engineers` / `engineer_emails` tables. Their schema is fixed in
  `add-identity-mapping/design.md`, so this change can be built in parallel: tests create
  those tables themselves and never import `identity.py`.
- No schema changes to ingestion tables, no UI.
