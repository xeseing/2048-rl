# DECISIONS.md — Architecture decision log

**APPEND ONLY.** Never edit or delete a past entry. If a decision is reversed, append a
new entry that supersedes it and say so.

Format:
### ADR-NNN — <title> (YYYY-MM-DD)
- **Context:** what forced a choice
- **Decision:** what was chosen
- **Rejected:** what was not chosen, and why
- **Consequence:** what this now costs or enables

---

### ADR-001 — Two engines, not one (seed)
- **Context:** RL needs millions of moves/sec; correctness needs readable code. One file cannot be both.
- **Decision:** Keep a naive readable engine as a permanent oracle; build a bitboard engine for speed; gate them with a 100k-game differential test.
- **Rejected:** Optimizing the naive engine in place — loses the oracle, so engine bugs become invisible and get blamed on the learning algorithm.
- **Consequence:** ~1 extra task (TASK-08), in exchange for never again wondering whether a bad training run is an engine bug.

### ADR-002 — N-tuple TD network is the primary learner, DQN is secondary (seed)
- **Context:** "Neural network that learns 2048" usually means DQN, but DQN is weak at 2048 relative to n-tuple TD.
- **Decision:** Build the n-tuple afterstate TD network first (Track A), then DQN (Track B) as a comparison, and report the gap honestly.
- **Rejected:** DQN only — likely plateaus around the 2048 tile and makes the project look like a failure of RL rather than a lesson about representation.
- **Consequence:** The headline result becomes "why sparse linear features beat a convnet here", which is a better finding than either track alone.

### ADR-003 — Learn V(afterstate), not V(state) (seed)
- **Context:** 2048 transitions are deterministic move + random spawn.
- **Decision:** Value the deterministic afterstate, so spawn randomness never enters the value target.
- **Rejected:** V(state) — still trains, but the target carries spawn variance and plateaus noticeably lower.
- **Consequence:** `env.afterstate()` is part of the frozen public API, not an internal helper.

### ADR-004 — Trunk-based branching with a PR per task (seed)
- **Context:** An autonomous agent commits fast; `main` needs a gate that is not "the agent said it was fine".
- **Decision:** One short-lived `task/<NN>-<slug>` branch per task, PR with CI required, squash-merge to a protected `main`. Commit messages carry a `Verified:` footer naming the command that proved the task.
- **Rejected:** Committing straight to `main` (no CI gate before the code lands, no diff review surface); git-flow with develop/release branches (ceremony with no payoff for a solo repo).
- **Consequence:** `git log --grep="Verified:"` becomes the project's audit trail, and a broken `main` becomes a rare event rather than a weekly one.

### ADR-005 — Weights ship as GitHub Release assets, not in git (seed)
- **Context:** The Stage 2 n-tuple network is ~268 MB; checkpoints are larger still.
- **Decision:** Git holds the recipe (config, metrics, summary); GitHub Releases hold the artifact. `2048rl fetch-weights` downloads and SHA-256 verifies against the checksum recorded in `runs/<id>/config.json`.
- **Rejected:** Git LFS — the free storage/bandwidth quota is small enough that a few Stage 2 runs would exhaust it, and a clone would then be unusable.
- **Consequence:** `git clone` stays fast, but an offline user cannot run a trained agent without one download step. Acceptable; failing loudly on a missing checksum is mandatory so it never silently runs an untrained net.

### ADR-006 — One distribution package, `game2048`; everything else is a subpackage (2026-09-15)
- **Context:** `CLAUDE.md`'s layout block put `agents/`, `train/` and `bench/` as top-level siblings of `game2048` under `src/`, and placed `app.py` at `src/train/app.py`. `SPECS.md` §6.1 freezes the entry point as `game2048.app:main`, and `nightly.yml` invoked `python -m src.train.evaluate` and `python -m bench.differential`. Three documents, three different import roots.
- **Decision:** SPECS wins. One distribution package, `src/game2048/`, with `agents/`, `train/` and `bench/` as subpackages inside it and `app.py` at the package root. Every module path becomes `game2048.*`, so `python -m game2048.bench.differential` and `python -m game2048.train.evaluate` work from an installed wheel. `CLAUDE.md`'s layout block and `nightly.yml` corrected to match. This also settles the `Agent` protocol in favour of SPECS §4: `act(self, env: Env) -> Move`, not `act(state)` — an agent needs `legal_moves()` and `afterstate()`, which only the env exposes.
- **Rejected:** Keeping `agents/`, `train/` and `bench/` as top-level siblings of `game2048`. It fails twice over. Anything outside the package root is not importable from an installed wheel, so `python -m bench.differential` would work only from a source checkout — the wheel CI installs and the tree the developer runs would be different programs, and the difference surfaces at release time, which is the worst moment to find it. Separately, top-level packages literally named `agents` and `train` squat generic names in site-packages and collide with any other distribution claiming them.
- **Consequence:** `src/game2048/` is the only importable root. `tests/` stays outside it, unpackaged, running from the checkout. Every `python -m` path in CI, docs and commit footers reads `game2048.*`; a path starting `src.` or bare `bench.` is a bug.

### ADR-007 — Ruff does not format Markdown; ruff is pinned in CI (2026-09-15)
- **Context:** The first CI run on PR #1 failed `lint`, not on code (there is none yet) but on `SPECS.md:86` — ruff 0.16.7 formats Python code blocks inside Markdown, and the frozen API stub in SPECS §2.3 is not in ruff's preferred shape.
- **Decision:** `.ruff.toml` with `extend-exclude = ["*.md"]`, and pin `ruff==0.16.7` in `ci.yml`.
- **Rejected:** Reformatting SPECS.md to satisfy the formatter — the spec is the contract; a formatter's defaults are not a reason to edit it. Also rejected leaving ruff unpinned: a `pip install ruff` that silently changes behavior means CI can go red with no commit to blame, which is the worst kind of red.
- **Consequence:** Ruff config lives in `.ruff.toml` for the life of the repo. `.ruff.toml` takes precedence over `[tool.ruff]` in `pyproject.toml`, so TASK-01 must NOT add a second config block there — it would be silently ignored.

### ADR-008 — Hatchling, version single-sourced from `__init__.py`, no console script yet (2026-09-15)
- **Context:** TASK-01 needed a build backend, a version, and a decision about whether to declare the `2048rl` entry point that SPECS §6.2 freezes.
- **Decision:** Hatchling with `packages = ["src/game2048"]`, and `dynamic = ["version"]` reading `src/game2048/__init__.py`. No `[project.scripts]` block yet: `game2048/app.py` does not exist until TASK-19.
- **Rejected:** A static `version = "0.0.0"` in `pyproject.toml` alongside `__version__` in the package — two copies drift, and they drift silently until a release ships a wheel whose version disagrees with its tag, which is exactly when it is most expensive. Also rejected declaring `2048rl = "game2048.app:main"` now: `pip install .` would succeed and the command would then crash on a missing module, which is a worse failure than the command simply not existing yet.
- **Consequence:** Bump the version by editing `__version__` only. TASK-19 adds `[project.scripts]` at the same time it adds `app.py`, so the entry point never points at nothing.

### ADR-009 — Naive engine: plain lists, and one slide path for all four directions (2026-09-15)
- **Context:** SPECS §2.1 allows the oracle's board to be `list[list[int]]` or a numpy array, and leaves open whether the four directions share code.
- **Decision:** Plain `list[list[int]]` holding tile values, with every function returning a new board. One sliding implementation, `slide_row_left`; `move()` reorients the board so the requested direction becomes a left-move, slides, then reorients back.
- **Rejected:** A numpy board — it buys speed this file is explicitly forbidden to care about, and adds dtype and view-vs-copy semantics to the one file whose job is to be obviously correct. Also rejected four hand-written direction routines: that is four places for the merge rule to be written and only three of them get read carefully, so an edge-order bug can hide in `down` while `left` passes its golden test. With a single slide path, a bug in the merge rule fails all four directions at once.
- **Consequence:** The oracle is slow and that is correct. Golden tests for the four directions still exist and still matter, but they now verify the reorientation, not four copies of the merge rule.

### ADR-010 — SPECS' score invariant was identically zero; corrected to a weighted form (2026-09-15)
- **Context:** SPECS §3 stated the score invariant as `final score == sum of all merge rewards == (sum of tiles) - (spawn values sum)`. Writing the test for it showed the right-hand side is always 0: a merge turns `a + a` into `2a`, so a move never changes the board's tile sum, and the tile sum therefore always equals the sum of every value ever spawned. Measured on a real seeded game (seed 0): score 2260, sum(tiles) 420, sum(spawned) 420, difference 0. As written, the invariant could only hold for games that scored nothing.
- **Decision:** Correct SPECS §3 to the weighted form `score == Σ w(tile) - Σ w(spawned)` where `w(v) = v·(log₂v - 1)`, and add the derivation below the verification table. The middle term of the original — "final score == sum of all merge rewards" — was always true and is kept.
- **Rejected:** Implementing the invariant as literally specified. It would have produced a test asserting `score == 0`, which fails on every real game, and four attempts spent "fixing" a correct engine to satisfy a broken check. Also rejected leaving SPECS alone and only fixing the test: CLAUDE.md makes SPECS the frozen contract, so a test that knowingly disagrees with it turns the contract into decoration.
- **Consequence:** SPECS is no longer a document this project has silently diverged from; the corrected invariant is strong enough to catch real scoring bugs, verified by mutating `naive.py` to score half the merged value, which the invariant rejects on all five seeds. This is the first edit to the frozen contract and it followed the documented route: change SPECS first, log why here.

### ADR-011 — Env state is copied out, never handed out; purity is structural (2026-09-16)
- **Context:** SPECS §2.3 freezes `afterstate()` as "does not mutate the env and does not spawn", and every agent above random calls it speculatively thousands of times per game. The question was how to guarantee that rather than assert it in a docstring.
- **Decision:** `Env` keeps its board private (`_board`) and every method that returns a board returns a copy — `state`, `reset()`, `step()` and, via `naive.move`'s existing copy-on-return, `afterstate()`. `afterstate()` delegates straight to `naive.move`, which allocates a fresh board and reads no RNG, so it has nothing to mutate with. `step()` raises `IllegalMove` before assigning to any attribute, so there is no window in which a rejected move has spawned.
- **Rejected:** Returning the internal board for speed and documenting "do not mutate". The caller here is an agent inside a training loop that will run tens of millions of steps; a single in-place scribble becomes a silent corruption that looks like a learning-rate problem for a week. Also rejected checking legality *after* computing the spawn and rolling back: rollback code is the thing that has to be correct, and "never did it" needs no rollback.
- **Consequence:** Every `step()` and `afterstate()` allocates. That cost lands on the naive engine, which is already the slow path and is not what training will run on; `bitboard.py` at TASK-07 makes the copy a 64-bit integer assignment. The guarantee is tested by fingerprinting the env including its RNG state, which catches a spawn-then-raise mutant that an "unchanged board" check does not.

### ADR-012 — Renderer returns strings; key decoding split from terminal I/O (2026-09-16)
- **Context:** TASK-05 needed a playable terminal game. Two things could have been done the obvious way and both would have cost later: the renderer could print directly, and the keyboard handling could be one function that reads and interprets a keypress together.
- **Decision:** `render.py` returns strings and never prints; `app.py` owns every `print`. Keyboard handling splits into `decode(sequence) -> move | QUIT | None`, a pure function, and `read_key_from_terminal()`, the platform I/O that feeds it. `app.play()` takes `read_key` and `write` as injectable arguments.
- **Rejected:** A renderer that prints. Tests would then have to capture stdout to assert anything, watch mode at TASK-17 would likely grow a second renderer rather than reuse one that insists on printing, and `play` could not be driven to game over in a test at all. Also rejected one read-and-interpret keyboard function: the genuinely error-prone part is Windows' two-byte arrow encoding, and welding it to `msvcrt.getch()` would make it testable only by hand, on one OS, which in practice means never.
- **Consequence:** A whole game can be played to game over inside a test with a scripted key source and no terminal, which is how the game-over screen is verified. The Linux CI runner tests the arrow-key decoding it can never physically produce. `msvcrt` and `termios` are imported lazily inside `read_key_from_terminal`, because a module-scope `import msvcrt` would make `game2048.app` unimportable on CI. The cost is that `read_key_from_terminal` itself is unit-tested by nobody and needs a human at a real keyboard.

### ADR-013 — Tables are built by calling the oracle, and overflow rows are marked, not wrapped (2026-09-16)
- **Context:** SPECS §2.2 requires the 65536-row tables to be "a pure function of `naive.move_left` on a single row". Two things had to be decided: how the build obtains each row's result, and what to store for the 767 rows whose left-slide produces 65536, which no nibble can hold.
- **Decision:** `build_tables()` calls `naive.slide_row_left` for every row, resolving it as a module attribute at call time so the delegation is testable. Overflow rows store an `OVERFLOW` sentinel; the `row_left()` / `row_score()` accessors raise `NibbleOverflow` on them.
- **Rejected:** Hand-writing the table build to match the naive engine. This is the important rejection and it is not hypothetical — a mutant that inlines a *correct* slide into `build_tables` passes all 65536 exhaustive comparisons, because it is right. The exhaustive test cannot tell the two apart. What it would destroy is TASK-08: if the oracle has a subtle bug, the tables must inherit that exact bug, otherwise the differential test compares two independent guesses at the merge rule and agrees only where both guessed the same way. So the tables must *be* the oracle memoized, and a separate test asserts the delegation by replacing the oracle with a lie and checking the rebuilt tables repeat it.
- **Rejected:** Wrapping the exponent (`& 0xF`) on overflow. 65536 becomes exponent 16, which wraps to nibble 0 — an empty cell — so the engine would silently delete the largest tile on the board and keep playing (SPECS trap 4). Also rejected raising during the build: the tables are indexed by row value, so every one of the 65536 entries has to exist; refusing to build means no tables at all because of 767 rows that a real game will essentially never reach.
- **Rejected:** A single small sentinel (`-1`) for both tables. The accessors `row_left()` / `row_score()` raise, but the bitboard engine will index `ROW_LEFT` and `ROW_SCORE` raw to reach the throughput gate, and a `-1` score shifts a real total by one per lookup — a drift small enough to be mistaken for anything, which is exactly the silent corruption the raise exists to prevent. The sentinels are now chosen to be loud instead: `OVERFLOW_ROW = 0xFFFF` and `OVERFLOW_SCORE = -1_000_000_000`.
  `0xFFFF` is four nibbles of 15, a row of four 32768s, and no slide can produce it: for it to come out it would have to go in, and four adjacent 32768s merge — and overflow. So a raw index that skips the check yields a board that is instantly, obviously wrong rather than subtly so. `test_no_legitimate_entry_collides_with_either_sentinel` proves both sentinels are unreachable by real play across all 65536 rows, which is what makes comparing against them sound.
- **Consequence:** `tables.py` imports `naive`, so the fast engine depends on the slow one at build time and not at all at move time. Callers that index `ROW_LEFT` directly for speed must treat `OVERFLOW_ROW` as a hard error rather than a row value — TASK-07's bitboard engine owns that check, and `tables.is_overflow(row)` is there for it.
- **Consequence (dtype):** no dtype change today — both tables are tuples of Python ints. It does constrain a future move to numpy, which `.gitignore` already anticipates via `_tables_cache.npy`: `ROW_LEFT` stays `uint16` (every entry, sentinel included, is in `[0, 0xFFFF]`), but `ROW_SCORE` can no longer be unsigned. It needs `int32` — `-1_000_000_000` does not fit `int16`, and real scores reach 65536 so `int16` was already out. That is the price of a loud score sentinel, and it is worth paying.

### ADR-014 — Bitboard mirrors naive's structure, and golden values live in one module (2026-09-16)
- **Context:** TASK-07 had to produce a second engine that TASK-08 will compare against the first. Two choices mattered: how closely the fast engine should track the slow one's shape, and where the golden expectations should live now that two engines need them.
- **Decision:** `bitboard.py` keeps `naive.py`'s exact control flow — reorient so the move becomes a left-move, slide four rows, reorient back — with only the row slide swapped for a table lookup. Golden values were extracted into `tests/golden_cases.py` and both `test_naive_engine.py` and `test_bitboard.py` import from it; the bitboard tests convert to `uint64` at their own boundary.
- **Rejected:** Writing the bitboard engine in whatever shape was most natural for bit twiddling. It would work, but TASK-08's differential test only tells you *that* two engines disagree, never where, and a reviewer chasing a divergence wants to read the two files side by side and see which line differs. Matching structure makes that possible; it costs nothing at runtime.
- **Rejected:** Copying the golden boards into the bitboard test file. Two copies of a table of hand-computed expectations drift — someone fixes a number in one file — and at that point the differential test is comparing two sets of expectations rather than two engines. Extracting them also meant editing TASK-02's test file, which is why this task's diff touches it: values were relocated, never changed, and that file went from 29 to 34 tests purely because the shared row sweep now includes the five named trap rows.
- **Consequence:** `tests/golden_cases.py` is the single place a golden expectation may be edited, and any engine added later reads it too. `bitboard.py` is deliberately unoptimised — `transpose` and `_reverse_rows` are per-cell Python loops — and the optimisation candidates are listed in LOOP_STATE against TASK-09 rather than taken here, because a benchmark has not been run and nothing has been measured.
