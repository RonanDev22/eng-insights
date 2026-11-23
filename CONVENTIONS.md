# Rules for the implementing model

You are implementing ONE task from `openspec/changes/add-repo-ingestion/tasks.md`.

1. Edit only the single source file named in the task.
2. Never edit anything in `tests/`, never edit `src/eng_insights/models.py`, and never
   change the `SCHEMA` constant in `db.py`.
3. The docstring on each stub is the contract. Follow it exactly, then replace the
   `raise NotImplementedError` with the real code. Keep every signature unchanged.
4. Python standard library only. Do not add dependencies.
5. Keep functions small and typed. Do not add features the docstring does not ask for.
6. Never print, log, or include an access token in any message or exception.
7. Library code does not use `print`. Only `cli.py` prints.
8. If a test fails, read the assertion, then fix the source file. Do not change the test.
