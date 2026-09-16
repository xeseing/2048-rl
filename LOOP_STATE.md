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
| `TASK-03` | Spawn + determinism tests (0.9/0.1, uniform empties, seeded replay) | P0 | chi-square p > 0.01; identical transcripts; score invariant | [x] DONE | #4 (b06a7c0) |
| `TASK-04` | `env.py` with the frozen API from SPECS §2.3, `IllegalMove` raise | P0 | Illegal move: no spawn, no score, raises, env byte-identical | [x] DONE | #5 (9bdc4d0) |
| `TASK-05` | Terminal render + `python -m game2048 play` (human playable; the `2048rl` script is TASK-19) | P2 | Manual: play one game to game-over | [x] DONE | #6 (e5b85c5) |
| `TASK-06` | `tables.py`: 65536-row tables built from the naive oracle | P0 | Table entries == naive row moves, all 65536 | [x] DONE | #8 (c724377) |
| `TASK-07` | `bitboard.py`: uint64 board, transpose, 4 directions, overflow assert | P0 | Golden tests pass on bitboard engine too | [x] DONE | #9 (88aee30) |
| `TASK-08` | **Differential test**: 100k random games, naive vs bitboard; adds the 5k differential step to `ci.yml` | P0 | `python -m game2048.bench.differential --games 100000 --seed 7` — zero divergences | [x] DONE | #10 (8b8f7a4) |
| `TASK-09` | Throughput benchmark; informational smoke step in `ci.yml`, full gate in `nightly.yml`; **re-enabled nightly's `schedule:` trigger** | P1 | `python -m game2048.bench.engine_bench --seconds 30 --gate 200000` ≥ 200,000 moves/sec | [x] DONE | #11 |
| `TASK-10` | Random + heuristic 1-ply agents | P1 | 1000 seeded games each via a plain loop (no eval harness yet): zero `IllegalMove` raised; heuristic mean ≥ 3,000 and ≥ 10× random | [x] DONE | #13 |
| `TASK-11` | `evaluate.py`: 1000 held-out seeds → score stats + max-tile histogram; **re-enables nightly's baseline-eval step**, commented out in TASK-09 because the module did not exist | P0 | Random agent reports ~1,000 mean over 1000 held-out seeds | [x] DONE | #14 |
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

### Optimisation candidates — TASK-09 outcome

Profiled, then taken in order, measuring after each. **Stopped at candidate 3**, which
cleared the gate with headroom; 4, 5 and 6 expired untaken.

| # | Candidate | Outcome |
| :-- | :-- | :-- |
| 1 | `transpose` mask-and-shift instead of a 16-iteration loop | **taken** — 44,704 → 68,273 moves/sec; `transpose` 3.16us → 0.38us |
| 2 | `_reverse_rows` mask-and-shift | **taken** — 68,273 → 111,596; `_reverse_rows` 2.04us → 0.28us |
| 3 | `ROW_RIGHT` table, deleting reversals from `right`/`down` | **taken** — 111,596 → 273,918 |
| 4 | `legal_moves` single pass | expired — gate cleared first, and the benchmark loop calls `move` directly so this was never on the measured path |
| 5 | Table storage: tuple vs list vs `array.array` | measured in #12, not taken — tuple 15.7ns, list 15.3ns, `array.array` 23.1ns per lookup |
| 6 | (warning only: do not "optimise" `moved == board`) | still stands |

**The profile moved as the work progressed.** After 1 and 2, the largest single cost
per applied move was `spawn` at 1.89us, of which `empty_cells` was 1.58us.

**Reopened (#12).** The dev-machine headroom did not survive the CI runner: its smoke
step read 174k–229k. `empty_cells` became a single mask (1.37us → 0.47us; in-process A/B
+10.8%), and nightly's 30s gate on the branch then read **222,045 moves/sec, PASS**
(run 35097911041). Accepted at 222k; 240k is not being chased (ADR-019).

---

**Do not start TASK-12 before TASK-08 and TASK-09 are green.** Training on an unverified
or slow engine is the single most expensive mistake available in this project.

---

## 🧪 Verification Log & Feedback Scratchpad
<!-- Keep only the latest attempt. Older failures belong in memory/FAILURES.md -->

### Current Active Task: `TASK-11`
- **Branch:** `task/11-evaluate` (#14)
- **Attempt:** 1 / 4
- **Last Verification Result:** `pytest -q` → 281 passed; ruff clean.
  `evaluate --agent random --games 1000 --seed-base 900000` → mean 1,108, gate PASS,
  exit 0. `--agent heuristic` same seeds → mean 11,548, 2048 rate 7.0%, gate PASS,
  exit 0. Out-of-range proof through the real CLI: heuristic in the random slot
  (mean 12,034) and first-legal-move "random" (mean 818) both FAIL, exit 1.
  Mutation run: 24 mutants, 24 killed (5 survived the first pass; tests fixed).
- **Command Run:** `pytest -q` / `ruff check .` / `ruff format --check .` / the two
  eval commands above
- **Errors / Tracebacks:** `None`
- **Corrective Action Plan:** `None`.

---

## 🏁 Shipped Deliverables & Metrics
- **Latest Tag:** v0.1.0 (888a6cf)
- **CI Status on `main`:** `lint` + `test` + `secret-scan` (each later task adds its own gate)
- **Passing Tests:** 281 / 281
- **Lint Status:** clean (`ruff` 0.16.7)
- **Engine Throughput:** 222,045 moves/sec, nightly 30s on ubuntu-latest / Python 3.12 (gate: 200,000)
- **Differential Test:** 100,000 games, seed 7 — 0 divergences (TASK-08)
- **Best Agent:** — (baselines only, held-out seeds 900000+: heuristic 11,548 mean, 7.0% 2048; random 1,108)
- **Milestones Completed:** None
