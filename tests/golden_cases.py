"""Golden test data, shared by every engine.

Each value here is hand-computed from the rules in SPECS section 1. Nothing was
captured from any implementation's output.

This module exists so that the naive engine and the bitboard engine are checked
against **the same expected values**, written once. Two copies of a golden table
drift, and when they do the differential test at TASK-08 starts comparing two
sets of expectations instead of two engines.

Boards here are `list[list[int]]` of tile values. The bitboard tests convert at
their own boundary; the numbers do not change.
"""

# --------------------------------------------------------------------------
# Single-row cases. (row, expected after sliding left, score gained)
# --------------------------------------------------------------------------

# SPECS section 7, trap 1: merges resolve from the edge being moved toward.
TRAP_EDGE_ORDER = ([2, 2, 2, 0], [4, 2, 0, 0], 4)

# SPECS section 7, trap 2: a tile produced by a merge cannot merge again.
TRAP_MERGE_ONCE = ([4, 4, 4, 4], [8, 8, 0, 0], 16)

# Trap 2 again: the new 4 does not go on to eat the existing 4.
TRAP_NO_CASCADE = ([2, 2, 4, 0], [4, 4, 0, 0], 4)

# The two remaining row cases named in SPECS section 1.
FOUR_EQUAL_TILES = ([2, 2, 2, 2], [4, 4, 0, 0], 8)
TWO_DISTINCT_PAIRS = ([4, 4, 2, 2], [8, 4, 0, 0], 12)

ROW_CASES = [
    TRAP_EDGE_ORDER,
    TRAP_MERGE_ONCE,
    TRAP_NO_CASCADE,
    FOUR_EQUAL_TILES,
    TWO_DISTINCT_PAIRS,
    ([0, 0, 0, 0], [0, 0, 0, 0], 0),
    ([2, 0, 0, 0], [2, 0, 0, 0], 0),
    ([0, 0, 0, 2], [2, 0, 0, 0], 0),
    ([2, 4, 8, 16], [2, 4, 8, 16], 0),
    ([0, 2, 0, 2], [4, 0, 0, 0], 4),
    ([2, 0, 0, 2], [4, 0, 0, 0], 4),
    ([4, 2, 2, 0], [4, 4, 0, 0], 4),
    ([2, 2, 0, 4], [4, 4, 0, 0], 4),
]

# --------------------------------------------------------------------------
# One board, all four directions. Chosen so every direction does something
# different and every row and column contains at least one merge.
# --------------------------------------------------------------------------

GOLDEN = [
    [2, 2, 4, 0],
    [0, 4, 4, 4],
    [2, 0, 2, 2],
    [8, 8, 0, 0],
]

# (direction, expected board, score gained)
GOLDEN_MOVES = [
    ("left", [[4, 4, 0, 0], [8, 4, 0, 0], [4, 2, 0, 0], [16, 0, 0, 0]], 32),
    ("right", [[0, 0, 4, 4], [0, 0, 4, 8], [0, 0, 2, 4], [0, 0, 0, 16]], 32),
    ("up", [[4, 2, 8, 4], [8, 4, 2, 2], [0, 8, 0, 0], [0, 0, 0, 0]], 12),
    ("down", [[0, 0, 0, 0], [0, 2, 0, 0], [4, 4, 8, 4], [8, 8, 2, 2]], 12),
]

# --------------------------------------------------------------------------
# Legality and game over.
# --------------------------------------------------------------------------

# Full, no two equal neighbours anywhere: no legal move in any direction.
DEAD = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 2, 4],
    [16, 2, 4, 8],
]

# One empty cell at (3, 3). Left and up change nothing; down and right do.
WEDGED = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 2, 4],
    [16, 2, 4, 0],
]
WEDGED_LEGAL_MOVES = ["down", "right"]

# Full, but the bottom row has an adjacent pair, so the game is not over.
ALIVE = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 2, 4],
    [16, 2, 4, 4],
]

# --------------------------------------------------------------------------
# The nibble ceiling (SPECS section 7, trap 4). 32768 is the largest tile a
# nibble can hold, so merging two of them has nowhere to go.
# --------------------------------------------------------------------------

# One merge away from the ceiling: 16384 + 16384 makes 32768, which is legal.
# The pre-existing 32768 does not join in — a merged tile cannot merge again.
ONE_NIBBLE_FROM_OVERFLOW = [
    [16384, 16384, 32768, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
]
ONE_NIBBLE_FROM_OVERFLOW_AFTER_LEFT = [
    [32768, 32768, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
]
ONE_NIBBLE_FROM_OVERFLOW_SCORE = 32768

# In each of these the two 32768s are adjacent along the axis named, so moving
# that way merges them into 65536. (The horizontal pair also overflows moving the
# other way along its own axis; the key is that the named move must raise.)
OVERFLOW_BOARDS = {
    "left": [[32768, 32768, 0, 0], [0] * 4, [0] * 4, [0] * 4],
    "right": [[0, 0, 32768, 32768], [0] * 4, [0] * 4, [0] * 4],
    "up": [[32768, 0, 0, 0], [32768, 0, 0, 0], [0] * 4, [0] * 4],
    "down": [[0] * 4, [0] * 4, [32768, 0, 0, 0], [32768, 0, 0, 0]],
}
