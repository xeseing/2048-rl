# 🔄 LOOP STATE & ROADMAP

## Project Overview
- **Objective:** 2048 engine + an agent that learns to play it from self-play (N-tuple TD network, plus a DQN track for comparison), shipped as an installable app.
- **Repo:** `github.com/xeseing/2048-rl` · **Branch model:** `task/<NN>-<slug>` → PR → squash to `main`
- **Current Phase:** Phase 0 — TASK-00 in flight (attempt 1/4)
- **Circuit Breaker Limit:** 4 retries per task
- **Contract:** `SPECS.md` · **Knowledge:** `memory/` · **Rules:** `CLAUDE.md` · **Git:** `GIT_WORKFLOW.md`

---

## 📋 Task Register & Verification Matrix

| Task ID | Description | Priority | Verification Method | Status | PR / Commit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-00` | Git init, GitHub repo created, `.gitignore`, CI + nightly workflows, PR template, branch protection on `main` | P0 | `gh repo view` succeeds; CI green on first PR | [x] DONE | #1 (29993a6) |
| `TASK-01` | Repo skeleton, `pyproject.toml` (`game2048` package + `[dev]` extra), ruff, pytest, one trivial passing test; adds the `test` job to `ci.yml` | P0 | `pytest -q` exits 0; `ruff check .` + `ruff format --check .` clean | [x] DONE | #2 (1b1402e) |
| `TASK-02` | Naive engine: `move_left` + rotations, spawn, score, game-over | P0 | Golden move tests, merge-once, edge-order | [x] DONE | #3 (6d4a9b2) |
| `TASK-03` | Spawn + determinism tests (0.9/0.1, uniform empties, seeded replay) | P0 | chi-square p > 0.01; identical transcripts; score invariant | [x] DONE | #4 |
| `TASK-04` | `env.py` with the frozen API from SPECS §2.3, `IllegalMove` raise | P0 | Illegal move: no spawn, no score, raises | [ ] PENDING | — |
| `TASK-05` | Terminal render + `2048rl play` (human playable) | P2 | Manual: play one game to game-over | [ ] PENDING | — |
| `TASK-06` | `tables.py`: 65536-row tables built from the naive oracle | P0 | Table entries == naive row moves, all 65536 | [ ] PENDING | — |
| `TASK-07` | `bitboard.py`: uint64 board, transpose, 4 directions, overflow assert | P0 | Golden tests pass on bitboard engine too | [ ] PENDING | — |
| `TASK-08` | **Differential test**: 100k random games, naive vs bitboard; adds the 5k differential step to `ci.yml` | P0 | `python -m game2048.bench.differential --games 100000 --seed 7` — zero divergences | [ ] PENDING | — |
| `TASK-09` | Throughput benchmark; adds the throughput gate to `ci.yml` and the heavy steps to `nightly.yml`; **re-enables nightly's `schedule:` trigger**, commented out in TASK-01 because the modules it invokes did not exist | P1 | `python -m game2048.bench.engine_bench --seconds 30 --gate 200000` ≥ 200,000 moves/sec | [ ] PENDING | — |
| `TASK-10` | Random + heuristic 1-ply agents | P1 | 1000 seeded games each via a plain loop (no eval harness yet): zero `IllegalMove` raised; heuristic mean ≥ 3,000 and ≥ 10× random | [ ] PENDING | — |
| `TASK-11` | `evaluate.py`: 1000 held-out seeds → score stats + max-tile histogram | P0 | Random agent reports ~1,000 mean over 1000 held-out seeds | [ ] PENDING | — |
| `TASK-12` | **N-tuple Stage 1**: 4×5-tuples, symmetries, TD(0) afterstate loop | P0 | 100k games → ≥ 15,000 mean, ≥ 50% 2048 | [ ] PENDING | — |
| `TASK-13` | **N-tuple Stage 2**: 4×6-tuples, checkpointing, resume | P0 | 1M games → ≥ 40,000 mean, ≥ 90% 2048 | [ ] PENDING | — |
| `TASK-14` | Expectimax depth-3 reference ceiling | P2 | ≥ 20,000 mean, ≥ 80% 2048 | [ ] PENDING | — |
| `TASK-15` | **DQN Track B**: one-hot planes, (2,1)/(1,2) convnet, Double DQN | P1 | Smoke run 10k steps, loss finite, no NaN | [ ] PENDING | — |
| `TASK-16` | DQN full run + honest write-up vs Track A | P1 | ≥ 3,000 mean; comparison table produced | [ ] PENDING | — |
| `TASK-17` | Watch mode: replay a trained agent's game in the terminal | P2 | Manual: visibly builds toward a corner | [ ] PENDING | — |
| `TASK-18` | `RESULTS.md`: all 6 agents, same 1000 seeds, with analysis | P1 | Table complete, every number reproducible | [ ] PENDING | — |
| `TASK-19` | `2048rl` CLI entry point + packaging (`pyproject.toml`, extras groups) | P1 | Clean-venv `pip install .` then `2048rl play` works | [ ] PENDING | — |
| `TASK-20` | `fetch-weights`: download from GitHub Release, SHA-256 verify, cache | P1 | Fresh machine: fetch → `2048rl watch` plays trained | [ ] PENDING | — |
| `TASK-21` | Rich TUI polish: coloured tiles, live value estimates in `watch` | P2 | Manual; also renders with `--no-color` | [ ] PENDING | — |
| `TASK-22` | README with asciinema demo, results table, CI badge | P1 | Numbers match `RESULTS.md` exactly | [ ] PENDING | — |
| `TASK-23` | Release `v1.0.0`: tag, release notes, weights uploaded as assets | P1 | `pip install git+...` on clean machine → works | [ ] PENDING | — |

**Dependency spine:** 00 → 01 → 02 → 03 → 04 → {05, 06} → 07 → 08 → 09 → 10 → 11 → 12 → 13 → {14, 15} → 16 → 17 → 18 → 19 → {20, 21, 22} → 23

The spine still reads in ascending order, but **TASK-10 and TASK-11 exchanged their
contents**: agents are now TASK-10, `evaluate.py` is now TASK-11. The old order was
circular - TASK-10 built `evaluate.py` and was gated on "random agent reports ~1,000
mean", while the random agent was not built until TASK-11, so TASK-10 could never pass
its own gate.

**Version tags:** v0.1.0 after TASK-09 · v0.2.0 after TASK-11 (baselines are built in
TASK-10 and first measured by the TASK-11 eval harness — same milestone as before, both
tasks renumbered by the swap above) · v0.3.0 after TASK-12 · v0.4.0 after TASK-13 · v0.5.0 after TASK-16 · v1.0.0 after TASK-23

**Do not start TASK-12 before TASK-08 and TASK-09 are green.** Training on an unverified
or slow engine is the single most expensive mistake available in this project.

---

## 🧪 Verification Log & Feedback Scratchpad
<!-- Keep only the latest attempt. Older failures belong in memory/FAILURES.md -->

### Current Active Task: `TASK-03`
- **Branch:** `task/03-spawn-determinism` (#4)
- **Attempt:** 1 / 4
- **Last Verification Result:** `pytest -q` → 49 passed; `ruff check .` → All checks
  passed; `ruff format --check .` → 5 files already formatted. Four mutants of
  `naive.py` were each caught by the intended test (see PR body).
- **Command Run:** `pytest -q` / `ruff check .` / `ruff format --check .`
- **Errors / Tracebacks:** `None`
- **Corrective Action Plan:** `None` — awaiting merge approval.

---

## 🏁 Shipped Deliverables & Metrics
- **Latest Tag:** none
- **CI Status on `main`:** `lint` + `test` + `secret-scan` (each later task adds its own gate)
- **Passing Tests:** 49 / 49
- **Lint Status:** clean (`ruff` 0.16.7)
- **Engine Throughput:** — moves/sec (gate: 200,000)
- **Differential Test:** NOT RUN
- **Best Agent:** — (mean score —, 2048 rate —)
- **Milestones Completed:** None
