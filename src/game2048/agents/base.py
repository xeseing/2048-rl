"""The protocol every agent satisfies (SPECS section 4).

`act` takes the env, not a state: an agent looks ahead through
`env.afterstate()` and `env.legal_moves()`, never through an engine import.
"""

from typing import Protocol, runtime_checkable

from game2048.env import Env, Move


@runtime_checkable
class Agent(Protocol):
    def act(self, env: Env) -> Move: ...
    def name(self) -> str: ...
