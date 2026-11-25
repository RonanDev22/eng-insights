## 1. Schema

- [ ] 1.1 Append the `engineers` / `engineer_emails` DDL from design.md to `SCHEMA` in `src/eng_insights/db.py`. Done when: existing `tests/test_db.py` still passes and the tables exist after `init_schema`.

## 2. Pure helpers (no database)

- [ ] 2.1 `normalise_email`, `noreply_username`, `looks_like_bot` in `src/eng_insights/identity.py`, with `tests/test_identity_helpers.py` covering every scenario above that is pure.

## 3. Discovery and management

- [ ] 3.1 `discover_engineers` with tests: new email, case-insensitive, idempotent, noreply merging, bots, manual overrides survive.
- [ ] 3.2 `merge_engineers`, `rename_engineer`, `set_bot`, `list_engineers` with tests: merge moves emails, invalid merges raise and change nothing, rename persists.

## 4. CLI

- [ ] 4.1 Add `discover` and `engineers` subcommands to `src/eng_insights/cli.py`; make `sync` call `discover_engineers` after syncing and print the count. Tests in `tests/test_cli_identity.py`.

## 5. Wrap-up

- [ ] 5.1 Full `pytest` and `ruff check src` green.
- [ ] 5.2 Review against the spec scenarios, then `openspec validate add-identity-mapping` and archive.

> Parallel note: tasks 1.1 and 2.1 are independent. 3.x needs 1.1. 4.1 needs 3.x.
