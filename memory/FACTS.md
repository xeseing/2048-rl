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
