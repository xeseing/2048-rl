"""Differential test: the naive oracle against the bitboard engine.

The backbone of the whole project (SPECS section 3). Both engines play the same
games, from the same seeds, choosing the same moves, and every step is compared:
all four directions' resulting boards, all four scores, all four `changed`
flags, the spawned board, and whether the game is over.

**What this proves and what it does not.** It catches divergences. It cannot
catch a bug both engines share, and there is a real way for that to happen here:
`tables.py` is built by calling `naive.slide_row_left`, so the bitboard engine
inherits the oracle's merge rule by construction (ADR-013). That inheritance is
deliberate — it is what makes a divergence mean "the bitboard plumbing is wrong"
rather than "one of these two guessed differently" — but it does mean a wrong
merge rule would be wrong identically on both sides and pass here in silence.
The golden tests in `tests/`, whose expected values are hand-computed from
SPECS section 1 and never captured from either implementation, are what guard
that. This harness and those tests cover different things and neither is
redundant.

    python -m game2048.bench.differential --games 5000 --seed 1234
"""

import argparse
import random
import sys
import time
from dataclasses import dataclass, field

from game2048 import bitboard, naive

MOVES = naive.MOVES


@dataclass
class Divergence:
    """Everything needed to reproduce one disagreement, and nothing else."""

    seed: int
    move_index: int
    what: str
    direction: str | None = None
    naive_value: object = None
    fast_value: object = None
    naive_grid: list = field(default_factory=list)
    fast_grid: list = field(default_factory=list)
    naive_score: int = 0
    fast_score: int = 0

    def report(self) -> str:
        lines = [
            "DIVERGENCE",
            f"  seed         : {self.seed}",
            f"  move number  : {self.move_index}",
            f"  disagreement : {self.what}",
        ]
        if self.direction is not None:
            lines.append(f"  move played  : {self.direction}")
        lines += [
            f"  naive says   : {self.naive_value!r}",
            f"  bitboard says: {self.fast_value!r}",
            f"  score naive  : {self.naive_score}",
            f"  score fast   : {self.fast_score}",
            "",
            "  board at the point of disagreement, naive:",
            *_grid_lines(self.naive_grid),
            "",
            "  board at the point of disagreement, bitboard:",
            *_grid_lines(self.fast_grid),
            "",
            "  reproduce with:",
            f"    python -m game2048.bench.differential --games 1 --seed {self.seed}",
        ]
        return "\n".join(lines)


def _grid_lines(grid: list) -> list[str]:
    return ["    " + " ".join(f"{value:>6}" for value in row) for row in grid]


def compare_game(seed: int) -> Divergence | None:
    """Play one game through both engines in lockstep. None means they agreed.

    Each engine gets its own RNG seeded identically rather than sharing one, so
    an engine that consumes a different number of draws per spawn shows up as a
    board divergence rather than being hidden by a shared stream.
    """
    naive_rng = random.Random(seed)
    fast_rng = random.Random(seed)
    policy = random.Random(seed ^ 0x5EED)

    grid = naive.new_game(naive_rng)
    board = bitboard.new_game(fast_rng)

    def mismatch(move_index, what, naive_value, fast_value, direction=None):
        return Divergence(
            seed=seed,
            move_index=move_index,
            what=what,
            direction=direction,
            naive_value=naive_value,
            fast_value=fast_value,
            naive_grid=grid,
            fast_grid=bitboard.decode(board),
            naive_score=naive_score,
            fast_score=fast_score,
        )

    naive_score = 0
    fast_score = 0
    move_index = 0

    if bitboard.decode(board) != grid:
        return mismatch(0, "opening board", grid, bitboard.decode(board))

    while True:
        # One pass over all four directions, comparing everything, rather than
        # asking each engine for legal_moves and then moving: same cost, and it
        # checks the three directions that are not taken as well as the one
        # that is.
        naive_results = {d: naive.move(grid, d) for d in MOVES}
        fast_results = {d: bitboard.move(board, d) for d in MOVES}

        for direction in MOVES:
            slow_grid, slow_score, slow_changed = naive_results[direction]
            fast_board, quick_score, quick_changed = fast_results[direction]

            if slow_changed != quick_changed:
                return mismatch(
                    move_index, "changed flag", slow_changed, quick_changed, direction
                )
            if slow_score != quick_score:
                return mismatch(
                    move_index, "move score", slow_score, quick_score, direction
                )
            if bitboard.decode(fast_board) != slow_grid:
                return mismatch(
                    move_index,
                    "board after move",
                    slow_grid,
                    bitboard.decode(fast_board),
                    direction,
                )

        # Derived from the results already computed above. Calling
        # naive.legal_moves / bitboard.legal_moves / is_game_over here instead
        # would recompute all four moves four more times per step, for the same
        # answer: 20 move computations per step rather than 8.
        legal = [d for d in MOVES if naive_results[d][2]]
        fast_legal = [d for d in MOVES if fast_results[d][2]]
        if legal != fast_legal:
            return mismatch(move_index, "legal moves", legal, fast_legal)

        if not legal:
            if naive_score != fast_score:
                return mismatch(move_index, "final score", naive_score, fast_score)
            return None

        direction = policy.choice(legal)
        grid, gained, _ = naive_results[direction]
        board, fast_gained, _ = fast_results[direction]
        naive_score += gained
        fast_score += fast_gained

        grid = naive.spawn(grid, naive_rng)
        board = bitboard.spawn(board, fast_rng)
        move_index += 1

        if bitboard.decode(board) != grid:
            return mismatch(
                move_index, "board after spawn", grid, bitboard.decode(board), direction
            )
        if naive_score != fast_score:
            return mismatch(
                move_index, "running score", naive_score, fast_score, direction
            )


def run(games: int, seed: int, progress_every: int = 0) -> Divergence | None:
    """Play `games` games, seeds `seed`..`seed + games - 1`. None means agreement."""
    for index in range(games):
        divergence = compare_game(seed + index)
        if divergence is not None:
            return divergence
        if progress_every and (index + 1) % progress_every == 0:
            print(f"  {index + 1}/{games} games agreed", flush=True)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m game2048.bench.differential",
        description="Play identical games through the naive and bitboard engines "
        "and compare every step.",
    )
    parser.add_argument("--games", type=int, default=5000, help="how many games")
    parser.add_argument("--seed", type=int, default=1234, help="first game's seed")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=0,
        help="print a line every N games (0 = silent)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(
        f"differential: {args.games} games, seeds "
        f"{args.seed}..{args.seed + args.games - 1}",
        flush=True,
    )
    started = time.perf_counter()
    divergence = run(args.games, args.seed, args.progress_every)
    elapsed = time.perf_counter() - started

    if divergence is not None:
        print(divergence.report(), file=sys.stderr)
        print(f"\nFAILED after {elapsed:.1f}s", file=sys.stderr)
        return 1

    print(f"OK: {args.games} games, 0 divergences, {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
