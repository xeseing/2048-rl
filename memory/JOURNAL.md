# JOURNAL.md — Session narrative, newest first

One entry per session. Cap 10 entries; roll entries 11+ into a single summary line.

---

### 2026-09-16 — TASK-09 fix, TASK-10, TASK-11, v0.1.0 and v0.2.0
- TASK-10 (#13) and TASK-11 (#14) landed. Held-out baselines, seed-base 900000:
  random mean 1,108; heuristic mean 11,548, 2048 rate 7.0%.
- v0.1.0 tagged at 888a6cf; its release notes were rewritten from the auto-generated
  PR list to the `[0.1.0]` changelog section (#15). v0.2.0 tagged at 9f7f461 (#16).
- ADR-018: the agent and env seeded with the same int draw identical streams, so the
  agent's moves mirrored the spawns. Mitigated with `"{seed}:agent"`; pre-TASK-11
  agent numbers are marked non-comparable in FACTS.
- Throughput: #12 (`empty_cells`) cleared the CI-runner gate at 222,045 moves/sec
  (nightly, 30s, Python 3.12); the next nightly read 273,029, reproducing the pass
  with headroom.
- ADR-021: nightly's `| tee` hid eval-gate failures (the default Actions shell has no
  pipefail). Fixed in #17 before v0.2.0 was tagged.

### 2026-09-15 — TASK-00, attempt 1/4
- Repo was docs-only: no `.git`, no `memory/`, and `ci.yml` / `nightly.yml` /
  `pull_request_template.md` loose in the project root. Moved them under `.github/`
  and moved the seed `DECISIONS.md` into `memory/` rather than duplicating it.
- `git init -b main`; `gh repo create xeseing/2048-rl --public --source=.` → created.
- Scaffold committed on `task/00-repo-setup`, PR opened, left unmerged for review.
- **Open:** TASK-00's own gate says "CI green on first PR", but `ci.yml`'s `test` job
  runs `pip install -e ".[dev]"` and no `pyproject.toml` exists until TASK-01. The
  `test` job is expected red on this PR. Not worked around.
- First CI run also failed `lint`, which I had not predicted: ruff 0.16.7 formats
  Python blocks inside Markdown and objected to `SPECS.md:86`. Fixed via `.ruff.toml`
  + pinned ruff (ADR-002). `lint` and `secret-scan` now pass; `test` stays red on
  `setup-python` finding no `pyproject.toml`, which is TASK-01's deliverable.
- Audit A-1..A-7 applied on the same branch, as directed: `test` job deleted from
  `ci.yml` (no `hashFiles` guards — each task adds its own gate, new CLAUDE.md rule 9);
  Makefile dropped entirely, all gates respelled as raw commands, one per line for
  PowerShell 5.1; package root settled as `game2048` with `agents`/`train`/`bench` as
  subpackages (ADR-006); my duplicate ADR-002 renumbered to ADR-007.
- TASK-10/TASK-11 contents exchanged: agents first, `evaluate.py` second. The old order
  had TASK-10 gated on a random agent that TASK-11 built.
