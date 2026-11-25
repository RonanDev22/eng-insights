## Why

The goal of the tool is to point it at a public GitHub repository and immediately see who
contributes, how activity changes over time, and who the top contributors are. Everything
built so far is command line only. This change adds a local web UI that does exactly that.

## What Changes

- `eng-insights serve` starts a local web server (FastAPI) bound to localhost.
- An **Add repository** form takes a public GitHub URL, registers it, and clones and syncs it
  in the background while showing progress.
- A **repository dashboard**: summary tiles, a stacked weekly chart of commits per
  contributor over time, a contributor table (the leaderboard) showing every component,
  and a recent-activity feed.
- A **contributor page**: one person's weekly activity, summary numbers, and recent commits.
- JSON endpoints behind the charts, with the response shapes fixed in design.md.
- Date-range presets and a bots toggle on every view, held in the URL so views can be shared.

## Capabilities

### New Capabilities
- `web-ui`: local web application for browsing repository activity.

### Modified Capabilities
- `repo-ingestion`: `serve` reuses `register_repo` and `sync_repo` unchanged. `db.connect`
  gains an optional `wal` argument (default off, so existing behaviour is untouched).

## Impact

- New package `src/eng_insights/web/` (app, routes, templates, static files).
- New optional dependency group `web` in `pyproject.toml`: `fastapi`, `uvicorn`, `jinja2`,
  `httpx` (httpx only for tests).
- Depends on `add-identity-mapping` (engineers, discovery) and `add-activity-queries` (all
  numbers). It can be built before they land, against a seeded demo database (see tasks.md).
- Out of scope: authentication, private repositories, a people/merge admin screen, teams,
  complexity scoring, PR data, exports.
