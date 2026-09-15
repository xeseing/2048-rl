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
| `TASK-00` | Git init, GitHub repo created, `.gitignore`, CI + nightly workflows, PR template, branch protection on `main` | P0 | `gh repo view` succeeds; CI green on first PR | [~] IN PROGRESS | `task/00-repo-setup` |
| `TASK-01` | Repo skeleton, `pyproject.toml`, Makefile, ruff, pytest, one trivial passing test | P0 | `make test` exits 0, `make lint` clean | [ ] PENDING | — |
| `TASK-02` | Naive engine: `move_left` + rotations, spawn, score, game-over | P0 | Golden move tests, merge-once, edge-order | [ ] PENDING | — |
| `TASK-03` | Spawn + determinism tests (0.9/0.1, uniform empties, seeded replay) | P0 | chi-square p > 0.01; identical transcripts | [ ] PENDING | — |
| `TASK-04` | `env.py` with the frozen API from SPECS §2.3, `IllegalMove` raise | P0 | Illegal move: no spawn, no score, raises | [ ] PENDING | — |
| `TASK-05` | Terminal render + `make play` (human playable) | P2 | Manual: play one game to game-over | [ ] PENDING | — |
| `TASK-06` | `tables.py`: 65536-row tables built from the naive oracle | P0 | Table entries == naive row moves, all 65536 | [ ] PENDING | — |
| `TASK-07` | `bitboard.py`: uint64 board, transpose, 4 directions, overflow assert | P0 | Golden tests pass on bitboard engine too | [ ] PENDING | — |
| `TASK-08` | **Differential test**: 100k random games, naive vs bitboard | P0 | `make diff-test` — zero divergences | [ ] PENDING | — |
| `TASK-09` | Throughput benchmark | P1 | `make bench` ≥ 200,000 moves/sec | [ ] PENDING | — |
| `TASK-10` | `evaluate.py`: 1000 held-out seeds → score stats + max-tile histogram | P0 | Random agent reports ~1,000 mean | [ ] PENDING | — |
| `TASK-11` | Random + heuristic 1-ply agents | P1 | Heuristic ≥ 3,000 mean, beats random 10x | [ ] PENDING | — |
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

**Version tags:** v0.1.0 after TASK-09 · v0.2.0 after TASK-11 · v0.3.0 after TASK-12 · v0.4.0 after TASK-13 · v0.5.0 after TASK-16 · v1.0.0 after TASK-23

**Do not start TASK-12 before TASK-08 and TASK-09 are green.** Training on an unverified
or slow engine is the single most expensive mistake available in this project.

---

## 🧪 Verification Log & Feedback Scratchpad
<!-- Keep only the latest attempt. Older failures belong in memory/FAILURES.md -->

### Current Active Task: `TASK-00`
- **Branch:** `task/00-repo-setup`
- **Attempt:** 0 / 4
- **Last Verification Result:** NOT STARTED
- **Command Run:** `None`
- **Errors / Tracebacks:** `None`
- **Corrective Action Plan:** `None`

---

## 🏁 Shipped Deliverables & Metrics
- **Latest Tag:** none
- **CI Status on `main`:** not yet configured
- **Passing Tests:** 0 / 0
- **Lint Status:** —
- **Engine Throughput:** — moves/sec (gate: 200,000)
- **Differential Test:** NOT RUN
- **Best Agent:** — (mean score —, 2048 rate —)
- **Milestones Completed:** None
