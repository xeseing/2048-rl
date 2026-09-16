"""Throughput benchmark for the bitboard engine (SPECS section 3).

    python -m game2048.bench.engine_bench --seconds 30 --gate 200000

**What a "move" means here.** One applied move: a board transition the engine
actually performed. Illegal attempts are not counted, so the number is moves the
engine made, not calls it serviced. A random rotation of the four directions is
tried in order and the first legal one is applied, which costs about 1.3 engine
calls per counted move. Counting calls instead would make the same engine look
roughly 30% faster, so it is not done.

The loop carries nothing a player would not: no score, no statistics, no
per-move bookkeeping. The clock is read once per batch rather than once per
move, because reading it per move would measure `perf_counter` as much as the
engine.

`--gate` is what makes this a gate rather than a curiosity: below it, exit 1.
CI's fast lane passes no gate and is informational; nightly passes 200000.
"""

import argparse
import platform
import sys
import time
from dataclasses import dataclass

from game2048 import bitboard, naive

DIRECTIONS = tuple(naive.MOVES)

# Moves between clock reads. Large enough that perf_counter is noise, small
# enough that the run does not overshoot --seconds noticeably.
BATCH = 2048


@dataclass
class Result:
    moves: int
    games: int
    elapsed: float

    @property
    def moves_per_second(self) -> float:
        return self.moves / self.elapsed if self.elapsed else 0.0

    @property
    def games_per_second(self) -> float:
        return self.games / self.elapsed if self.elapsed else 0.0


def machine_line() -> str:
    processor = platform.processor() or "unknown CPU"
    return (
        f"{platform.system()} {platform.machine()} | {processor} | "
        f"{platform.python_implementation()} {platform.python_version()}"
    )


def measure(seconds: float, seed: int = 0) -> Result:
    """Play random games for `seconds` and count applied moves."""
    import random

    rng = random.Random(seed)

    # Bound once. Attribute lookups in the inner loop would be measuring
    # Python's attribute lookup, not the engine.
    move = bitboard.move
    spawn = bitboard.spawn
    new_game = bitboard.new_game
    randrange = rng.randrange
    directions = DIRECTIONS

    board = new_game(rng)
    moves = 0
    games = 0

    start = time.perf_counter()
    deadline = start + seconds
    now = start

    while True:
        for _ in range(BATCH):
            offset = randrange(4)
            for index in range(4):
                direction = directions[(offset + index) & 3]
                moved, _, changed = move(board, direction)
                if changed:
                    board = spawn(moved, rng)
                    moves += 1
                    break
            else:
                games += 1
                board = new_game(rng)
        now = time.perf_counter()
        if now >= deadline:
            break

    return Result(moves=moves, games=games, elapsed=now - start)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m game2048.bench.engine_bench",
        description="Measure bitboard engine throughput in applied moves per second.",
    )
    parser.add_argument(
        "--seconds", type=float, default=30.0, help="measurement wall time"
    )
    parser.add_argument(
        "--gate",
        type=int,
        default=None,
        help="minimum moves/sec required; exit 1 below it. Omit for informational.",
    )
    parser.add_argument("--seed", type=int, default=0, help="seed for the random play")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"engine_bench: bitboard, {args.seconds:g}s target")
    print(f"machine     : {machine_line()}")

    result = measure(args.seconds, args.seed)

    print(f"moves       : {result.moves:,}")
    print(f"wall time   : {result.elapsed:.2f}s")
    print(f"moves/sec   : {result.moves_per_second:,.0f}")
    print(f"games       : {result.games:,}")
    print(f"games/sec   : {result.games_per_second:,.1f}  (secondary, never gated)")

    if args.gate is None:
        print("gate        : none (informational)")
        return 0

    passed = result.moves_per_second >= args.gate
    verdict = "PASS" if passed else "FAIL"
    print(f"gate        : {args.gate:,} moves/sec -> {verdict}")
    if not passed:
        shortfall = args.gate - result.moves_per_second
        print(
            f"short by {shortfall:,.0f} moves/sec "
            f"({result.moves_per_second / args.gate:.1%} of the gate)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
