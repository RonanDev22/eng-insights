## ADDED Requirements

### Requirement: Automatic engineer discovery
The system SHALL ensure that every distinct author email in `commits` (compared
case-insensitively) is mapped to exactly one engineer. Discovery MUST be idempotent and
MUST NOT change existing mappings.

#### Scenario: New email creates an engineer
- **WHEN** discovery runs and `alice@example.com` is not mapped
- **THEN** an engineer exists whose display name is the author name most often used with that email
- **AND** `alice@example.com` is mapped to that engineer

#### Scenario: Email matching ignores case
- **WHEN** commits exist under `Alice@Example.com` and `alice@example.com`
- **THEN** one engineer exists for both and the stored email is lowercase

#### Scenario: Discovery is idempotent
- **WHEN** discovery runs twice with no new commits
- **THEN** the second run creates 0 engineers and 0 mappings

#### Scenario: Manual mappings survive discovery
- **WHEN** an email was merged into another engineer and new commits arrive and discovery runs
- **THEN** that email is still mapped to the engineer it was merged into

### Requirement: GitHub noreply addresses
The system SHALL treat `<digits>+<user>@users.noreply.github.com` and
`<user>@users.noreply.github.com` as the same person, comparing the username
case-insensitively. Other domains are never merged automatically.

#### Scenario: Both noreply forms map to one engineer
- **WHEN** commits exist under `1234+Alice@users.noreply.github.com` and `alice@users.noreply.github.com`
- **THEN** both emails are mapped to a single engineer

#### Scenario: Different users stay separate
- **WHEN** commits exist under `1+alice@users.noreply.github.com` and `2+bob@users.noreply.github.com`
- **THEN** two engineers exist

#### Scenario: Other domains are not merged by username
- **WHEN** commits exist under `alice@users.noreply.github.com` and `alice@example.com`
- **THEN** two engineers exist

### Requirement: Name-based merging
When discovery maps previously unmapped emails, it SHALL map emails to the same engineer
when they share an author name, compared case-insensitively with surrounding whitespace
ignored, and the name contains at least two words. Single-word names (usernames such as
`root` or `alice`) MUST NOT be merged by name. This rule applies only to emails that are
not yet mapped, so it never changes an existing mapping. Discovery SHALL report how many
emails were joined to an existing or sibling engineer by name.

#### Scenario: Same name, different emails
- **WHEN** `kevin@deldycke.com` and `kdeldycke@users.noreply.github.com` both have commits authored as "Kevin Deldycke"
- **THEN** both emails map to one engineer

#### Scenario: Case and spacing are ignored
- **WHEN** commits are authored as "Kevin Deldycke" and " kevin deldycke "
- **THEN** their emails map to one engineer

#### Scenario: Single-word names are not merged
- **WHEN** two unrelated emails both have commits authored as "alice"
- **THEN** two engineers exist

#### Scenario: New email joins an existing engineer
- **WHEN** engineer "Dan Sully" already exists and a new email appears with commits authored as "Dan Sully"
- **THEN** the new email maps to the existing engineer and no new engineer is created

#### Scenario: Existing mappings are never changed by name
- **WHEN** an email was previously unmerged from an engineer and discovery runs again
- **THEN** it stays on its own engineer

### Requirement: Bot detection
The system SHALL flag an engineer as a bot when discovery first creates it and any of
its emails or its display name matches a bot pattern: email local part or name ending in
`[bot]`; email local part or name equal (case-insensitive) to `dependabot`, `renovate`,
`github-actions`, `greenkeeper`, or `snyk-bot`. Manual flag changes MUST persist and
MUST NOT be overridden by later discovery.

#### Scenario: Known bots are flagged
- **WHEN** discovery creates engineers for `49699333+dependabot[bot]@users.noreply.github.com` and `alice@example.com`
- **THEN** the dependabot engineer is flagged as a bot and Alice's is not

#### Scenario: Real-world bot accounts
- **WHEN** discovery sees `27856297+dependabot-preview[bot]@users.noreply.github.com`, `66853113+pre-commit-ci[bot]@users.noreply.github.com`, and `117423508+pre-commit-ci-lite[bot]@users.noreply.github.com`
- **THEN** each is mapped to a separate engineer flagged as a bot
- **AND** these are not name-merged into one another

#### Scenario: Manual override persists
- **WHEN** an engineer is manually marked as a bot (or unmarked) and discovery runs again
- **THEN** the manual setting is unchanged

### Requirement: Merging and renaming engineers
The system SHALL let a user merge one engineer into another, moving every email and
removing the emptied engineer, and rename an engineer. Merging an engineer into itself
or referencing a missing engineer MUST fail with a clear error and change nothing.

#### Scenario: Merge moves all emails
- **WHEN** engineer B (two emails) is merged into engineer A
- **THEN** all of B's emails map to A and engineer B no longer exists

#### Scenario: Merged bot flag
- **WHEN** a bot engineer is merged into a human engineer
- **THEN** the surviving engineer keeps its own bot flag

#### Scenario: Invalid merges are rejected
- **WHEN** a merge names the same engineer twice, or an id that does not exist
- **THEN** a `ValueError` naming the problem is raised and no rows change

#### Scenario: Rename
- **WHEN** an engineer is renamed to "Alice Example"
- **THEN** its display name is "Alice Example" and discovery does not change it later

#### Scenario: Unmerge an email
- **WHEN** an email is unmerged from an engineer that has two emails
- **THEN** a new engineer exists for that email, named after the author name most used with it, and the original engineer keeps its other email

#### Scenario: Invalid unmerge
- **WHEN** the email is unknown, or is the only email of its engineer
- **THEN** a `ValueError` is raised and no rows change

### Requirement: Command line interface
The system SHALL provide commands `discover`, `engineers list`, `engineers merge A B`,
`engineers rename ID NAME`, `engineers unmerge EMAIL`, and `engineers mark-bot ID` / `unmark-bot ID`. The existing
`sync` command SHALL run discovery after syncing and print how many engineers were created.

#### Scenario: Sync runs discovery
- **WHEN** the user runs `sync` on a repository with commits from two authors
- **THEN** the output reports 2 new engineers

#### Scenario: Listing shows commit counts
- **WHEN** the user runs `engineers list`
- **THEN** each engineer is shown with its id, name, bot flag, emails, and commit count
