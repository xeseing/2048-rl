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
- `naive.py` is the oracle. `move(board, direction)` returns
  `(new_board, score_gained, changed)` and never spawns — it is the afterstate half
  of a turn. An illegal move returns the board unchanged with score 0; raising is
  `env.py`'s job. Boards are `list[list[int]]` of tile values, never exponents, and
  every function returns a new board rather than mutating its argument.
- `slide_row_left` is the only sliding code in the naive engine; the other three
  directions go through `_to_left_frame` / `_from_left_frame`. A bug in the slide is
  therefore visible in all four directions at once, never in just one. (ADR-009)
- `spawn()` draws cell first, then value. That order is part of what a seed
  reproduces — swapping it invalidates every recorded transcript.
- The score invariant is `score == Σ w(tile on board) - Σ w(spawned tile)` with
  `w(v) = v·(log₂v - 1)` (`v * (v.bit_length() - 2)` for powers of two). The
  unweighted form is identically 0: a merge conserves the board's tile sum, so
  `sum(tiles) == sum(spawned)` always. Measured on seed 0: score 2260, sum(tiles) 420,
  sum(spawned) 420, weighted difference 2260. (ADR-010)
- Chi-square uniformity in the tests compares the statistic against tabulated
  alpha=0.01 critical values (df 15 -> 30.578, df 4 -> 13.277) rather than computing a
  p-value; scipy is not a dependency and an incomplete gamma in a test file is not
  worth owning.
- `Env.step()` checks legality and raises `IllegalMove` before assigning anything, so
  a rejected move cannot have spawned or scored. Proved by a mutant that spawns first
  and raises second: it passes a naive "board unchanged" check and is caught only by
  comparing a fingerprint that includes the RNG state. (`tests/test_env.py`)
- `Env.afterstate()` is pure because `naive.move` builds a fresh board and touches no
  RNG — purity is structural, not a promise the method keeps by being careful. The
  test that guards it compares `env._rng.getstate()`, which is what makes "did not
  spawn" provable rather than plausible.
- `Env.reset(seed=None)` continues the existing RNG stream rather than reseeding, so a
  run of many games stays reproducible from the one seed the env was built with.
  `reset(seed=k)` replaces the RNG.
- `Env`'s spawn stream is identical to driving `naive` directly from the same seed —
  the env adds no hidden draws. Pinned by
  `test_the_env_spawns_exactly_what_the_naive_engine_would_from_the_same_seed`.
- Windows sends arrow keys as TWO bytes: a 0xe0 or 0x00 prefix, then a scan code
  (H up, P down, K left, M right). A bare b"H" is the letter H, not an arrow. POSIX
  terminals send the same keys as 3-byte ANSI sequences (ESC [ A/B/C/D). `app.decode`
  is a pure function over those byte sequences, split from the terminal I/O that
  feeds it, so CI tests it on Linux without a terminal. (ADR-012)
- `msvcrt` / `termios` are imported inside `read_key_from_terminal`, never at module
  scope. A top-level `import msvcrt` makes `game2048.app` unimportable on the Linux
  CI runner and every test in the file collapses at collection.
- Everything in `render.py` returns a string and nothing there prints; all printing is
  in `app.py`. `Env.render()` delegates to `render.frame`. Guarded by a capsys test.
- `python -m game2048 play --seed N` is the entry point as of TASK-05;
  `[project.scripts] 2048rl` is still deliberately absent until TASK-19 (ADR-008).
- **Stale `.pyc` can keep a reverted mutant alive.** A `.pyc` is validated against the
  source's mtime *truncated to one second* and its byte size. A mutate/run/restore
  cycle finishes well inside one second, and `print(x)` is exactly as many bytes as
  `return x`, so both checks matched and Python went on executing the mutant after
  `env.py` had been restored byte-for-byte. Symptom: `Env.render()` returned `None` and
  printed, while `inspect.getsource` showed the correct code — `getsource` reads the
  `.py`, not the loaded bytecode, so it cannot detect this. Any mutation harness must
  run its subprocess with `PYTHONDONTWRITEBYTECODE=1` and delete `src/**/__pycache__`
  around each mutant. Running the full suite after a mutation run catches it too.
- Row encoding: 4 nibbles of log2(tile), 16 bits, **cell 0 in the highest nibble**, so
  a row reads left-to-right in hex — `[2, 4, 8, 16]` is `0x1234`. Nibble 0 is empty,
  15 is 32768.
- `build_tables()` looks the oracle up as `naive.slide_row_left` at call time, not by
  importing the name, so a test can swap the oracle and prove the build delegates
  rather than carrying its own merge rule. A *correct* hand-written build passes all
  65536 exhaustive comparisons and is caught only by that test. (ADR-013)
- 767 of the 65536 rows slide into a tile above the 32768 nibble ceiling (two adjacent
  32768s). Those entries hold `OVERFLOW_ROW` (`0xFFFF`) and `OVERFLOW_SCORE`
  (`-1_000_000_000`); `row_left()` / `row_score()` raise `NibbleOverflow` on them and
  `is_overflow(row)` reports them. Verified: the sentinel set equals the set of rows
  whose naive result exceeds 32768, and no legitimate entry equals either sentinel.
- The sentinels are deliberately loud, because the bitboard engine indexes the tables
  raw for speed and a forgotten check must not corrupt quietly. `0xFFFF` decodes to
  four 32768s, which no slide can ever produce, so a board that picks it up is
  obviously wrong; a `-1` score would instead have shifted a real total by one per
  lookup. (ADR-013)
- Building both tables costs 0.140s at import and ~1.0 MB resident. No on-disk cache
  yet; `.gitignore` already anticipates `_tables_cache.npy` if that ever matters.
- Bitboard packing: 16 nibbles of log2(tile), row-major, cell (0,0) in the **highest**
  nibble. Row `r` occupies bits `16*(3-r)..16*(3-r)+15`, so a row lifted straight out
  of a board is exactly the 16-bit key `tables.ROW_LEFT` is indexed by — no shuffling
  between the board layout and the table layout.
- `bitboard.py` mirrors `naive.py`'s structure move for move (reorient, slide, reorient
  back) so the two can be read side by side. Only the row slide differs: a table lookup
  instead of compress/merge/compress.
- `bitboard._slide_left` checks `tables.OVERFLOW_ROW` **before** using the looked-up
  value, on every row, so all four directions are covered by one check. A mutant that
  guarded only the `left` path passes 42 of 47 tests and is caught solely by the
  per-direction overflow tests. (ADR-013)
- `bitboard.spawn` draws cell first, value second, and `empty_cells` returns row-major
  indices — identical to `naive.spawn`, so both engines consume the same RNG stream
  from the same seed. `test_spawn_consumes_the_rng_exactly_as_the_naive_engine_does`
  asserts `rng.getstate()` matches after 16 spawns. TASK-08's differential test depends
  on this.
- Golden test values live once, in `tests/golden_cases.py`, and are read by both
  engines' test modules. Neither file re-types an expected board.
- **First differential proof point:** `python -m game2048.bench.differential
  --games 100000 --seed 7` → 0 divergences, 1449.8s, 14.5ms per game. Re-run on the
  TASK-09 engine: same seed, same 0 divergences, 589.3s. Nightly's 60-minute timeout
  is comfortable. Games use seeds
  `7..100006`; each game seeds the naive RNG, the bitboard RNG and the move policy
  independently and deterministically, so any single game replays from its own seed.
  The CI fast lane is the same command with `--games 5000 --seed 1234`: 40.2s on an
  otherwise idle dev machine, so it adds well under a minute to each `test` job.
- The differential harness compares **all four directions every step**, not just the
  move taken: board, score and `changed` for each, then `legal_moves`, then the board
  after the spawn, then the running score. That is 8 move computations per step;
  calling `legal_moves` and `is_game_over` on both engines instead would be 20 for the
  same answer.
- Each engine gets its **own** RNG seeded identically, rather than sharing one. An
  engine that consumed a different number of draws per spawn would then diverge
  visibly instead of being hidden by a shared stream. (ADR-015)
- The differential test cannot catch a bug both engines share, and `tables.py` is
  built by calling `naive.slide_row_left`, so a wrong merge rule is wrong identically
  on both sides and passes in silence. The golden tests in `tests/golden_cases.py`,
  hand-computed from SPECS and never captured from an implementation, are what cover
  that. `test_a_bug_shared_by_both_engines_is_invisible_here` pins the limitation.
- **Engine throughput after TASK-09:** seven 15s runs on a quiet dev machine (Windows
  AMD64, Intel Family 6 Model 183, CPython 3.11.7) gave min 236,847, median 267,359,
  max 276,410 applied moves/sec against the 200,000 gate. A "move" here is an applied
  board transition, not an engine call; the benchmark tries a random rotation of the
  four directions and applies the first legal one, about 1.3 calls per counted move.
- **That machine is too noisy to trust a single benchmark run.** Contended readings
  during the same session ranged from 79,729 to 276,486 moves/sec — a 3.5x spread —
  with no code change between them. Always take several runs and report the spread;
  a single number from this box means nothing. (ADR-016)
- Optimisation results, each measured with `--seconds 10` before and after:
  `transpose` mask-and-shift 44,704 → 68,273; `_reverse_rows` mask-and-shift
  68,273 → 111,596; `ROW_RIGHT` table 111,596 → 273,918. Component costs after:
  `transpose` 0.38us, `_reverse_rows` 0.28us, `_slide_left` 0.63us, `move` 0.86–1.86us
  by direction, `spawn` 1.89us of which `empty_cells` was 1.58us.
- `empty_cells` is now one mask (OR each nibble onto its low bit, invert against
  `0x1111...`) plus a walk over the set flags, highest first: 1.37us → 0.47us per call,
  same row-major order and RNG stream. In-process A/B (20 × 1.5s slices alternating
  old/new): median 172,206 → 190,780 moves/sec, ratio 1.108. (#12, ADR-019)
- A 4 × 65536 table of empty-cell tuples was faster still (0.22us) but cost 0.61s at
  import and 6.3 MB, so it was not taken.
- Table storage (candidate 5) measured: tuple 15.7ns and list 15.3ns per lookup,
  `array.array('H')` 23.1ns. No gain available; tuples stay.
- **The dev machine does not predict the CI runner.** After TASK-09 the dev median was
  267k, but ubuntu-latest's 5s smoke step read 194,166 / 174,191 / 192,783 / 229,129.
  After #12: smoke 247,839 (3.11) / 289,658 (3.12); nightly 30s gate on 3.12
  (run 35097911041) **222,045 moves/sec, PASS**. That nightly number is the tagged one
  (v0.1.0). Check CI's own number before claiming headroom.
- Nightly run 35097911041 (commit a58cd11, tree-identical to main 888a6cf):
  differential 100,000 games, seed 7, 0 divergences, 667.5s on ubuntu-latest.
- v0.1.0 is tagged at 888a6cf, but `__version__` there still reads `0.0.0`; the bump
  landed after the tag.
- `tables.py` now also builds `ROW_RIGHT` / `ROW_SCORE_RIGHT` by mirroring the left
  tables. Import cost is roughly double TASK-06's 0.14s and about 2 MB resident, in
  exchange for `right` being a plain lookup and `down` being transpose-lookup-transpose.
- **Baselines (TASK-10), plain loop, seeds 0–999, naive-backed `Env`:** random mean
  1,084 (median 1,064, max 3,264, 0% 2048); heuristic mean 11,577 (median 10,544,
  max 43,356, 2048 rate 7.4%, 1024 rate 51.8%). Zero `IllegalMove` from either.
  1000 heuristic games take ~76s on the dev machine. Weights and why: ADR-017.
- The heuristic's lever is smoothness: raising its weight from 0.1 to 0.5 took the mean
  from 7,765 to 11,708 on tuning seeds; empty/monotonicity/corner weights barely mattered.
- `heuristic.act` holds TASK-04's afterstate-purity guarantee in practice: the env's
  fingerprint (RNG state included) is unchanged across 300 consecutive `act` calls.
  A mutant that draws one number from `env._rng` is caught only by that fingerprint.
- Tests reuse `fingerprint`, `with_board`, `WEDGED`, `DEAD` by `from test_env import ...`
  (tests/ is on sys.path, as for `golden_cases`); no copies.
- A monotonicity mutant that checked rows only survived a suite whose boards were all
  symmetric in rows and columns. Feature tests need at least one board where rows and
  columns disagree.
- **Agent numbers from before TASK-11 used correlated seeds** (`RandomAgent(seed=s)`
  with `Env(seed=s)`): TASK-10's random 1,084 / heuristic 11,577 on seeds 0–999 are
  kept as measured but are not comparable to eval-harness output. (ADR-018)
- The random gate is 750–1250 (ADR-020); held-out random mean 1,108 sits mid-range.
- **Held-out eval seeds are 900000+** (CLAUDE.md hard constraints). Tests use 4200+,
  heuristic tuning used 5000–6299.
- **Eval harness, 1000 games, seed-base 900000 (TASK-11):** random mean 1,108, median
  1,070, max 3,284, 0.141 ms/move; heuristic mean 11,548, median 10,644, max 36,828,
  2048 rate 7.0%, 4096 rate 0%, 0.339 ms/move, 239s on the dev machine. Both gates
  pass. Heuristic/random = 10.4x.
- The GitHub Actions default `run:` shell on Linux is `bash -eo pipefail`, which is what
  lets nightly `| tee` an eval table without swallowing the gate's exit code.
