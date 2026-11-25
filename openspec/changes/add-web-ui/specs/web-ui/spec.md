## ADDED Requirements

### Requirement: Local-only server
The system SHALL provide `eng-insights serve` accepting `--db`, `--cache-dir`, `--host`
(default `127.0.0.1`) and `--port` (default `8000`). The UI has no authentication, so when
`--host` is not a loopback address the command MUST print a warning that the data is exposed
to the network.

#### Scenario: Default binding
- **WHEN** the user runs `serve` with no `--host`
- **THEN** the server binds to 127.0.0.1 and prints the URL it is serving

#### Scenario: Non-loopback host warns
- **WHEN** the user runs `serve --host 0.0.0.0`
- **THEN** a warning that the UI has no authentication is printed before the server starts

### Requirement: Repository index
The home page `/` SHALL list every registered repository with its name, commit count,
contributor count, date range of counted commits, and last sync time, each linking to its
dashboard, and SHALL show the Add repository form.

#### Scenario: Lists repositories
- **WHEN** two repositories are registered and one has been synced
- **THEN** the page lists both, and the unsynced one shows "not synced yet"

#### Scenario: Empty state
- **WHEN** no repositories are registered
- **THEN** the page explains how to add one and shows the form

### Requirement: Add a repository
`POST /repos` SHALL accept a GitHub repository URL, register it, start a background
clone, sync, and engineer discovery, and redirect to the repository's dashboard. Only
`https://github.com/<owner>/<repo>` URLs (optional `.git`, optional trailing slash) are accepted,
normalised to `https://github.com/<owner>/<repo>.git`. The UI MUST NOT accept, display, or log an access
token; a token is read from the server's `GITHUB_TOKEN` environment variable only.
At most one sync runs per repository at a time.

#### Scenario: Valid URL is accepted
- **WHEN** the user submits `https://github.com/pallets/click`
- **THEN** the repository is registered as `https://github.com/pallets/click.git` and the user is redirected to its dashboard

#### Scenario: Case and whitespace are normalised
- **WHEN** the user submits ` https://github.com/Pallets/Click/ `
- **THEN** the repository is registered as `https://github.com/pallets/click.git`
- **AND** submitting `https://github.com/pallets/click` afterwards finds the same repository

#### Scenario: Invalid URLs are rejected
- **WHEN** the user submits `file:///etc`, `git@github.com:a/b.git`, `https://example.com/a/b`, or an empty value
- **THEN** the form is shown again with a clear error and nothing is registered

#### Scenario: Duplicate submission
- **WHEN** the user submits a URL that is already registered
- **THEN** no duplicate is created and the user is redirected to the existing dashboard

#### Scenario: Sync progress is visible
- **WHEN** a repository is syncing
- **THEN** its dashboard shows "Syncing…" and refreshes itself until the sync finishes

#### Scenario: Sync failure is shown
- **WHEN** the clone fails (for example the repository does not exist)
- **THEN** the dashboard shows the error message and a Retry button, and the message contains no token

#### Scenario: Only one sync at a time
- **WHEN** a sync is requested for a repository that is already syncing
- **THEN** no second sync starts

### Requirement: Repository dashboard
`GET /repos/{id}` SHALL show: summary tiles (counted commits, contributors, first and last commit
date, bot commits excluded); a stacked bar chart of commits per week by contributor (the top 8 by
commits in range plus an "Other" group); the contributor table; and the recent activity feed.
Unknown ids return 404. A repository that has not synced shows a sync prompt rather than empty charts.

#### Scenario: Dashboard content
- **WHEN** a synced repository with 3 contributors is opened
- **THEN** the page shows the tiles, a chart, a table with 3 rows, and a recent feed

#### Scenario: Top eight plus Other
- **WHEN** a repository has 12 contributors with commits in range
- **THEN** the chart has 8 named series plus "Other" containing the remaining 4

#### Scenario: Unknown repository
- **WHEN** `/repos/999` is requested and no such repository exists
- **THEN** the response is 404 with a friendly message

#### Scenario: Not yet synced
- **WHEN** a registered repository has never been synced
- **THEN** the page offers a Sync button and shows no chart

### Requirement: Range and bot filters
Every repository and contributor view SHALL accept `range` (`14d`, `90d`, `1y`, `all`; default
`90d`) and `bots` (`0` or `1`; default `0`) query parameters, shown as controls and preserved
in links. A preset range ends at the repository's latest counted commit date, not at today's date,
so dormant repositories still show data. The page states the exact dates being shown, in UTC.

#### Scenario: Range is anchored to the latest commit
- **WHEN** a repository's latest counted commit is 2025-03-10 and range is `14d`
- **THEN** the data covers 2025-02-25 to 2025-03-10 inclusive and the page says so

#### Scenario: Bots toggle
- **WHEN** `bots=1` is given
- **THEN** bot contributors appear in the chart and table, and the tile for excluded bot commits shows 0

#### Scenario: Invalid parameters
- **WHEN** `range=banana` is given
- **THEN** the default range is used rather than an error

### Requirement: Contributor table
The table SHALL show one row per contributor with commits, lines added, lines deleted, files
touched, active days, median commit size, and p90 commit size, sortable by commits, lines, or
active days via a `sort` query parameter, with a caption stating what is excluded (merge commits,
bots unless enabled, generated and binary files). There MUST NOT be a combined score or a
column that merges several measures into one number.

#### Scenario: Sorting
- **WHEN** `sort=lines` is given
- **THEN** rows are ordered by lines changed, highest first

#### Scenario: Components are all visible
- **WHEN** the table is rendered
- **THEN** each row shows all seven measures

#### Scenario: Caption explains the numbers
- **WHEN** the table is rendered with default filters
- **THEN** the caption mentions merge commits, bots, and generated files

### Requirement: Contributor page
`GET /repos/{id}/engineers/{engineer_id}` SHALL show that contributor's summary numbers, a weekly
commits chart for the selected range, and their recent commits (date, subject, lines changed).
Unknown engineers return 404.

#### Scenario: Contributor page content
- **WHEN** a contributor with commits in range is opened
- **THEN** the page shows their name, summary numbers, a weekly chart, and a list of commits

#### Scenario: Unknown contributor
- **WHEN** the engineer id does not exist, or has no commits in this repository
- **THEN** the response is 404

### Requirement: JSON endpoints
The system SHALL provide `GET /api/repos/{id}/overview`, `/series`, `/leaderboard`, and `/recent`,
and `GET /api/repos/{id}/engineers/{engineer_id}/series`, returning the shapes defined in design.md,
accepting the same `range` and `bots` parameters. Charts MUST be drawn from these endpoints.

#### Scenario: Series shape
- **WHEN** `/api/repos/1/series?range=90d` is requested
- **THEN** the response has aligned `periods`, per-contributor `series`, and an `other` group, all with equal lengths

#### Scenario: Unknown repository
- **WHEN** the repository id does not exist
- **THEN** the response is 404 with a JSON error body

### Requirement: Readable and accessible charts
Each chart SHALL have a title, labelled axes, a legend, a consistent colour per contributor across
every chart on the site, and a text alternative (the table beneath it). Charts MUST work without
network access, so the chart library is served from the application's own static files, and the
pages respect the browser's light or dark colour scheme.

#### Scenario: No external requests
- **WHEN** a dashboard page is rendered
- **THEN** it references no scripts, styles, or fonts hosted on another domain

#### Scenario: Stable colours
- **WHEN** the same contributor appears on the dashboard and on their own page
- **THEN** they are drawn in the same colour
