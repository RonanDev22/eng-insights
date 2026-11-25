## Context

Ingestion stores raw `author_name` and `author_email` on `commits`. This change adds the
layer that groups emails into people. It is deliberately the smallest model that makes
leaderboards correct, and it is shared with `add-activity-queries` (built in parallel).

## Schema contract (shared; do not change without updating both changes)

```sql
CREATE TABLE IF NOT EXISTS engineers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    is_bot INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS engineer_emails (
    email TEXT PRIMARY KEY,                       -- always lowercase
    engineer_id INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_engineer_emails_engineer ON engineer_emails (engineer_id);
```

Commit-to-engineer join: `JOIN engineer_emails ee ON ee.email = lower(c.author_email)`.

## Decisions

1. **Engineer per email, merged later.** Discovery auto-creates one engineer per unmapped
   email so views work immediately; merging fixes the rest. Chosen over an "unmapped"
   queue because it gets to a working leaderboard with zero manual setup.
2. **Not storing an engineer id on commits.** Keeps ingestion untouched, and a merge is
   instant (repoint emails) with no rewrite of commit rows. Cost: a join on a `lower()`
   expression; fine at this scale, add an expression index if it ever shows up.
3. **GitHub noreply normalisation.** Regex `^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$`
   (case-insensitive). The captured username becomes the grouping key within discovery,
   so both forms land on one engineer. Only this domain gets username-based merging.
4. **Bot patterns live as constants** at the top of `identity.py` (same style as
   `classify.py`). Matching strips a trailing `[bot]` and compares the local part or
   display name case-insensitively.
5. **Display name** = most frequent `author_name` for that email (ties: most recent).
   Used only when an engineer is created; renames and merges are never overwritten.
6. **Discovery in one transaction**, using `with conn:` at the call site like `sync_repo`.
   Functions here do not commit.
7. **Merge semantics.** `merge_engineers(conn, keep_id, remove_id)`: validate both exist and
   differ, `UPDATE engineer_emails SET engineer_id = keep`, then delete the removed
   engineer. The survivor's name and bot flag win.

8. **Name-based merging (added after a real run on pallets/click).** In 3,416 commits, ten
   of the top authors each used two emails, e.g. a personal address plus a GitHub noreply
   address whose username differs from the email (`kevin@deldycke.com` and
   `kdeldycke@users.noreply.github.com`). Only the author name links them, so discovery
   joins unmapped emails that share a normalised, multi-word author name. Single-word names
   are excluded because they are usually usernames and collide. Wrong merges are recoverable
   with `unmerge_email`, and discovery reports how many name-merges it performed so they are
   never silent. Author names come from `commits.author_name` (all names seen per email).
   Known risk: two different people with the same full name merge; the unmerge command is the fix.

## Interface (what the next change relies on)

`src/eng_insights/identity.py`:

- `normalise_email(email: str) -> str`: lowercase, stripped.
- `noreply_username(email: str) -> str | None`
- `looks_like_bot(name: str, email: str) -> bool`
- `discover_engineers(conn) -> DiscoveryResult`: `created` (engineers created) and `name_merged`
  (emails joined to another engineer by author name).
- `merge_engineers(conn, keep_id: int, remove_id: int) -> None`
- `unmerge_email(conn, email: str) -> int`: returns the new engineer id.
- `rename_engineer(conn, engineer_id: int, name: str) -> None`
- `set_bot(conn, engineer_id: int, is_bot: bool) -> None`
- `list_engineers(conn) -> list[sqlite3.Row]`: id, display_name, is_bot, emails (comma-joined), commit_count.

## Risks / Trade-offs

- Two people sharing one email (shared CI accounts) collapse into one engineer; fixable only
  by tooling we have not built. Acceptable.
- Squash merges credit the merger; co-author trailers are not parsed yet.
- A person using unrelated emails needs a manual merge. `engineers list` sorted by
  commit count makes the big ones easy to spot.

## Open Questions

- Do you want a "suggested merges" list (same display name, different emails)? Easy to add later.
