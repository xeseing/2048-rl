"""The fast engine: one 64-bit int per board (SPECS section 2.2).

16 nibbles of log2(tile), row-major, cell (0,0) in the **highest** nibble, so a
board reads left to right and top to bottom in hex. Row r occupies bits
`16*(3-r) .. 16*(3-r)+15`, which means a row lifted out of a board is exactly
the 16-bit key `tables.ROW_LEFT` is indexed by.

Structurally this file is the naive engine with the row slide replaced by a
table lookup: reorient so the move becomes a left-move, slide the four rows,
reorient back. Keeping the shape identical is deliberate — TASK-08 compares the
two engines, and a reviewer should be able to see that they agree by reading
them side by side rather than by trusting the test.

**The overflow check is not optional.** `tables.ROW_LEFT` is indexed raw here,
for speed, and 767 of its entries are the `OVERFLOW_ROW` sentinel rather than a
row. Every lookup below checks before using the value, so a merge past the
32768 ceiling raises instead of writing `0xFFFF` — four 32768s — into the
board. That is ADR-013's whole reason for existing (SPECS trap 4).
"""

import random

from game2048 import naive, tables

SIZE = naive.SIZE
MOVES = naive.MOVES

ROW_BITS = 16
ROW_MASK = 0xFFFF
CELL_BITS = 4
CELL_MASK = 0xF

# Row r starts at this bit offset. Row 0 is the highest.
ROW_SHIFTS = tuple(ROW_BITS * (SIZE - 1 - r) for r in range(SIZE))

Board = int


def encode(grid: list[list[int]]) -> Board:
    """Pack a 4x4 grid of tile values into one 64-bit int."""
    board = 0
    for row in grid:
        board = (board << ROW_BITS) | tables.encode_row(row)
    return board


def decode(board: Board) -> list[list[int]]:
    """Unpack a 64-bit board back into a 4x4 grid of tile values."""
    return [tables.decode_row((board >> shift) & ROW_MASK) for shift in ROW_SHIFTS]


# Masks for `transpose`. The first triple swaps nibbles across the diagonal
# within each 2x2 block of nibbles; the second swaps the 2x2 blocks themselves.
# Two passes of mask-shift-or replace sixteen iterations of shift-mask-shift-or.
_DIAGONAL_KEEP = 0xF0F00F0FF0F00F0F
_DIAGONAL_UP = 0x0000F0F00000F0F0
_DIAGONAL_DOWN = 0x0F0F00000F0F0000
_BLOCK_KEEP = 0xFF00FF0000FF00FF
_BLOCK_UP = 0x00FF00FF00000000
_BLOCK_DOWN = 0x00000000FF00FF00


def transpose(board: Board) -> Board:
    """Reflect the board across its main diagonal.

    The cell-by-cell version this replaced cost 3.16us; this costs about a
    sixth of that, and `up` and `down` each pay it twice per move. Verified
    against the old implementation on 200,000 random 64-bit values and 50,000
    structured boards before the old one was deleted, and `tests/test_bitboard.py`
    checks it against `zip(*grid)`, which is an independent definition rather
    than a second copy of this trick.
    """
    folded = (
        (board & _DIAGONAL_KEEP)
        | ((board & _DIAGONAL_UP) << 12)
        | ((board & _DIAGONAL_DOWN) >> 12)
    )
    return (
        (folded & _BLOCK_KEEP)
        | ((folded & _BLOCK_UP) >> 24)
        | ((folded & _BLOCK_DOWN) << 24)
    )


def _reverse_rows(board: Board) -> Board:
    """Reverse the four cells within every row."""
    result = 0
    for shift in ROW_SHIFTS:
        row = (board >> shift) & ROW_MASK
        reversed_row = 0
        for cell in range(SIZE):
            nibble = (row >> (CELL_BITS * cell)) & CELL_MASK
            reversed_row |= nibble << (CELL_BITS * (SIZE - 1 - cell))
        result |= reversed_row << shift
    return result


def _slide_left(board: Board) -> tuple[Board, int]:
    """Slide all four rows left via the tables. Raises on nibble overflow."""
    result = 0
    score = 0
    for shift in ROW_SHIFTS:
        row = (board >> shift) & ROW_MASK
        moved = tables.ROW_LEFT[row]
        # Checked before the value is used, never after. An unchecked lookup
        # would write 0xFFFF into the board and carry on (ADR-013).
        if moved == tables.OVERFLOW_ROW:
            raise tables.NibbleOverflow(
                f"row {row:#06x} -> {tables.decode_row(row)} merges past "
                f"{tables.MAX_TILE}; board {board:#018x}"
            )
        result |= moved << shift
        score += tables.ROW_SCORE[row]
    return result, score


def _to_left_frame(board: Board, direction: str) -> Board:
    """Reorient so `direction` becomes a left-move. Mirrors naive._to_left_frame."""
    if direction == "left":
        return board
    if direction == "right":
        return _reverse_rows(board)
    if direction == "up":
        return transpose(board)
    return _reverse_rows(transpose(board))  # down


def _from_left_frame(board: Board, direction: str) -> Board:
    """Undo `_to_left_frame`."""
    if direction == "left":
        return board
    if direction == "right":
        return _reverse_rows(board)
    if direction == "up":
        return transpose(board)
    return transpose(_reverse_rows(board))  # down


def move(board: Board, direction: str) -> tuple[Board, int, bool]:
    """Apply a move. Returns (new_board, score_gained, changed).

    No spawn, no raise on an illegal move — the board comes back untouched with
    `changed` False, exactly as `naive.move` behaves. A merge past the nibble
    ceiling does raise, because there is no board it could honestly return.
    """
    if direction not in MOVES:
        raise ValueError(f"unknown direction {direction!r}, expected one of {MOVES}")

    oriented = _to_left_frame(board, direction)
    slid, score = _slide_left(oriented)
    moved = _from_left_frame(slid, direction)

    if moved == board:
        return board, 0, False
    return moved, score, True


def legal_moves(board: Board) -> list[str]:
    """The directions that change the board."""
    return [direction for direction in MOVES if move(board, direction)[2]]


def is_game_over(board: Board) -> bool:
    return not legal_moves(board)


def empty_cells(board: Board) -> list[int]:
    """Indices 0..15 of the empty cells, row-major.

    Row-major order matters: `spawn` picks from this list with `rng.choice`, and
    the naive engine builds its list the same way. A different order would draw
    a different cell from the same seed and TASK-08 could never replay both
    engines from one seed.
    """
    return [
        index
        for index in range(SIZE * SIZE)
        if (board >> (CELL_BITS * (SIZE * SIZE - 1 - index))) & CELL_MASK == 0
    ]


def spawn(board: Board, rng: random.Random) -> Board:
    """Place one tile: uniform over empty cells, 2 at p=0.9 and 4 at p=0.1.

    Draws the cell first and the value second, the same order as `naive.spawn`,
    so both engines consume an identical RNG stream.
    """
    empty = empty_cells(board)
    if not empty:
        raise ValueError("cannot spawn on a full board")

    index = rng.choice(empty)
    exponent = 2 if rng.random() < naive.PROBABILITY_OF_FOUR else 1
    return board | (exponent << (CELL_BITS * (SIZE * SIZE - 1 - index)))


def new_game(rng: random.Random) -> Board:
    """An empty board with two tiles spawned into it."""
    return spawn(spawn(0, rng), rng)
