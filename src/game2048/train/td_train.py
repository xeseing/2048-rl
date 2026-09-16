"""Track A training: TD(0) on afterstates, self-play (SPECS section 4.4).

    python -m game2048.train.td_train --run td-01 --games 100000 --seed 1

`batch` games are played side by side on the bitboard engine, so the network's
lookups and updates run as numpy batches instead of per board. Each step, for
every game in the batch: pick the greedy move on `r + V(s')`, then move the
previous afterstate toward that target (`0` once the game is over). Updates
from one step are applied together; within a step every game reads the same
weights.

Writes `runs/<run>/`: config.json, metrics.csv, summary.md (committed) and
weights.npz (gitignored). Refuses to overwrite an existing run.
"""

import argparse
import csv
import json
import random
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from game2048 import bitboard
from game2048.agents.ntuple import NTupleNetwork

EVAL_SEED_FLOOR = 900_000  # held-out eval range (CLAUDE.md); never train on it

_SHIFTS = np.arange(60, -1, -4, dtype=np.uint64)


def exponents(boards: list[int]) -> np.ndarray:
    """Bitboards -> (N, 16) exponents, row-major (cell 0 is the high nibble)."""
    packed = np.array(boards, dtype=np.uint64)[:, None]
    return ((packed >> _SHIFTS) & np.uint64(15)).astype(np.int64)


def max_tile(board: int) -> int:
    return 1 << max((board >> s) & 15 for s in range(0, 64, 4))


def train(network, games, seed, alpha=0.1, batch=64, on_game=None):
    """Play `games` self-play games, learning as it goes.

    `on_game(score, max_tile)` is called as each game ends. Returns the list of
    (score, max_tile) in finishing order.
    """
    rng = random.Random(seed)
    # A slot is [board, previous afterstate or None, score].
    slots: list[list] = []
    started = 0
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
            network.update(prevs, targets - network.values(prevs), alpha)

        survivors = []
        for slot, choice in zip(slots, best, strict=True):
            if choice is None:
                result = (slot[2], max_tile(slot[0]))
                finished.append(result)
                if on_game:
                    on_game(*result)
                continue
            k = choice[1]
            slot[1] = afters[k]
            slot[2] += rewards[k]
            slot[0] = bitboard.spawn(afters[k], rng)
            survivors.append(slot)
        slots = survivors
    return finished


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m game2048.train.td_train")
    parser.add_argument("--run", required=True, help="run id, writes runs/<run>/")
    parser.add_argument("--games", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--log-every", type=int, default=1000)
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args(argv)
    if args.seed >= EVAL_SEED_FLOOR:
        parser.error(f"seeds >= {EVAL_SEED_FLOOR} are the held-out eval range")

    out = Path(args.runs_dir) / args.run
    out.mkdir(parents=True, exist_ok=False)
    config = vars(args) | {"tuples": NTupleNetwork().tuples}
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    network = NTupleNetwork()
    start = time.perf_counter()
    window: list[tuple[int, int]] = []
    done = 0
    metrics_file = open(out / "metrics.csv", "w", newline="")  # noqa: SIM115
    metrics = csv.writer(metrics_file)
    metrics.writerow(["games", "mean_score", "rate_2048", "max_score", "seconds"])

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
                round(time.perf_counter() - start, 1),
            ]
            metrics.writerow(row)
            metrics_file.flush()
            print(*row, sep="\t", flush=True)
            window.clear()

    with metrics_file:
        train(network, args.games, args.seed, args.alpha, args.batch, on_game)
    network.save(out / "weights.npz")

    last = list(csv.DictReader(open(out / "metrics.csv")))[-1]  # noqa: SIM115
    (out / "summary.md").write_text(
        f"# {args.run}\n\n"
        f"- games: {args.games:,}, seed {args.seed}, alpha {args.alpha}, "
        f"batch {args.batch}\n"
        f"- last {args.log_every:,} training games: mean {int(last['mean_score']):,}, "
        f"2048 rate {float(last['rate_2048']):.1%}\n"
        f"- wall time: {float(last['seconds']):,.0f}s\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
