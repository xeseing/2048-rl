"""Track A: N-tuple value network + TD(0) on afterstates (SPECS section 4.4).

`V(afterstate) = sum of W[index]` over every tuple in every one of the board's
8 symmetries. A tuple's index is its cells' exponents (log2 tile, 0 = empty)
read as base-16. All tuples share one flat weight array; tuple t's LUT is the
slice starting at `t * 16**n`.

Boards come in as `(N, 16)` exponent arrays, row-major. That is the only board
form this module knows: the agent converts `Env` grids, the trainer converts
bitboards, and both then go through the same `indices`.

The learner sees merge score and nothing else (CLAUDE.md golden rule 5).
"""

import numpy as np

from game2048.env import Env, Move

# Stage 1: four 5-tuples, row-major cell numbers. Two row-plus-one shapes and
# two 2x2-plus-one shapes; the 8 symmetries carry each one to every edge.
STAGE1 = ((0, 1, 2, 3, 4), (4, 5, 6, 7, 8), (0, 1, 2, 4, 5), (4, 5, 6, 8, 9))

_GRID = np.arange(16).reshape(4, 4)
# Each row maps a transformed board's cell to the original cell it reads.
SYMMETRIES = np.array(
    [np.rot90(g, k).ravel() for g in (_GRID, _GRID.T) for k in range(4)]
)


class NTupleNetwork:
    def __init__(self, tuples=STAGE1, weights: np.ndarray | None = None) -> None:
        n = len(tuples[0])
        assert all(len(t) == n for t in tuples), "tuples must share one length"
        self.tuples = tuple(tuple(t) for t in tuples)
        size = 16**n
        # (features, n): the original cell behind each position of each tuple
        # under each symmetry. 8 symmetries x len(tuples) features per board.
        self._cells = np.array(
            [sym[list(t)] for sym in SYMMETRIES for t in self.tuples]
        )
        self._offsets = np.array(
            [t * size for _ in SYMMETRIES for t in range(len(self.tuples))]
        )
        self._powers = 16 ** np.arange(n - 1, -1, -1)
        if weights is None:
            weights = np.zeros(len(self.tuples) * size, dtype=np.float32)
        assert weights.shape == (len(self.tuples) * size,), weights.shape
        self.weights = weights

    @property
    def features(self) -> int:
        """LUT entries read per board: tuples x 8 symmetries."""
        return len(self._cells)

    def indices(self, exponents: np.ndarray) -> np.ndarray:
        """(N, 16) exponents -> (N, features) flat weight indices."""
        return exponents[:, self._cells] @ self._powers + self._offsets

    def values(self, exponents: np.ndarray) -> np.ndarray:
        return self.weights[self.indices(exponents)].sum(axis=1)

    def update(self, exponents: np.ndarray, deltas: np.ndarray, alpha: float) -> None:
        """`V(s') += alpha / features * delta` on every feature of each board.

        SPECS trap 6: without the division the update is `features` times too
        large and the weights diverge. `np.add.at` accumulates entries that
        repeat, within a board (symmetric boards) and across a batch.
        """
        idx = self.indices(exponents)
        step = (alpha / self.features) * deltas.astype(np.float32)
        np.add.at(self.weights, idx.ravel(), np.repeat(step, idx.shape[1]))

    def save(self, path) -> None:
        np.savez_compressed(
            path, weights=self.weights, tuples=np.array(self.tuples, dtype=np.int64)
        )

    @classmethod
    def load(cls, path) -> "NTupleNetwork":
        with np.load(path) as data:
            tuples = tuple(map(tuple, data["tuples"].tolist()))
            return cls(tuples, data["weights"])


def grid_exponents(grids: list[list[list[int]]]) -> np.ndarray:
    """Tile-value grids -> (N, 16) exponents."""
    return np.array(
        [[v.bit_length() - 1 if v else 0 for row in g for v in row] for g in grids],
        dtype=np.int64,
    )


class NTupleAgent:
    """Greedy on `reward + V(afterstate)`. No RNG, no exploration."""

    def __init__(self, network: NTupleNetwork) -> None:
        self.network = network

    def name(self) -> str:
        return "ntuple"

    def act(self, env: Env) -> Move:
        moves = env.legal_moves()
        results = [env.afterstate(m) for m in moves]
        values = self.network.values(grid_exponents([r[0] for r in results]))
        totals = values + np.array([r[1] for r in results])
        return moves[int(np.argmax(totals))]
