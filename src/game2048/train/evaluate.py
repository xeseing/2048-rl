"""The shared eval harness (SPECS section 3, 4).

    python -m game2048.train.evaluate --agent random --games 1000 --seed-base 900000

Game i is `Env(seed=seed_base + i)`. **Seeds 900000 and up are the held-out
eval range**: nothing trains, tunes or tests on them (SPECS trap 7).

Each baseline has a gate describing what it is supposed to look like; outside
it, exit 1. The random gate is a range rather than a floor, because a "random"
agent that scores 3,000 is not random, whatever its code says.
"""

import argparse
import functools
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass

from game2048.agents.heuristic import HeuristicAgent
from game2048.agents.ntuple import NTupleAgent, NTupleNetwork
from game2048.agents.random_agent import RandomAgent
from game2048.env import Env

# Trained weights for `--agent ntuple`; `--weights` replaces it.
WEIGHTS = "runs/td-01/weights.npz"


@functools.cache
def load_ntuple(path: str) -> NTupleAgent:
    """One load per path, not per game: the agent holds no per-game state."""
    return NTupleAgent(NTupleNetwork.load(path))


AGENTS = {
    "random": lambda seed: RandomAgent(seed=seed),
    "heuristic": lambda seed: HeuristicAgent(),
    "ntuple": lambda seed: load_ntuple(WEIGHTS),
}


def agent_seed(game_seed: int) -> str:
    """The agent's own seed for a game.

    Not `game_seed` itself: `Random(k)` in the agent and `Random(k)` in the env
    would draw the same stream, and the agent's moves would mirror the spawns.
    """
    return f"{game_seed}:agent"


@dataclass
class Report:
    agent: str
    seed_base: int
    scores: list[int]
    max_tiles: list[int]
    moves: int
    seconds: float

    @property
    def games(self) -> int:
        return len(self.scores)

    @property
    def mean(self) -> float:
        return statistics.mean(self.scores)

    @property
    def median(self) -> float:
        return statistics.median(self.scores)

    @property
    def max(self) -> int:
        return max(self.scores)

    def rate(self, tile: int) -> float:
        """Fraction of games whose max tile reached at least `tile`."""
        return sum(t >= tile for t in self.max_tiles) / self.games

    @property
    def histogram(self) -> dict[int, int]:
        return dict(sorted(Counter(self.max_tiles).items()))

    @property
    def ms_per_move(self) -> float:
        return 1000 * self.seconds / self.moves


GATES = {
    "random": ("750 <= mean <= 1250", lambda r: 750 <= r.mean <= 1250),
    "heuristic": (
        "mean >= 3000 and 2048 rate >= 5%",
        lambda r: r.mean >= 3000 and r.rate(2048) >= 0.05,
    ),
    "ntuple": (
        "mean >= 15000 and 2048 rate >= 50%",
        lambda r: r.mean >= 15000 and r.rate(2048) >= 0.5,
    ),
}


def evaluate(agent: str, games: int, seed_base: int) -> Report:
    scores, max_tiles, moves = [], [], 0
    start = time.perf_counter()
    for seed in range(seed_base, seed_base + games):
        env = Env(seed=seed)
        player = AGENTS[agent](agent_seed(seed))
        while env.legal_moves():
            env.step(player.act(env))
        scores.append(env.score)
        max_tiles.append(max(map(max, env.state)))
        moves += env.moves
    seconds = time.perf_counter() - start
    return Report(agent, seed_base, scores, max_tiles, moves, seconds)


def gate(report: Report) -> tuple[str, bool]:
    description, check = GATES[report.agent]
    return description, check(report)


def table(report: Report) -> str:
    description, passed = gate(report)
    seeds = f"{report.seed_base}..{report.seed_base + report.games - 1}"
    work = f"{report.moves:,} moves, {report.seconds:.1f}s"
    lines = [
        f"agent       : {report.agent}",
        f"games       : {report.games:,} (seeds {seeds})",
        f"mean score  : {report.mean:,.0f}",
        f"median score: {report.median:,.0f}",
        f"max score   : {report.max:,}",
        f"2048 rate   : {report.rate(2048):.1%}",
        f"4096 rate   : {report.rate(4096):.1%}",
        f"ms/move     : {report.ms_per_move:.3f} ({work})",
        "max tile    : games",
    ]
    lines += [f"{tile:>11} : {count}" for tile, count in report.histogram.items()]
    lines.append(f"gate        : {description} -> {'PASS' if passed else 'FAIL'}")
    return "\n".join(lines)


def as_json(report: Report) -> str:
    description, passed = gate(report)
    return json.dumps(
        {
            "agent": report.agent,
            "games": report.games,
            "seed_base": report.seed_base,
            "mean": report.mean,
            "median": report.median,
            "max": report.max,
            "rate_2048": report.rate(2048),
            "rate_4096": report.rate(4096),
            "histogram": report.histogram,
            "moves": report.moves,
            "seconds": report.seconds,
            "ms_per_move": report.ms_per_move,
            "gate": {"rule": description, "passed": passed},
        },
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    global WEIGHTS
    parser = argparse.ArgumentParser(prog="python -m game2048.train.evaluate")
    parser.add_argument("--agent", choices=sorted(AGENTS), required=True)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed-base", type=int, default=900_000)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--weights", default=WEIGHTS, help="ntuple weights file")
    args = parser.parse_args(argv)
    WEIGHTS = args.weights

    report = evaluate(args.agent, args.games, args.seed_base)
    print(as_json(report) if args.json else table(report))
    return 0 if gate(report)[1] else 1


if __name__ == "__main__":
    sys.exit(main())
