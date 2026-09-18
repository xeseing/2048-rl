"""Track A training: TD(0) on afterstates, self-play (SPECS section 4.4).

    python -m game2048.train.td_train --run td-01 --games 100000 --seed 1
    python -m game2048.train.td_train --run td-02 --stage 2 --games 1000000 \
        --alpha-schedule linear --alpha-start 0.1 --alpha-end 0.01
    python -m game2048.train.td_train --run td-02 --resume

`batch` games are played side by side on the bitboard engine, so the network's
lookups and updates run as numpy batches instead of per board. Each step, for
every game in the batch: pick the greedy move on `r + V(s')`, then move the
previous afterstate toward that target (`0` once the game is over). Updates
from one step are applied together; within a step every game reads the same
weights.

Writes `runs/<run>/`: config.json, metrics.csv, summary.md (committed) and
weights.npz (gitignored). Refuses to overwrite an existing run.

Every `--checkpoint-every` games it replaces `checkpoint_latest.npz`
(gitignored): weights plus everything else the run needs to continue exactly
as if it had never stopped. `--resume` reads the run's own config.json, drops
metrics rows written after that checkpoint, and appends from there. The file
is deleted once the run completes.
"""

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from game2048 import bitboard
from game2048.agents.ntuple import STAGES, NTupleNetwork

EVAL_SEED_FLOOR = 900_000  # held-out eval range (CLAUDE.md); never train on it

_SHIFTS = np.arange(60, -1, -4, dtype=np.uint64)


def exponents(boards: list[int]) -> np.ndarray:
    """Bitboards -> (N, 16) exponents, row-major (cell 0 is the high nibble)."""
    packed = np.array(boards, dtype=np.uint64)[:, None]
    return ((packed >> _SHIFTS) & np.uint64(15)).astype(np.int64)


def max_tile(board: int) -> int:
    return 1 << max((board >> s) & 15 for s in range(0, 64, 4))


def alpha_at(done, games, alpha, alpha_end=None):
    """The step size after `done` of `games` finished games.

    `alpha_end=None` is constant alpha. Otherwise alpha falls linearly from
    `alpha` at game 0 to `alpha_end` at game `games`.
    """
    if alpha_end is None:
        return alpha
    return alpha + (alpha_end - alpha) * done / games


def train(
    network,
    games,
    seed,
    alpha=0.1,
    batch=64,
    on_game=None,
    state=None,
    checkpoint_every=0,
    on_checkpoint=None,
    alpha_end=None,
):
    """Play `games` self-play games, learning as it goes.

    `on_game(score, max_tile)` is called as each game ends. Returns the list of
    (score, max_tile) finished in this call, in finishing order.

    The step size is recomputed before every batched update from the games
    finished so far, run-wide (see `alpha_at`), so a resumed run decays on
    the same schedule.

    `on_checkpoint(state)` is called at the end of the step in which the
    finished-game count crosses a multiple of `checkpoint_every`. Passing that
    `state` back (with the weights as they were then) continues the run
    exactly where it left off.
    """
    rng = random.Random(seed)
    # A slot is [board, previous afterstate or None, score].
    slots: list[list] = []
    started = done = 0
    if state is not None:
        version, internal, gauss = state["rng"]
        rng.setstate((version, tuple(internal), gauss))
        slots, started, done = state["slots"], state["started"], state["done"]
    mark = done // checkpoint_every if checkpoint_every else 0
    finished = []
    while slots or started < games:
        while len(slots) < batch and started < games:
            slots.append([bitboard.new_game(rng), None, 0])
            started += 1

        afters, rewards, owners = [], [], []
        for i, (board, _, _) in enumerate(slots):
            for direction in bitboard.MOVES:
                after, reward, changed = bitboard.move(board, direction)
                if changed:
                    afters.append(after)
                    rewards.append(reward)
                    owners.append(i)

        # Best candidate per slot; slots with none are over and target 0.
        best = [None] * len(slots)
        if afters:
            totals = network.values(exponents(afters)) + np.array(rewards)
            for k, total in enumerate(totals.tolist()):
                i = owners[k]
                if best[i] is None or total > best[i][0]:
                    best[i] = (total, k)

        learners = [i for i, slot in enumerate(slots) if slot[1] is not None]
        if learners:
            prevs = exponents([slots[i][1] for i in learners])
            targets = np.array([best[i][0] if best[i] else 0.0 for i in learners])
            step = alpha_at(done, games, alpha, alpha_end)
            network.update(prevs, targets - network.values(prevs), step)

        survivors = []
        for slot, choice in zip(slots, best, strict=True):
            if choice is None:
                result = (slot[2], max_tile(slot[0]))
                finished.append(result)
                done += 1
                if on_game:
                    on_game(*result)
                continue
            k = choice[1]
            slot[1] = afters[k]
            slot[2] += rewards[k]
            slot[0] = bitboard.spawn(afters[k], rng)
            survivors.append(slot)
        slots = survivors
        # No checkpoint for a finished run: main() is about to save the weights.
        if on_checkpoint and done < games and done // checkpoint_every > mark:
            mark = done // checkpoint_every
            on_checkpoint(
                {
                    "rng": rng.getstate(),
                    "slots": slots,
                    "started": started,
                    "done": done,
                }
            )
    return finished


def save_checkpoint(path: Path, network, state: dict) -> None:
    """Write-then-rename, so a crash mid-write leaves the previous one intact."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        np.savez(f, weights=network.weights, state=np.array(json.dumps(state)))
    os.replace(tmp, path)


def load_checkpoint(path: Path, tuples) -> tuple[NTupleNetwork, dict]:
    with np.load(path) as data:
        return NTupleNetwork(tuples, data["weights"]), json.loads(str(data["state"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m game2048.train.td_train")
    parser.add_argument("--run", required=True, help="run id, writes runs/<run>/")
    parser.add_argument("--games", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--alpha-schedule", choices=("constant", "linear"), default="constant"
    )
    parser.add_argument("--alpha-start", "--alpha", type=float, default=0.1)
    parser.add_argument("--alpha-end", type=float, help="linear schedule only")
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--log-every", type=int, default=1000)
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--stage", type=int, choices=sorted(STAGES), default=1)
    parser.add_argument("--checkpoint-every", type=int, default=10_000)
    parser.add_argument(
        "--resume", action="store_true", help="continue <run> from its checkpoint"
    )
    args = parser.parse_args(argv)

    out = Path(args.runs_dir) / args.run
    checkpoint = out / "checkpoint_latest.npz"
    if args.resume:
        # The run's own config wins over anything else on the command line.
        config = json.loads((out / "config.json").read_text())
        for key in (
            "games",
            "seed",
            "alpha_schedule",
            "alpha_start",
            "alpha_end",
            "batch",
            "log_every",
            "stage",
            "checkpoint_every",
        ):
            setattr(args, key, config[key])
    if args.seed >= EVAL_SEED_FLOOR:
        parser.error(f"seeds >= {EVAL_SEED_FLOOR} are the held-out eval range")
    if (args.alpha_schedule == "linear") != (args.alpha_end is not None):
        parser.error("--alpha-end goes with --alpha-schedule linear, and only there")
    tuples = STAGES[args.stage]

    if args.resume:
        if not checkpoint.exists():
            parser.error(f"{checkpoint} does not exist; nothing to resume")
        network, state = load_checkpoint(checkpoint, tuples)
        # Rows past the checkpoint get replayed, so drop them before appending.
        with open(out / "metrics.csv", newline="") as f:
            rows = list(csv.reader(f))
        rows = rows[:1] + [r for r in rows[1:] if int(r[0]) <= state["done"]]
        with open(out / "metrics.csv", "w", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"resuming {args.run} at game {state['done']:,}", flush=True)
    else:
        out.mkdir(parents=True, exist_ok=False)
        cadence = "every batched update, from games finished run-wide"
        config = vars(args) | {"alpha_cadence": cadence, "tuples": tuples}
        del config["resume"]
        (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")
        network, state = NTupleNetwork(tuples), None

    # Wall time spent up to the checkpoint carries over.
    start = time.perf_counter() - (state["seconds"] if state else 0.0)
    window = [tuple(w) for w in state["window"]] if state else []
    done = state["done"] if state else 0
    metrics_file = open(out / "metrics.csv", "a", newline="")  # noqa: SIM115
    metrics = csv.writer(metrics_file)
    if not state:
        header = ["games", "mean_score", "rate_2048", "max_score", "alpha", "seconds"]
        metrics.writerow(header)

    def on_game(score, tile):
        nonlocal done
        done += 1
        window.append((score, tile))
        if len(window) == args.log_every or done == args.games:
            row = [
                done,
                round(statistics.mean(s for s, _ in window)),
                round(sum(t >= 2048 for _, t in window) / len(window), 4),
                max(s for s, _ in window),
                round(alpha_at(done, args.games, args.alpha_start, args.alpha_end), 6),
                round(time.perf_counter() - start, 1),
            ]
            metrics.writerow(row)
            metrics_file.flush()
            print(*row, sep="\t", flush=True)
            window.clear()

    def on_checkpoint(train_state):
        seconds = time.perf_counter() - start
        state = train_state | {"window": window, "seconds": seconds}
        save_checkpoint(checkpoint, network, state)
        print(f"checkpoint at game {train_state['done']:,}", flush=True)

    with metrics_file:
        train(
            network,
            args.games,
            args.seed,
            args.alpha_start,
            args.batch,
            on_game,
            state,
            args.checkpoint_every,
            on_checkpoint,
            args.alpha_end,
        )
    network.save(out / "weights.npz")
    checkpoint.unlink(missing_ok=True)

    last = list(csv.DictReader(open(out / "metrics.csv")))[-1]  # noqa: SIM115
    alpha = f"alpha {args.alpha_start}"
    if args.alpha_end is not None:
        alpha += f" -> {args.alpha_end} ({args.alpha_schedule})"
    (out / "summary.md").write_text(
        f"# {args.run}\n\n"
        f"- games: {args.games:,}, seed {args.seed}, {alpha}, "
        f"batch {args.batch}, stage {args.stage}\n"
        f"- last {args.log_every:,} training games: mean {int(last['mean_score']):,}, "
        f"2048 rate {float(last['rate_2048']):.1%}\n"
        f"- wall time: {float(last['seconds']):,.0f}s\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
