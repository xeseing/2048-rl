# FACTS.md — Verified truths about this codebase

Edit in place. If a line here is contradicted by evidence, fix the line and append an
ADR to `DECISIONS.md` saying what changed. Never leave two contradictory facts on file.
Nothing goes here that was not produced by a command that ran. Cap ~60 lines.

---

- `ruff format` (>=0.16) formats Python code blocks inside Markdown files. Repo excludes
  `*.md` via `.ruff.toml`. Config must stay in `.ruff.toml`, never `pyproject.toml`:
  `.ruff.toml` wins and would shadow it. (ADR-007)
- CI pins `ruff==0.16.7`. Unpinned linters make CI red with no commit to blame.
- Dev machine (win32): Python 3.11.7, numpy 2.4.4, pytest 9.1.1 already importable.
  `make` is NOT installed and there is no Makefile — every gate is spelled as the raw
  command it runs. The shell is PowerShell 5.1, where `&&` is a parse error, so chained
  commands are written one per line.
- `ci.yml` runs `lint` + `secret-scan` only as of TASK-00. The deleted `test` job
  invoked `bench.differential` and `bench.engine_bench`, which do not exist until
  TASK-08/09, so it could not have gone green before TASK-09. Each task now adds its own
  gate in its own PR; no `hashFiles` guards, because a skipped gate reports green while
  testing nothing. (CLAUDE.md version-control rule 9)
- The only importable root is `game2048`; `agents`, `train` and `bench` are subpackages
  of it. A `python -m` path starting `src.` or bare `bench.` does not work from an
  installed wheel. (ADR-006)
- Package installs as distribution `2048rl`, import root `game2048`, built by hatchling
  from `src/`. Version is single-sourced from `src/game2048/__init__.py` via
  `[tool.hatch.version]`; `pyproject.toml` carries no version string. (ADR-008)
- The `pytest` console script is NOT on PATH outside `.venv` on this machine — bare
  `pytest` raises CommandNotFoundException in PowerShell. Activate `.venv` first, or use
  `python -m pytest`. Same applies to `ruff`.
