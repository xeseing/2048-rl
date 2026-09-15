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
