"""The floor (SPECS section 4.1): uniform over the legal moves."""

import random

from game2048.env import Env, Move


class RandomAgent:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def name(self) -> str:
        return "random"

    def act(self, env: Env) -> Move:
        return self._rng.choice(env.legal_moves())
