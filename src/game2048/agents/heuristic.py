"""Greedy 1-ply baseline (SPECS section 4.2).

Scores each legal move's afterstate with handcrafted features and takes the
best. A measuring stick, not a learner: these features are strategy, and they
must never reach any learning agent's reward (CLAUDE.md golden rule 5). Nothing
outside this module imports them.

Every feature is a pure function of a grid of tile values. `act` only reads the
env through `legal_moves()` and `afterstate()`, both pure (TASK-04), so the env
is byte-identical after `act` returns.
"""

from itertools import pairwise

from game2048.env import Env, Move, State

# Hand-tuned; see LOOP_STATE TASK-10 for the measured result.
W_EMPTY = 2.7
W_MONOTONICITY = 1.0
W_SMOOTHNESS = 0.5
W_CORNER = 1.0


def _logs(grid: State) -> list[list[int]]:
    return [[value.bit_length() - 1 if value else 0 for value in row] for row in grid]


def _lines(logs: list[list[int]]) -> list[list[int]]:
    """The four rows and four columns."""
    return logs + [list(column) for column in zip(*logs)]


def empty(grid: State) -> int:
    return sum(row.count(0) for row in grid)


def monotonicity(grid: State) -> int:
    """Penalty: for each line, the smaller of its total rises and total falls.

    Zero when every row and column is monotone in either direction.
    """
    penalty = 0
    for line in _lines(_logs(grid)):
        rises = falls = 0
        for a, b in pairwise(line):
            if b > a:
                rises += b - a
            else:
                falls += a - b
        penalty += min(rises, falls)
    return penalty


def smoothness(grid: State) -> int:
    """Penalty: log2 gap between adjacent occupied cells, summed."""
    penalty = 0
    for line in _lines(_logs(grid)):
        for a, b in pairwise(line):
            if a and b:
                penalty += abs(a - b)
    return penalty


def max_in_corner(grid: State) -> int:
    top = max(max(row) for row in grid)
    return int(top in (grid[0][0], grid[0][-1], grid[-1][0], grid[-1][-1]))


def evaluate(grid: State) -> float:
    return (
        W_EMPTY * empty(grid)
        - W_MONOTONICITY * monotonicity(grid)
        - W_SMOOTHNESS * smoothness(grid)
        + W_CORNER * max_in_corner(grid)
    )


class HeuristicAgent:
    def name(self) -> str:
        return "heuristic"

    def act(self, env: Env) -> Move:
        # max() keeps the first of equal scores, so ties break by legal_moves order.
        return max(
            env.legal_moves(), key=lambda move: evaluate(env.afterstate(move)[0])
        )
