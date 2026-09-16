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
