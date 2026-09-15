# FACTS.md — Verified truths about this codebase

Edit in place. If a line here is contradicted by evidence, fix the line and append an
ADR to `DECISIONS.md` saying what changed. Never leave two contradictory facts on file.
Nothing goes here that was not produced by a command that ran. Cap ~60 lines.

---

(empty — no code exists yet)

- `ruff format` (>=0.16) formats Python code blocks inside Markdown files. Repo excludes
  `*.md` via `.ruff.toml`. Config must stay in `.ruff.toml`, never `pyproject.toml`:
  `.ruff.toml` wins and would shadow it. (ADR-002)
- CI pins `ruff==0.16.7`. Unpinned linters make CI red with no commit to blame.
- Dev machine (win32): Python 3.11.7, numpy 2.4.4, pytest 9.1.1 already importable.
  `make` is NOT installed — every `make <target>` gate in CLAUDE.md is unrunnable
  locally until that is resolved. CI (ubuntu) has make but never calls it; `ci.yml`
  and `nightly.yml` invoke the underlying commands directly.
- CI `test` job runs `python -m bench.differential` and `python -m bench.engine_bench`
  on every PR. Those modules do not exist until TASK-08/TASK-09, so the `test` job is
  red on every PR from TASK-00 through TASK-07 as `ci.yml` is currently written.
