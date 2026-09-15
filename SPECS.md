# SPECS.md — Technical Contract

Frozen contract. If an implementation disagrees with this file, the implementation is
wrong — unless you change this file first and log why in `memory/DECISIONS.md`.

---

## 0. Scope

**In scope:** 4x4 2048 engine (naive + bitboard), a polished terminal app, evaluation
harness, five agents (random, heuristic, expectimax, n-tuple TD, DQN), a written
comparison of Track A vs Track B, and shipping it as an installable package with
published weights.

**Out of scope, permanently:** multiplayer, board sizes other than 4x4, distributed
training, GPU clusters, pretrained models from elsewhere, imitation learning from human
games.

**Deferred (v2, only after v1.0.0 ships):** browser demo. Do not start it early; a
half-built web UI competing for attention with an untrained agent is how this project
dies.

---

## 1. Game rules (exact — most bugs live here)

- Board: 4x4. Tile values are powers of two starting at 2. Empty = 0.
- **Initial state:** two tiles spawned into an empty board.
- **Spawn:** uniformly at random among empty cells. Value is 2 with probability 0.9,
  4 with probability 0.1.
- **Move** (Up/Down/Left/Right): every tile slides as far as possible in that
  direction; two adjacent equal tiles merge into one tile of double value.
  - A tile produced by a merge **cannot merge again in the same move**.
  - Merges resolve **from the edge being moved toward, inward**. `[2,2,2,0]` moved
    left is `[4,2,0,0]`, never `[2,4,0,0]`.
  - `[2,2,2,2]` left → `[4,4,0,0]`.
  - `[4,4,2,2]` left → `[8,4,0,0]`.
- **Score:** each merge adds the value of the *resulting* tile. Merging two 2s adds 4.
- **Legality:** a move is legal only if it changes the board. An illegal move must not
  be applied and must **not** spawn a tile. Playing an illegal move is an error, not a
  no-op turn.
- **Game over:** no legal moves in any of the four directions.
- **2048 tile:** recorded as a win event; play continues to the real game over.

### The afterstate

One turn is two steps:

```
s  --(move a, deterministic)-->  s'  --(random spawn)-->  s_next
     state                       afterstate                next state
```

The reward (merge score) is fully determined by `s -> s'`. Track A learns
`V(afterstate)`, not `V(state)`. This is not an optimization detail — it is why the
approach works, because it removes the spawn randomness from the value target.

---

## 2. Engine specs

### 2.1 Naive engine (`naive.py`) — the oracle

Readable above all. A 4x4 `list[list[int]]` or `numpy.ndarray`. Implement `move_left`
honestly (compress → merge → compress), derive the other three by rotation/reversal.
Nobody optimizes this file, ever. Its only jobs are: be obviously correct, and catch
the bitboard engine lying.

### 2.2 Bitboard engine (`bitboard.py`) — the workhorse

- Board = one `uint64`. 16 nibbles, one per cell, row-major.
- Nibble stores `log2(tile)`: `0` = empty, `1` = 2, `2` = 4, ... `11` = 2048,
  `15` = 32768. The 4-bit ceiling is 32768; assert on overflow rather than wrapping.
- `tables.py` precomputes, for all 65536 possible rows:
  `ROW_LEFT[row] -> new_row`, `ROW_SCORE[row] -> score_gained`.
  Right = reverse the row, look up, reverse back. Up/Down = transpose, apply
  left/right, transpose back.
- Table build must be a pure function of `naive.move_left` on a single row, so the
  tables inherit the oracle's correctness by construction.

### 2.3 Environment API (`env.py`) — frozen signatures

```python
Move = Literal["up", "down", "left", "right"]

class Env:
    def __init__(self, seed: int | None = None) -> None: ...
    def reset(self, seed: int | None = None) -> State: ...
    def legal_moves(self) -> list[Move]: ...
    def afterstate(self, move: Move) -> tuple[State, int, bool]:
        """Deterministic part only. Returns (afterstate, reward, changed).
        Does not mutate the env and does not spawn."""
    def step(self, move: Move) -> tuple[State, int, bool, dict]:
        """(next_state, reward, done, info). Raises IllegalMove if not changed."""
    def render(self) -> str: ...
```

Agents see only this. If an agent imports `bitboard` directly, that is a bug.

---

## 3. Verification harness

| Check | What it proves | Gate |
| :-- | :-- | :-- |
| Golden move tests | Hand-written boards → expected boards, all 4 directions, both engines | must pass |
| Merge-once test | `[4,4,4,4]` left is `[8,8,0,0]`, never `[16,0,0,0]` | must pass |
| Edge-order test | `[2,2,2,0]` left is `[4,2,0,0]` | must pass |
| Illegal-move test | No board change → no spawn, no score, raises | must pass |
| Spawn distribution | 100k spawns: P(4) in [0.09, 0.11]; empty cells uniform (chi-square p > 0.01) | must pass |
| Score invariant | Final score == sum of all merge rewards == (sum of tiles) - (spawn values sum) | must pass |
| Determinism | Same seed → byte-identical game transcript, twice | must pass |
| **Differential test** | 100k random games: naive and bitboard produce identical boards, scores, terminations | must pass |
| Throughput bench | `bench/engine_bench.py` | **≥ 200,000 moves/sec** (pure Python + numpy) |
| Eval harness | 1000 seeded games → mean/median/max score, max-tile histogram, 2048/4096 rate | must produce a table |

The differential test is the backbone. Once it holds, no engine bug can hide.

---

## 4. Agents

Shared protocol (`agents/base.py`):

```python
class Agent(Protocol):
    def act(self, env: Env) -> Move: ...
    def name(self) -> str: ...
```

Every agent is evaluated by the **same** `evaluate.py` over the **same** 1000 seeds.

### 4.1 Random (floor)
Uniform over `legal_moves()`. Establishes the floor.

### 4.2 Heuristic greedy (1-ply)
Score each afterstate with handcrafted features: empty-cell count, monotonicity,
smoothness, max-tile-in-corner. Pick the best. This is a **baseline for comparison
only** — its features must never leak into the learners' reward.

### 4.3 Expectimax (reference ceiling)
Max nodes for the player, chance nodes for the spawn (0.9/0.1, uniform over empties),
depth-limited with the 4.2 heuristic at leaves. Add a transposition table and
probability cutoff (skip branches below ~1e-4) if depth 3 is too slow.

### 4.4 Track A — N-tuple network + TD(0)  ← the main event

- **Value function:** `V(afterstate) = Σ_i LUT_i[index_i(afterstate)]`. Each tuple is a
  fixed set of `n` cells; its index is the `n` nibbles read as base-16. Sparse, linear,
  and a genuine learned network — just not a deep one.
- **Stage 1 (TASK-12):** 4 × 5-tuples. `16^5 = 1,048,576` entries each → ~4 MB float32
  per tuple, ~17 MB total. Trains to something watchable in minutes.
- **Stage 2 (TASK-13):** 4 × 6-tuples (two rows + two squares). `16^6 = 16,777,216`
  entries each → ~67 MB each, **~268 MB total**. Check RAM before starting; this is
  the number that surprises people.
- **Symmetric sampling:** each board has 8 symmetries (4 rotations × reflection). Index
  all 8 and update all 8 per step — an 8× free increase in sample efficiency.
- **Update (TD(0) on afterstates):** after taking `a` in `s`, reaching afterstate `s'`,
  spawning to `s_next`, then choosing greedy `a_next` giving `(s'_next, r_next)`:
  ```
  δ = r_next + V(s'_next) - V(s')
  V(s') += (α / num_tuples) * δ        # applied to every tuple's LUT entry
  ```
  Terminal: `V(terminal afterstate) = 0`.
- **Action selection:** greedy on `r + V(afterstate)`. **No ε-greedy** — 2048's own
  spawn randomness supplies the exploration. If you add ε, log it as an experiment and
  expect it to hurt.
- **α:** 0.1 to start, decayed. **No discounting** (γ = 1); the episode is finite and
  the objective is total score.
- Checkpoint every 10k games to `runs/<run_id>/`. Resumable, because Stage 2 is a
  multi-hour run.

### 4.5 Track B — Deep RL (Double DQN)

- **Input:** 16 one-hot planes of 4x4 (plane `k` = cells holding `2^k`), float32.
- **Net:** the 2048-appropriate conv shapes — parallel `(2,1)` and `(1,2)` conv
  branches (they read merge-able pairs directly), ~128 filters, concat, 2 FC layers,
  4 outputs. Not a generic 3x3 ImageNet stack.
- Double DQN, target net synced every 1000 steps, replay buffer 100k, batch 512,
  ε-greedy 1.0 → 0.05, Adam 1e-4, illegal actions masked to `-inf` at selection.
- **Expected outcome: worse than Track A.** Sample efficiency is the reason. Report it
  as a finding. Do not quietly feed it heuristic features to make the graph nicer.

---

## 5. Acceptance criteria

Targets to verify, not promises. Record whatever you actually measure.

| Agent | Mean score | 2048 rate | Notes |
| :-- | :-- | :-- | :-- |
| Random | ~1,000 | ~0% | sanity floor; max tile rarely exceeds 256 |
| Heuristic 1-ply | ≥ 3,000 | ≥ 5% | |
| Expectimax d=3 | ≥ 20,000 | ≥ 80% | reference ceiling |
| **N-tuple Stage 1** (4×5-tuple, 100k games) | **≥ 15,000** | **≥ 50%** | the "it learns" gate |
| **N-tuple Stage 2** (4×6-tuple, 1M games) | **≥ 40,000** | **≥ 90%** | 4096 rate ≥ 50% |
| DQN (2M steps) | ≥ 3,000 | ≥ 5% | must at least beat random decisively |

Project ships when: the differential test passes, the throughput gate passes, Stage 1
clears its gate, and `RESULTS.md` compares all six agents on the same 1000 seeds with a
written explanation of why the sparse linear network beats the convnet.

---

## 6. The app (what makes it shippable, not just a script)

A stranger with Python installed should get from zero to watching a trained agent play
in under two minutes, without cloning anything.

### 6.1 Packaging

- `pyproject.toml`, PEP 621 metadata, hatchling or setuptools backend.
- `[project.scripts] 2048rl = "game2048.app:main"` — one console entry point.
- Optional dependency groups: `[dev]` (pytest, ruff), `[dl]` (torch, only Track B),
  `[tui]` (rich/textual). Base install stays numpy-only.
- `pip install git+https://github.com/xeseing/2048-rl` must work on a clean machine.
  CI proves this in the release workflow, not by assertion.

### 6.2 CLI surface (frozen)

```
2048rl play                              # human plays, arrow keys, in the terminal
2048rl watch --agent ntuple [--speed 4]  # watch the trained agent, live
2048rl eval  --agent ntuple --games 1000 # eval table to stdout
2048rl train --track td --run td-05      # training with live progress
2048rl fetch-weights [--tag v0.4.0]      # download weights from GitHub Releases
2048rl bench                             # engine throughput
```

- `--seed` on every subcommand that has randomness.
- `--json` on `eval` so results are machine-readable.
- Exit code 1 on gate failure, so CI can use the same commands the human uses.

### 6.3 Terminal UI

`rich` for coloured tiles, live score, and the agent's per-move value estimates in
`watch` mode. Degrades to plain ASCII when `--no-color` is passed or the terminal
doesn't support it — never crashes on a dumb terminal.

`watch` showing the agent's estimated value per direction is the single best
demonstration this project has. Prioritize it over any other polish.

### 6.4 Weight distribution

Weights are 17 MB (Stage 1) and ~268 MB (Stage 2). They are **not** in git.
`fetch-weights` pulls them from the GitHub Release matching the installed version,
verifies a SHA-256 recorded in `runs/<id>/config.json`, and caches to the user's
platform cache dir. Corrupt or missing checksum → hard failure, never silent fallback
to an untrained net.

### 6.5 README

The README is a deliverable, not an afterthought. It must contain: a GIF or asciinema
of `2048rl watch`, the real results table, the one-paragraph explanation of why the
n-tuple net beats the convnet, install instructions, and the CI badge. Numbers in the
README come from `RESULTS.md` and must match it exactly.

---

## 7. Known traps

1. Merging from the wrong side (`[2,2,2,0]` → `[2,4,0,0]`). Test it explicitly.
2. A merged tile merging twice in one move.
3. Spawning after an illegal move — silently destroys any agent's learning.
4. Nibble overflow past 32768 — assert, don't wrap.
5. Learning `V(state)` instead of `V(afterstate)`. It trains; it just plateaus low.
6. Forgetting the `1/num_tuples` in the learning rate → divergence to inf/NaN.
7. Evaluating on training seeds. Keep a held-out eval seed range and never train on it.
8. Reporting a max score instead of a distribution. One lucky game is not a result.
