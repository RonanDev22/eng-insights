## 1. Foundations

- [ ] 1.1 `src/eng_insights/reports/types.py` (dataclasses) and `tests/reports_helpers.py` (seed helper using the contract DDL).
- [ ] 1.2 `counted_commits` in `reports/queries.py` with tests for every "Shared counting rules" scenario.

## 2. Queries (independent of each other once 1.2 is done)

- [ ] 2.1 `leaderboard` with tests for every leaderboard scenario.
- [ ] 2.2 `commit_series` with tests for every time-series scenario.
- [ ] 2.3 `recent_commits` and `repo_overview` with tests.

## 3. CLI

- [ ] 3.1 `src/eng_insights/report_cli.py` with `tests/test_report_cli.py` (end to end: build a throwaway git repo, sync, discover or seed engineers, run `report leaderboard`).
- [ ] 3.2 Wire `report` into `cli.py` (two lines) once `add-identity-mapping` is merged; the end-to-end test then uses real discovery.

## 4. Wrap-up

- [ ] 4.1 Full `pytest` and `ruff check src` green.
- [ ] 4.2 Review against the spec scenarios, then `openspec validate add-activity-queries` and archive.

> Parallel note: 1.1 then 1.2, then 2.1, 2.2 and 2.3 can run side by side. This whole change can
> run alongside `add-identity-mapping`; only 3.2 needs it merged.
