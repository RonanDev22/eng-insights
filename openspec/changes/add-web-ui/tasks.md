## 1. Foundations

- [ ] 1.1 Add the `web` dependency group to `pyproject.toml`, add `wal: bool = False` to `db.connect`, create `src/eng_insights/web/` with `create_app`, the connection dependency, and a `serve` subcommand in `cli.py`. Tests: `/healthz` returns 200; the non-loopback warning is printed.
- [ ] 1.2 Vendor Chart.js 4.4.x (plus its licence) into `web/static/vendor/`, add base template and CSS with the 8-colour palette and light/dark support. Test: a rendered page has no cross-origin script/style/font references.
- [ ] 1.3 Demo data: `tests/web_helpers.py` with `make_demo_db(path)` that builds a database of ~3 repos, 12 contributors, 6 months of commits, a couple of bots, using `db.insert_commit` and writing `engineers` / `engineer_emails` rows directly (contract DDL in `add-identity-mapping/design.md`). Reused by every test below and by a `demo-db` CLI command so the UI can be run before the other changes land.

## 2. Pure helpers (independent, can run in parallel)

- [ ] 2.1 `web/ranges.py` `resolve_range` with tests for each preset, anchoring to the latest commit, and invalid keys falling back to `90d`.
- [ ] 2.2 `web/validation.py` `normalise_github_url` with tests for every accepted and rejected form in the spec.
- [ ] 2.3 `web/sync.py` `SyncRegistry` and runner with tests: only one sync at a time, errors are recorded and redacted, state transitions, works when `discover_engineers` is missing.

## 3. JSON API (needs `add-activity-queries`; can start against stubbed query functions)

- [ ] 3.1 `/overview`, `/series` (top 8 + Other, dense aligned periods), and the per-contributor series, with shape tests for every field in the contract.
- [ ] 3.2 `/leaderboard` and `/recent`, plus the 404 JSON error body.

## 4. Pages (needs 1.x; can run in parallel with 3.x using the contract)

- [ ] 4.1 Index page and Add repository form (`POST /repos`): validation errors, duplicates, redirect, background sync start.
- [ ] 4.2 Repository dashboard: tiles, filter controls, chart drawn from the JSON endpoint, contributor table with caption and `sort`, recent feed, sync/progress/error/not-synced states, 404.
- [ ] 4.3 Contributor page with weekly chart and commit list; 404 for unknown or empty contributors.

## 5. Wrap-up

- [ ] 5.1 Full `pytest` and `ruff check src` green.
- [ ] 5.2 Manual check on real data: run `serve --db click.db`, open the dashboard, and confirm the numbers match `report leaderboard` for the same range. Save a screenshot of the dashboard.
- [ ] 5.3 Review against the spec scenarios, then `openspec validate add-web-ui` and archive.

> Parallel note: after 1.1 and 1.3, tasks 1.2, 2.1, 2.2, 2.3 are all independent. 3.x and 4.x can run side by side
> using the JSON contract and the demo database. The only hard dependency on the other changes is real data:
> 3.x calls the `add-activity-queries` functions (stub them until they land) and 2.3 calls `discover_engineers`.
