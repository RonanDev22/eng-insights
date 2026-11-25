## Context

Ingestion produces `commits` and `commit_files`; `add-identity-mapping` produces
`engineers` and `engineer_emails` (schema contract in that change's design.md). This change
reads both and never writes. The web UI change will call these functions directly.

## Decisions

1. **Plain functions over a connection, returning dataclasses.** No ORM, no caching. Each
   function takes `(conn, flt: ActivityFilter, ...)`. Dataclasses live in
   `reports/types.py` so the UI can serialise them to JSON unchanged.
2. **One SQL "base" query, aggregation in Python where SQL is awkward.** A single helper
   `counted_commits(conn, flt)` returns one row per counted commit with
   `commit_id, repo_id, repo_name, sha, engineer_id, engineer_name, authored_at, message,
   lines_added, lines_deleted, files_touched` (file sums computed with a LEFT JOIN on
   `commit_files` filtered to `is_generated = 0` and grouped by commit). Everything else is
   built on top of it, so the counting rules exist in exactly one place. SQLite has no
   percentile function, so median/p90 are computed in Python.
3. **Join key.** `JOIN engineer_emails ee ON ee.email = lower(c.author_email)`.
4. **Dates are UTC strings.** Bounds compare as
   `authored_at >= '<since>T00:00:00+00:00'` and `< '<until>T00:00:00+00:00'`; this works because
   ingestion stores UTC ISO-8601 with a `+00:00` suffix, so string order equals time order.
5. **Week start = Monday.** Compute with Python `date - timedelta(days=d.weekday())`.
6. **No composite score.** The leaderboard exposes every component; `metric` only chooses the
   sort. This follows the project guardrail (see openspec/config.yaml).
7. **Percentiles**: median via `statistics.median`; p90 nearest-rank, so results are always
   actual commit sizes and trivially testable.
8. **Test seeding without `identity.py`.** `tests/reports_helpers.py` provides
   `seed(conn, commits=[...], engineers={...})`, which inserts via `db.insert_commit` and writes
   `engineers` / `engineer_emails` rows directly, creating the tables with the contract DDL
   (`CREATE TABLE IF NOT EXISTS`), so it works before and after the identity change lands.

## Interface

`src/eng_insights/reports/`:

- `types.py`: `ActivityFilter`, `LeaderRow`, `SeriesPoint`, `RecentCommit`, `RepoOverview`.
- `queries.py`: `counted_commits`, `leaderboard`, `commit_series`, `recent_commits`, `repo_overview`.

`src/eng_insights/report_cli.py`: `add_report_parser(subparsers)` and `run_report(args, conn) -> int`.
`cli.py` wires them in with two lines, done in the last task to avoid conflicts with the
identity change.

## Risks / Trade-offs

- Percentiles in Python load per-commit sizes into memory; fine up to hundreds of thousands of commits.
- Bots excluded by default means a misconfigured bot flag changes totals; the overview reports
  how many bot commits were excluded so it is visible.
- Per-commit file aggregation can be slow on very large histories; add indexes if measured.

## Open Questions

- Should lines-of-code size cap outliers (a 50k-line vendor drop that is not in a vendored path)?
  Median and p90 already soften this; revisit with real data.
