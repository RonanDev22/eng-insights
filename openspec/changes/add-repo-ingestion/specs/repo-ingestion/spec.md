## ADDED Requirements

### Requirement: Repository registration
The system SHALL let a user register a git repository by URL. Each URL MUST be
stored at most once, and a display name MUST be derived from the last two path
segments of the URL without any `.git` suffix.

#### Scenario: Register a new repository
- **WHEN** the user registers `https://github.com/acme/widgets.git`
- **THEN** a repository record exists with that URL and the name `acme/widgets`
- **AND** the record has no last-synced commit

#### Scenario: Register the same URL twice
- **WHEN** the user registers a URL that is already registered
- **THEN** the existing repository id is returned
- **AND** no duplicate record is created

### Requirement: Local clone cache
The system SHALL keep one bare clone per registered repository in a cache
directory, creating it on first sync and updating it on later syncs. Updates
MUST use a forced fetch with pruning so that rewritten branches are followed.

#### Scenario: First sync clones the repository
- **WHEN** a repository with no local clone is synced
- **THEN** a bare clone exists at the repository's cache path

#### Scenario: Later sync fetches new commits
- **WHEN** new commits are pushed upstream and the repository is synced again
- **THEN** the local clone contains the new commits

#### Scenario: Upstream history was rewritten
- **WHEN** the upstream default branch is force-updated to a different history
- **THEN** the next sync updates the local clone to match it

### Requirement: Commit extraction
The system SHALL extract every commit reachable from the clone's `HEAD`,
storing sha, author name, author email, author timestamp (converted to UTC),
full message, and a merge flag. For each commit it SHALL store one row per
changed file with added lines, deleted lines, path, and flags.

#### Scenario: First sync stores all commits
- **WHEN** a registered repository with 5 commits is synced for the first time
- **THEN** 5 commits are stored with author name, author email, UTC timestamp and message
- **AND** each changed file has its added and deleted line counts

#### Scenario: Merge commits are flagged
- **WHEN** a merge commit is ingested
- **THEN** it is stored with `is_merge` true and has no file rows

#### Scenario: Renames are recorded as renames
- **WHEN** a commit renames a file without changing it
- **THEN** its file row has `is_rename` true, the new path in `path`, and the previous path in `old_path`

#### Scenario: Binary files are flagged
- **WHEN** a commit adds a binary file
- **THEN** its file row has `is_binary` true, `is_generated` true, and null added and deleted counts

#### Scenario: Lockfiles and vendored paths are flagged as generated
- **WHEN** a commit changes `package-lock.json` or a file under `node_modules/`
- **THEN** those file rows have `is_generated` true
- **AND** ordinary source files in the same commit have `is_generated` false

### Requirement: Incremental sync
The system SHALL remember the last synced commit per repository and on later
syncs ingest only commits after it. If the remembered commit is no longer an
ancestor of `HEAD`, the system MUST delete that repository's stored commits and
re-ingest the full history so no stale or duplicate commits remain.

#### Scenario: Only new commits are ingested
- **WHEN** a repository synced earlier gains 3 commits and is synced again
- **THEN** exactly 3 commits are added and no commit is stored twice

#### Scenario: Nothing new
- **WHEN** a repository is synced twice with no upstream changes in between
- **THEN** the second sync reports 0 new commits

#### Scenario: Rewritten history triggers a clean re-sync
- **WHEN** the last synced commit has been removed from the branch by a force-push
- **THEN** the sync reports a full resync
- **AND** the stored commits exactly match the current history

#### Scenario: Empty repository
- **WHEN** a repository with no commits is synced
- **THEN** the sync succeeds, reports 0 commits, and leaves the last-synced marker unset

### Requirement: Credential safety
The system SHALL read an optional access token from the `GITHUB_TOKEN`
environment variable and pass it to git only through process environment. The
token MUST NOT appear in clone URLs, `.git/config`, log output, or error
messages.

#### Scenario: Token never persisted or logged
- **WHEN** a sync runs with `GITHUB_TOKEN` set
- **THEN** the token does not appear in log output
- **AND** the token does not appear in the clone's `config` file

#### Scenario: Git failure message is redacted
- **WHEN** a git command fails and its arguments or output contain the token
- **THEN** the raised error message contains `***` in place of the token

### Requirement: Command line interface
The system SHALL provide an `add-repo` command and a `sync` command. `sync`
SHALL process every registered repository (or one, selected by URL), continue
past a failing repository, and exit non-zero if any repository failed.

#### Scenario: Add and sync
- **WHEN** the user runs `add-repo <url>` and then `sync`
- **THEN** the output reports how many new commits were ingested for that repository

#### Scenario: One repository fails
- **WHEN** one registered repository cannot be cloned and another can
- **THEN** the working repository is still synced
- **AND** the error is written to stderr and the exit code is 1

#### Scenario: Unknown repository selected
- **WHEN** the user runs `sync --repo <url>` for a URL that is not registered
- **THEN** an error naming the URL is written to stderr and the exit code is 1
