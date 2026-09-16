# Changelog

All notable changes to this project. Format loosely follows Keep a Changelog; versions
follow SemVer and are tagged at the milestones defined in `GIT_WORKFLOW.md` Part 6.

Every entry must contain a **measured number**, not an adjective.

## [Unreleased]

## [0.3.0] - 2026-09-17

N-tuple Stage 1 learns: the first self-taught agent. Run `td-01`; its manifest is in
`runs/td-01/` and its weights are gitignored.

### Added
- N-tuple Stage 1 value network: 4 × 5-tuples with 8-way symmetric updates, TD(0) on
  afterstates, greedy on `r + V(s')`, no exploration bonus, no reward shaping (reward
  is the environment's merge score). 4,194,304 float32 weights = 16.8 MB in memory,
  5.4 MB compressed on disk.
- `python -m game2048.train.td_train --run <id> --games N --seed S`: batched self-play
  trainer (64 games side by side on the bitboard engine). It refuses seeds >= 900000 and
  will not overwrite an existing run.
- `python -m game2048.train.evaluate --agent ntuple --weights <path>`, gate
  `mean >= 15000 and 2048 rate >= 50%`.

### Verified
- Training: 100,000 games, seed 1, 4,251 seconds wall time on the dev machine, numpy
  only, no GPU.
- Training curve, last 1,000 games: mean 64,783, 2048 rate 96.2%.
- Held-out evaluation, seeds 900000..900999, 1,000 games: mean 64,492, median 70,620,
  max 133,928, 2048 rate 96.4%, 4096 rate 77.2%, 8192 rate 3.9%, 0.115 ms/move.
- Max-tile histogram over those 1,000 games: 256: 3 · 512: 8 · 1024: 25 · 2048: 192 ·
  4096: 733 · 8192: 39.
- Gate (SPECS §5, TASK-12): 15,000 mean, 50% 2048 rate. Cleared by 4.3x on mean and
  1.93x on win rate.
- The Stage 1 network already exceeds the Stage 2 gate from SPECS §5 (40,000 mean, 90%
  2048 rate, 50% 4096 rate).
- 300 tests.

## [0.2.0] - 2026-09-16

Baselines built and measured by the shared eval harness. Scores are deterministic from
the seeds; ms/move is from the dev machine.

### Added
- `agents/`: the `Agent` protocol, a seeded random agent, and a greedy 1-ply heuristic
  (empty cells, monotonicity, smoothness, max tile in a corner). The heuristic reads the
  env only through `legal_moves()` and `afterstate()`; a test proves the env is
  byte-identical after `act`.
- `python -m game2048.train.evaluate --agent {random|heuristic} --games N --seed-base S
  [--json]`: mean/median/max score, 2048/4096 rate, max-tile histogram, ms/move, and a
  per-agent gate (exit 1 on fail).
- Seeds 900000+ reserved as the held-out eval range.
- Nightly: baseline eval on both agents, tables uploaded as the `nightly-eval` artifact.

### Verified
- Random, 1000 games, seed-base 900000: mean 1,108, median 1,070, max 3,284, 2048 rate
  0.0%, 0.131 ms/move. Gate `750 <= mean <= 1250`: PASS.
- Heuristic, 1000 games, seed-base 900000: mean 11,548, median 10,644, max 36,828,
  2048 rate 7.0%, 4096 rate 0.0%, 0.339 ms/move. Gate `mean >= 3000 and 2048 rate >= 5%`:
  PASS. 10.4x random.
- Mutation runs: agents 21/21 mutants killed, eval harness 24/24.
- 281 tests across 10 modules.

## [0.1.0] - 2026-09-16

Engine verified. Tagged at `888a6cf`. Every number below comes from CI or nightly on
ubuntu-latest, not from the dev machine.

### Added
- Naive reference engine (`naive.py`) and bitboard engine (`bitboard.py`); both pass
  the same 13 golden row cases (`tests/golden_cases.py`).
- 65536-row move tables built by calling the naive oracle, with nibble-overflow
  sentinels.
- `env.py`: the frozen SPECS §2.3 API, with `IllegalMove`.
- Terminal play: `python -m game2048 play`.
- Differential test (`python -m game2048.bench.differential`) and throughput benchmark
  (`python -m game2048.bench.engine_bench`).
- CI: lint, secret scan, tests on Python 3.11 and 3.12, 5k-game differential, and an
  informational 5-second throughput step. Nightly: 100k differential, 30-second
  throughput gate.

### Verified
- Differential test: 100,000 games, seed 7, 0 divergences (nightly run 35097911041,
  667.5s).
- Throughput: 222,045 moves/sec, 30-second measurement on ubuntu-latest, Python 3.12
  (nightly run 35097911041; gate 200,000).
- 232 tests across 8 modules.

### Known
- `__version__` at the `v0.1.0` tag reads `0.0.0`; the bump to `0.1.0` landed after
  the tag.
