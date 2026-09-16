"""The environment agents see. Frozen API — SPECS section 2.3.

This is the only surface an agent is allowed to touch. An agent that imports
`bitboard` or `naive` directly is a bug, because the whole point of TASK-08 is
that the two engines are interchangeable behind this file.

One turn is two steps:

    s --(move, deterministic)--> s' --(random spawn)--> s_next
      state                      afterstate             next state

`afterstate()` gives you the first arrow and nothing else. It is pure: no spawn,
no score, no RNG draw, no mutation. Track A learns `V(afterstate)`, so this
method is called speculatively on moves that will never be taken, thousands of
times per game. If it ever leaks a side effect, every agent built on it trains
on a world that does not exist, and nothing visibly fails.
"""

import random
from typing import Literal

from game2048 import naive, render

Move = Literal["up", "down", "left", "right"]
State = list[list[int]]

# SPECS section 1: reaching 2048 is a win event; play continues to the real game
# over, so this never ends an episode.
WINNING_TILE = 2048


class IllegalMove(Exception):
    """A move that would not change the board.

    SPECS section 1: playing an illegal move is an error, not a no-op turn.
    Returning quietly instead of raising is how a spawn sneaks in on a move that
    never happened (SPECS trap 3).
    """


class Env:
    """A 4x4 2048 game. Every stochastic draw comes from `seed`."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.reset()

    def reset(self, seed: int | None = None) -> State:
        """Start a new game. Returns the opening state.

        With `seed`, the RNG is replaced, so `reset(seed=k)` always produces the
        same opening. Without it the existing stream continues, which keeps a
        run of many games reproducible from the one seed the env was built with.
        """
        if seed is not None:
            self._rng = random.Random(seed)

        self._board = naive.new_game(self._rng)
        self.score = 0
        self.moves = 0
        self.won = False
        return self.state

    @property
    def state(self) -> State:
        """A copy of the board. Callers never get a handle on the real one."""
        return [row[:] for row in self._board]

    def legal_moves(self) -> list[Move]:
        """The moves that change the board. Any other move is an IllegalMove."""
        return naive.legal_moves(self._board)

    def afterstate(self, move: Move) -> tuple[State, int, bool]:
        """Deterministic part only. Returns (afterstate, reward, changed).

        Does not mutate the env and does not spawn. `naive.move` builds a fresh
        board and reads nothing from the RNG, so purity here is structural
        rather than a promise this method keeps by being careful.
        """
        return naive.move(self._board, move)

    def step(self, move: Move) -> tuple[State, int, bool, dict]:
        """(next_state, reward, done, info). Raises IllegalMove if not changed.

        The legality check happens before anything is assigned, so there is no
        window in which a rejected move has already spawned or scored.
        """
        afterstate, reward, changed = naive.move(self._board, move)
        if not changed:
            raise IllegalMove(f"{move!r} does not change the board")

        self._board = naive.spawn(afterstate, self._rng)
        self.score += reward
        self.moves += 1

        max_tile = max(value for row in self._board for value in row)
        if max_tile >= WINNING_TILE:
            self.won = True

        done = naive.is_game_over(self._board)
        info = {
            "score": self.score,
            "max_tile": max_tile,
            "won": self.won,
            "moves": self.moves,
        }
        return self.state, reward, done, info

    def render(self) -> str:
        """The board as text. Returns; never prints — see render.py."""
        return render.frame(self._board, self.score, self.moves)
