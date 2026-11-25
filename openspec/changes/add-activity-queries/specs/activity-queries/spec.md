## ADDED Requirements

### Requirement: Shared counting rules
All queries SHALL accept an `ActivityFilter` (repositories, `since` inclusive and `until`
exclusive as UTC dates, engineer ids, `include_bots`) and SHALL apply these rules:
merge commits are never counted; commits by engineers flagged as bots are excluded unless
`include_bots` is true; commits whose author email is not mapped to an engineer are
excluded; line counts sum `added + deleted` over files with `is_generated = 0` only; a
commit's size is that same sum and a commit with only generated files has size 0 but still
counts as a commit.

#### Scenario: Merge commits are ignored
- **WHEN** a repository has 3 normal commits and 1 merge commit by the same engineer
- **THEN** that engineer's commit count is 3

#### Scenario: Bots excluded by default
- **WHEN** a bot engineer has 5 commits and a human has 2
- **THEN** the leaderboard lists only the human
- **AND** with `include_bots=True` it lists both

#### Scenario: Generated and binary files do not inflate size
- **WHEN** a commit changes `src/a.py` (+10/-2), `package-lock.json` (+5000/-100), and `logo.png` (binary)
- **THEN** its size is 12 and its files-touched count is 1

#### Scenario: Lockfile-only commit
- **WHEN** a commit changes only `package-lock.json`
- **THEN** it counts as 1 commit with size 0

#### Scenario: Date range bounds
- **WHEN** commits exist at 2026-01-01T23:59:59+00:00 and 2026-01-02T00:00:00+00:00 and the filter is `since=2026-01-02`
- **THEN** only the second commit is counted
- **AND** with `until=2026-01-02` only the first is counted

#### Scenario: Unmapped emails are skipped
- **WHEN** a commit's author email has no `engineer_emails` row
- **THEN** it appears in no result

### Requirement: Leaderboard with visible components
`leaderboard` SHALL return one row per engineer containing: engineer id and name, commits,
lines added, lines deleted, distinct files touched, active days (distinct UTC dates with a
commit), median commit size, p90 commit size, first and last commit timestamps. Rows are
ordered by the chosen metric (`commits`, `lines`, `active_days`) descending, ties broken by
display name ascending. Median uses the standard median; p90 uses nearest-rank
(`sorted[ceil(0.9 * n) - 1]`).

#### Scenario: Ranking by commits
- **WHEN** engineers A, B, C have 5, 9, and 5 commits and the metric is `commits`
- **THEN** the order is B, then A, then C (ties by name)

#### Scenario: Ranking by lines
- **WHEN** A has 3 small commits (30 lines total) and B has 1 commit of 200 lines
- **THEN** with metric `lines` B ranks above A, and with `commits` A ranks above B

#### Scenario: Distribution statistics
- **WHEN** an engineer's commit sizes are 1, 2, 3, 4, 100
- **THEN** median is 3 and p90 is 100

#### Scenario: Active days
- **WHEN** an engineer has 3 commits on one UTC date and 1 on another
- **THEN** active days is 2

#### Scenario: Empty result
- **WHEN** the filter matches no commits
- **THEN** an empty list is returned without error

### Requirement: Dense time series
`commit_series` SHALL return, for each engineer with at least one counted commit in the
filter, one point per period (`day` or `week`, weeks starting Monday, all UTC) between the
range start and end, with zeros for empty periods. When `since`/`until` are omitted, the range
is the first to last counted commit. Each point has engineer id and name, period start date,
commits, lines added, lines deleted.

#### Scenario: Gaps are zero-filled
- **WHEN** an engineer commits in week 1 and week 3 but not week 2
- **THEN** week 2 is present with 0 commits and 0 lines

#### Scenario: Week boundaries
- **WHEN** commits occur on Sunday 2026-01-04 and Monday 2026-01-05 (UTC)
- **THEN** they fall in different weeks starting 2025-12-29 and 2026-01-05

#### Scenario: Every engineer has the same periods
- **WHEN** two engineers are included in a 4-week range
- **THEN** each has exactly 4 weekly points

### Requirement: Recent activity feed
`recent_commits` SHALL return counted commits from the last N days (default 14, measured back
from an injectable `now`) newest first, each with sha, repository name, engineer name,
timestamp, subject line (first line of the message), lines added, lines deleted, and
non-generated files touched.

#### Scenario: Window and order
- **WHEN** `now` is 2026-01-15 and commits exist on Jan 1, Jan 2, and Jan 14
- **THEN** the default 14-day feed returns the Jan 14 and Jan 2 commits in that order

#### Scenario: Subject line
- **WHEN** a commit message is "Fix bug\n\nLonger explanation"
- **THEN** the subject is "Fix bug"

### Requirement: Repository overview
`repo_overview` SHALL return counted commits, engineers with at least one counted commit,
first and last counted commit timestamps, and the number of commits excluded as bots.

#### Scenario: Overview totals
- **WHEN** a repository has 10 human commits by 3 engineers and 4 bot commits
- **THEN** the overview shows 10 commits, 3 engineers, and 4 excluded bot commits

### Requirement: Report command line interface
The system SHALL provide `report leaderboard`, `report weekly`, and `report recent` commands
accepting `--repo URL` (repeatable), `--since`, `--until`, `--days` (recent only), `--metric`
(leaderboard), and `--include-bots`, printing aligned plain-text tables.

#### Scenario: Leaderboard output
- **WHEN** the user runs `report leaderboard --repo <url>`
- **THEN** a table prints with one row per engineer and a column for each component

#### Scenario: Unknown repository
- **WHEN** `--repo` names an unregistered URL
- **THEN** an error naming it is printed to stderr and the exit code is 1
