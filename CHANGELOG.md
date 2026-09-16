# Changelog

All notable changes to this project. Format loosely follows Keep a Changelog; versions
follow SemVer and are tagged at the milestones defined in `GIT_WORKFLOW.md` Part 6.

Every entry must contain a **measured number**, not an adjective.

## [Unreleased]

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
