## Context

The pieces below it are being built in parallel: `add-identity-mapping` (engineers) and
`add-activity-queries` (all numbers, as plain functions). This change is a thin web layer over
those functions plus the existing `register_repo` / `sync_repo`. It must not recompute metrics,
so the web and CLI always agree.

## Decisions

1. **FastAPI + Jinja2 + Chart.js, no build step.** Server-rendered pages, charts drawn in the
   browser from JSON endpoints. No Node toolchain, so small models and agents can work on it, and
   it is easy to test with `fastapi.testclient.TestClient`.
2. **Chart.js is vendored**, committed at `src/eng_insights/web/static/vendor/chart.umd.min.js`
   (Chart.js 4.4.x), not loaded from a CDN. The tool works offline and pages make no third-party
   requests. Include the licence file next to it.
3. **State lives in the URL.** `range`, `bots`, `sort` are query parameters on plain GET links and a
   plain `<form method="get">`. No client-side routing, no JavaScript needed for filtering.
4. **Preset ranges anchor to the repository's latest counted commit**, not "now". A repository
   with no commits for a year would otherwise show an empty "last 90 days". `since` is
   `anchor - (N-1) days`, inclusive; `until` is `anchor + 1 day`, exclusive (matching the query
   layer's bounds). `all` leaves both unset. The anchor is `repo_overview(...).last_commit` date.
5. **Connections.** SQLite connections are not shared across threads. Each request opens its own
   via a FastAPI dependency and closes it afterwards. The background sync opens its own. To let
   readers work while a sync writes, the server calls `db.connect(path, wal=True)`, which sets
   `PRAGMA journal_mode=WAL` (new optional argument; default off, so existing code and tests are unchanged).
6. **Background sync** runs in a daemon `threading.Thread` started by the app. An in-memory
   `SyncRegistry` (lock-protected dict keyed by repo id) holds `state` (`idle|running|error|done`),
   `error` text and timestamps, so a second request while running is ignored. It runs
   `sync_repo` then `discover_engineers` in one thread. If `discover_engineers` does not exist yet
   the registry skips it, so the UI works before the identity change lands. Status is lost on
   restart, which is fine because the database is the source of truth.
7. **URL validation** uses a single regex
   `^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$` (after stripping
   surrounding whitespace), then the normalised form `https://github.com/{owner}/{repo}.git`
   is stored with owner and repo **lowercased**: GitHub treats them case-insensitively, and
   without this `Pallets/Click` and `pallets/click` would register twice and share one cache folder. Only public GitHub
   HTTPS URLs are allowed, which also prevents the form being used to clone local paths or arbitrary
   hosts. Error text from git is passed through `redact`, as in ingestion.
8. **No authentication, localhost only.** This UI shows data about individuals. Default bind is
   127.0.0.1 and any other host prints a warning. Adding auth is a later change.
9. **Colours.** Contributor colours come from a fixed 8-colour categorical palette chosen to be
   distinguishable in light and dark themes, assigned by `engineer_id % 8` so the same person
   keeps the same colour on every page. "Other" is always neutral grey. Use CSS custom properties
   and `prefers-color-scheme`.
10. **Presentation guardrails** (see openspec/config.yaml): no composite score, every leaderboard
    row shows its components, and the caption states what is excluded.

## JSON contract (shared; the UI is built against this)

All endpoints accept `range` (`14d|90d|1y|all`, default `90d`) and `bots` (`0|1`, default `0`).
Every response also carries `"since"` and `"until"` (UTC dates; `until` exclusive) so pages can state
exactly what is shown.

`GET /api/repos/{id}/overview`
```json
{"repo": {"id": 1, "name": "pallets/click", "url": "https://github.com/pallets/click.git",
          "last_synced_at": "2026-11-25T09:00:00+00:00", "sync_state": "idle"},
 "commits": 2190, "contributors": 140, "first_commit": "2014-04-24T10:00:00+00:00",
 "last_commit": "2026-10-01T08:30:00+00:00", "bot_commits_excluded": 200,
 "since": "2026-07-04", "until": "2026-10-02"}
```

`GET /api/repos/{id}/series?top=8` (weekly)
```json
{"period": "week", "since": "2026-07-04", "until": "2026-10-02",
 "periods": ["2026-06-29", "2026-07-06"],
 "series": [{"engineer_id": 3, "name": "David Lord", "commits": [4, 7], "lines": [120, 310]}],
 "other": {"commits": [1, 2], "lines": [10, 44]}}
```
`other` is `null` when there are 8 or fewer contributors. Top contributors are ranked by commits
in range.

`GET /api/repos/{id}/engineers/{engineer_id}/series`: same shape with exactly one series and `other: null`.

`GET /api/repos/{id}/leaderboard?sort=commits|lines|active_days&limit=50`
```json
{"sort": "commits", "since": "...", "until": "...",
 "rows": [{"engineer_id": 3, "name": "David Lord", "commits": 40, "lines_added": 900,
           "lines_deleted": 400, "files_touched": 55, "active_days": 22,
           "median_size": 12, "p90_size": 140}]}
```
(`since` / `until` as above; fields mirror the query layer's `LeaderRow`.)

`GET /api/repos/{id}/recent?days=14`
```json
{"commits": [{"sha": "abc1234", "engineer_id": 3, "engineer": "David Lord",
              "authored_at": "2026-09-30T10:00:00+00:00", "subject": "Fix bug",
              "lines_added": 10, "lines_deleted": 2, "files_touched": 1}]}
```

Errors: `404` with `{"error": "repository not found"}`.

## Module layout

- `web/app.py`: `create_app(db_path, cache_dir)`; `web/deps.py`: connection dependency.
- `web/ranges.py`: pure function `resolve_range(range_key, anchor_date) -> (since, until)`.
- `web/sync.py`: `SyncRegistry` and the background runner.
- `web/validation.py`: `normalise_github_url(raw) -> str` (raises `ValueError`).
- `web/routes_api.py`, `web/routes_pages.py`, `web/templates/`, `web/static/`.
- `cli.py` gets a `serve` subcommand (`uvicorn.run` with the app).

## Risks / Trade-offs

- Computing every metric per request is fine at thousands of commits; add caching only if measured slow.
- Duplicate registration if the same repository was added from the CLI with a different URL spelling
  (e.g. without `.git`). They share a cache folder, so it only costs a duplicate row; fix later by
  normalising in `register_repo`.
- In-memory sync status vanishes on restart; a crash mid-sync leaves a partially updated database
  only if it dies between inserts and `mark_synced`, and `sync_repo` runs both in one transaction.
- Chart.js must be downloaded once when building (not at runtime). The agent doing task 1.2 needs network access.

## Open Questions

- Do you want a People page (merge / rename / unmerge in the browser) next, or teams first?
