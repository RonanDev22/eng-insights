## Why

Git records authors by whatever name and email each commit was made with. The same
person commonly appears under several emails (work, personal, GitHub noreply), and bots
(dependabot, GitHub Actions) commit alongside humans. Any per-person chart or leaderboard
is wrong until those are resolved. This change turns raw author emails into `engineers`.

## What Changes

- New tables `engineers` and `engineer_emails` (see design.md for the exact schema; the
  `add-activity-queries` change builds against the same schema).
- `discover_engineers`: after a sync, every previously unseen author email gets mapped to
  an engineer automatically, so charts work immediately with no manual setup.
- GitHub noreply addresses for the same username (`123+alice@users.noreply.github.com`
  and `alice@users.noreply.github.com`) map to one engineer.
- Bot detection by email/name patterns, stored as a flag on the engineer.
- Manual operations: merge two engineers, rename an engineer, mark/unmark a bot.
- CLI commands to run and inspect all of the above.

## Capabilities

### New Capabilities
- `identity-mapping`: engineers, their emails, bot flags, discovery and merging.

### Modified Capabilities
- `repo-ingestion`: `sync` additionally runs discovery at the end (the `sync` CLI command only;
  `sync_repo` itself is unchanged).

## Impact

- New module `src/eng_insights/identity.py`, schema additions in `db.py`, CLI additions.
- Commits are NOT modified. The link from commit to engineer is made by joining
  `lower(commits.author_email)` to `engineer_emails.email`.
- Out of scope: `Co-authored-by` trailers, teams, and any UI.
