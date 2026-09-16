# CLAUDE.md — Project Constitution

> Read this file first, every session. It is short on purpose. It tells you where
> everything else is and what you are never allowed to do.

## What this project is

A 2048 game engine plus an agent that **learns to play it by itself** from self-play,
with no human demonstrations and no hardcoded strategy inside the learner.

Two learning tracks, both built, both benchmarked against each other:

- **Track A — N-tuple network + TD(0) afterstate learning.** A sparse linear value
  network over board patterns. This is the approach that actually wins at 2048.
- **Track B — Deep RL (Double DQN, small convnet).** The "deep neural network"
  track. Expect it to lose to Track A. Report that honestly; do not tune it into a
  lie.

Non-learning agents exist only as **measuring sticks**: random (floor) and
expectimax+heuristic (ceiling). They are never presented as "the AI".

It ships as a real installable app (`pip install` → `2048rl play`), developed on GitHub
with CI, PRs, tags and releases. Engineering hygiene is part of the deliverable, not
overhead on top of it.

Full contract: `SPECS.md`. Current work: `LOOP_STATE.md`. Accumulated knowledge:
`memory/`. Git and GitHub conventions: `GIT_WORKFLOW.md`.

---

## Session boot sequence (do this before anything else)

1. Read `CLAUDE.md` (this file).
2. Read `LOOP_STATE.md` → what is the active task and its attempt count?
3. Read `memory/FACTS.md` → invariants and verified numbers you must not re-derive.
4. Read `memory/FAILURES.md` → things already tried that did not work. **Do not retry
   anything on this list without a stated new reason.**
5. Skim the top of `memory/JOURNAL.md` (last entry only).
6. Only open `SPECS.md`, `memory/DECISIONS.md`, `memory/EXPERIMENTS.md` when the
   current task touches them.
7. Run `git status` and `git log --oneline -5`. If the tree is dirty or you are not on
   the branch the active task expects, resolve that before anything else.
8. State in one line: "Resuming TASK-XX, attempt N/4, branch `task/xx-...`."

Never start editing code before step 8.

---

## Golden rules

1. **Nothing is [DONE] without a command that proves it.** A passing `pytest` run, a
   benchmark number, a printed eval table. "Looks right" is not verification.
2. **One task at a time.** The diff for a task touches only what that task needs. No
   drive-by refactors, no "while I'm here".
3. **Correctness before speed. Speed before learning.** A fast wrong engine trains a
   fast wrong agent for six hours before you find out.
4. **Every stochastic thing takes a seed.** Spawns, exploration, shuffling, init. If a
   result cannot be reproduced from a seed, it is not a result.
5. **The learner gets no strategy hints.** No "keep max tile in the corner" reward
   shaping, no snake-order bonus, no illegal-move masking learned from heuristics.
   Reward = merge score from the environment. That is all. Breaking this makes the
   whole project meaningless.
6. **Write to memory when you learn something, not when you finish talking.** See the
   memory protocol below.
7. **Circuit breaker: 4 attempts.** On the 4th failure of the same task, stop. Write
   the diagnosis to `memory/FAILURES.md`, set the task to `[!] BLOCKED` in
   `LOOP_STATE.md`, and ask the human. Do not thrash.

---

## Hard constraints

- Python 3.11+. `numpy` and `pytest` are the only dependencies until Track B; PyTorch
  arrives only at TASK-15.
- No neural network, no PyTorch import, and no Python-level allocation in the engine's
  hot path. The engine must be importable and runnable with numpy alone.
- The naive engine (`naive.py`) is **never deleted**. It is the oracle that the fast
  bitboard engine is differentially tested against, forever.
- Training runs write to `runs/<run_id>/`. Weights are gitignored; the manifest
  (`config.json`, `metrics.csv`, `summary.md`) is committed.
- No training run longer than 30 minutes without first proving the pipeline on a
  1000-game smoke run.

---

## Version control rules

Full conventions in `GIT_WORKFLOW.md`. The non-negotiable subset:

1. **One branch per task**, named `task/<NN>-<slug>`, cut fresh from `main`. Bug fixes
   use `fix/<slug>`; training sweeps use `exp/<slug>`.
2. **`main` is always green.** Never commit directly to `main`. Never
   `git push --force` to `main` under any circumstance.
3. **Every commit message carries a `Verified:` footer** with the command that was run
   and its result. A commit with no `Verified:` line is a commit that skipped the gate.
   What sits above it depends on the branch: **task branches carry `Task:` + `Verified:`;
   `fix/` and `chore/` branches carry `Chore:` + `Verified:`.** Same shape, different
   key, so `git log --grep="Task:"` stays a list of tasks and nothing else, and
   `git log --grep="Chore:"` is everything that changed the scaffolding around them.
   Never give a non-task commit a `Task:` line to look uniform — that is precisely the
   thing that makes the audit trail stop being one.
   ```
   feat(bitboard): add uint64 board with precomputed row tables

   Task: TASK-07
   Verified: pytest tests/test_engine.py -q -> 47 passed
   ```
   ```
   docs(process): one task per PR, and a pointer to the stale-.pyc trap

   Chore: atomic-task-PR rule and harness-hygiene note
   Verified: ruff check . -> All checks passed!
   ```
4. **PR per task.** `gh pr create --fill`, wait for CI with `gh pr checks --watch`, then
   `gh pr merge --squash --delete-branch`. Do not merge with CI red. Do not merge
   without showing the human the diff summary first.
5. **Never commit:** trained weights (they go to GitHub Release assets), `.env`, API
   keys, tokens, `runs/**/checkpoint_*`. If `git status` shows any of these, stop and
   fix `.gitignore` before committing anything.
6. **`LOOP_STATE.md` and `memory/` are committed with the task they describe**, in the
   same commit. Code and state must never drift apart across a clone.
7. **Tag at milestones only** (see `GIT_WORKFLOW.md` Part 6), never on a schedule. Tag
   messages contain the measured numbers that justify the tag.
8. If the human has not authenticated `gh`, say so and stop — do not invent a
   workaround or push over HTTPS with a pasted token.
9. **Each task adds its own CI gate in its own PR. Never add a conditional that lets a
   gate skip silently.** `ci.yml` grows with the repo: it may only invoke commands that
   already exist on `main`. A step guarded by `if: hashFiles(...)` reports green while
   testing nothing, which is worse than no step at all.
10. **A PR that edits `SPECS.md` says so under a `## SPECS CHANGED` heading** whenever
    the edit moves an acceptance criterion, a verification gate, a frozen signature, or
    a numeric target. State the old text, the new text, and the evidence that forced
    the change, and cite the ADR. The point is that the human cannot skim past a moved
    goalpost. Structural edits — wording, formatting, a clarifying sentence that changes
    no criterion — do not need the heading. Editing SPECS itself needs no advance
    sign-off: correct the contract first, log the ADR, and flag it in the PR.
11. **One task per PR.** If a process rule, doc fix, or infrastructure improvement
    is born from a discovery mid-task, land the current task's PR as it stands
    and open a follow-up `fix/` branch for the new rule. The atomic-commit
    convention is what makes `git log --grep="Task:"` and
    `git log --grep="Verified:"` searchable audit trails.

---

## Memory protocol

Five files, five different jobs. Keeping them separate is what stops them rotting.

| File | Job | Write style | Cap |
| :-- | :-- | :-- | :-- |
| `memory/FACTS.md` | Things now known to be true about this codebase | Edit in place; correct wrong lines | ~60 lines |
| `memory/DECISIONS.md` | Why a choice was made | **Append only.** Never edit or delete past entries | unbounded |
| `memory/FAILURES.md` | Dead ends, with the reason they died | Append only | unbounded |
| `memory/EXPERIMENTS.md` | One table row per training run | Append a row | unbounded |
| `memory/JOURNAL.md` | Session narrative, newest first | Prepend; roll entries 11+ into one summary line | 10 entries |

**Write triggers — write immediately when any of these happen:**

- A test fails for a reason you did not expect → `FACTS.md` (the gotcha) or
  `FAILURES.md` (if it killed an approach).
- You pick between two real options → `DECISIONS.md`, one entry, including the option
  you rejected.
- A benchmark or eval produces a number → `FACTS.md` if it is a property of the system
  ("bitboard engine: 1.4M moves/s"), `EXPERIMENTS.md` if it is a training result.
- A training run finishes or is killed → `EXPERIMENTS.md` row, always, even for
  failures. **A killed run with no row is a run you will pointlessly repeat.**
- A task hits attempt 4 → `FAILURES.md`, then stop.
- End of session → one `JOURNAL.md` entry.

**Never write to memory:**

- Restatements of `SPECS.md` or `CLAUDE.md`.
- Your plans, TODOs, or "next steps" — those live in `LOOP_STATE.md` and expire.
- Code snippets. Memory points at code (`src/agents/ntuple.py:88`), it does not copy it.
- Anything you have not verified. Memory is a record of evidence, not of guesses.

**Harness hygiene:** before writing a red-first mutation harness, read the stale
`.pyc` entry in `memory/FACTS.md` — a source file restored byte-for-byte can keep
executing its mutant, and `inspect.getsource` cannot see it.

**Contradiction rule:** if a new observation contradicts a line in `FACTS.md`, fix that
line in place and append a `DECISIONS.md` entry saying what changed and why. Never
leave two contradictory facts on file.

---

## Commands

There is no Makefile. `make` is not installed on the development machine and the
shell is PowerShell 5.1, where `&&` is a parse error — so every command below is
written as its own line, to be run one at a time.

Setup (once):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

The gates — run these before any commit:

```powershell
pytest -q                        # the gate for every engine task
ruff check .
ruff format --check .
```

Engine verification:

```powershell
python -m game2048.bench.differential --games 100000 --seed 7
python -m game2048.bench.engine_bench --seconds 30 --gate 200000
```

The app itself:

```powershell
2048rl play                              # human plays in the terminal
2048rl watch --agent ntuple              # replay a trained agent's game
2048rl eval --agent ntuple --games 1000  # score dist + tile rates
2048rl train --track td --run td-01      # Track A training
2048rl train --track dqn --run dqn-01    # Track B training
python -m build                          # build the wheel/sdist
```

"Everything CI runs, locally, before you push" is the four lines under *the gates*
plus the differential test, in that order.

If a command in this list does not exist yet, creating it is part of the task that
needs it — not a separate task, and not something to skip.

---

## Repo layout

```
src/game2048/          # the ONE distribution package. Nothing importable lives outside it.
  __init__.py
  naive.py      # readable reference implementation. The oracle. Never deleted.
  tables.py     # precomputed 65536-entry row-move tables
  bitboard.py   # fast engine: 64-bit board, 16 nibbles of log2(tile)
  env.py        # the API agents see: reset/step/afterstate/legal_moves
  render.py     # terminal rendering
  app.py        # Typer/argparse CLI. The `2048rl` entry point: game2048.app:main
  agents/
    base.py       # Agent protocol: act(env) -> Move   (env, not state — see SPECS 4)
    random_agent.py
    heuristic.py  # greedy 1-ply, handcrafted features
    expectimax.py # reference ceiling, not "the AI"
    ntuple.py     # Track A: value network + TD(0) afterstate learning
    dqn.py        # Track B: Double DQN convnet
  train/
    td_train.py
    dqn_train.py
    evaluate.py   # shared eval harness for every agent
  bench/
    differential.py
    engine_bench.py
tests/          # not packaged; runs from the checkout
runs/           # per-run artifacts; weights gitignored, manifests committed
.github/
  workflows/ci.yml       # lint + secret scan today; each task adds its own gate
  workflows/nightly.yml  # 100k differential + throughput gate + baseline eval
  pull_request_template.md
```
