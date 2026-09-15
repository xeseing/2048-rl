"""The naive 2048 engine — the permanent oracle.

Readable above all else. This file is never optimised and never deleted. Its only
two jobs are to be obviously correct, and to catch the bitboard engine lying
(SPECS section 2.1). If you are ever tempted to make this faster, don't: the
speed lives in `bitboard.py`, and the moment the two disagree this file is the
one that is right.

Boards are `list[list[int]]`, four rows of four, holding tile values (not
exponents). Empty is 0. Every function here returns a new board rather than
mutating its argument, so an aliasing bug cannot quietly corrupt the oracle.
"""

import random

SIZE = 4
MOVES = ("up", "down", "left", "right")

# SPECS section 1: a spawned tile is 2 with probability 0.9, 4 with 0.1.
PROBABILITY_OF_FOUR = 0.1

Board = list[list[int]]


def slide_row_left(row: list[int]) -> tuple[list[int], int]:
    """Slide one row to the left. Returns (new_row, score_gained).

    Honest three-step version, exactly as the rules are written:

    1. compress — drop the gaps, tiles keep their order
    2. merge    — walk left to right, merging each adjacent equal pair once
    3. compress — pad back out to SIZE with zeros

    Walking left to right in step 2 is what makes merges resolve from the edge
    being moved toward, inward: [2,2,2,0] becomes [4,2,0,0] and never
    [2,4,0,0] (SPECS trap 1). Skipping two tiles after a merge is what stops a
    freshly merged tile merging again in the same move: [4,4,4,4] becomes
    [8,8,0,0] and never [16,0,0,0] (SPECS trap 2).
    """
    tiles = [value for value in row if value != 0]

    merged: list[int] = []
    score = 0
    index = 0
    while index < len(tiles):
        is_pair = index + 1 < len(tiles) and tiles[index] == tiles[index + 1]
        if is_pair:
            combined = tiles[index] * 2
            merged.append(combined)
            score += combined  # the score is the value of the resulting tile
            index += 2  # both tiles are consumed; the new one cannot merge again
        else:
            merged.append(tiles[index])
            index += 1

    return merged + [0] * (SIZE - len(merged)), score


def _transpose(board: Board) -> Board:
    return [list(column) for column in zip(*board)]


def _reverse_rows(board: Board) -> Board:
    return [row[::-1] for row in board]


def _to_left_frame(board: Board, direction: str) -> Board:
    """Rotate/reflect the board so that `direction` becomes a left-move.

    Every direction is a left-move wearing a disguise, so `slide_row_left` is
    the only sliding code in the engine and the other three directions cannot
    drift away from it (SPECS section 2.1).
    """
    if direction == "left":
        return [row[:] for row in board]
    if direction == "right":
        return _reverse_rows(board)
    if direction == "up":
        return _transpose(board)
    return _reverse_rows(_transpose(board))  # down


def _from_left_frame(board: Board, direction: str) -> Board:
    """Undo `_to_left_frame`. Both helpers are their own inverses, in reverse."""
    if direction == "left":
        return board
    if direction == "right":
        return _reverse_rows(board)
    if direction == "up":
        return _transpose(board)
    return _transpose(_reverse_rows(board))  # down


def move(board: Board, direction: str) -> tuple[Board, int, bool]:
    """Apply a move. Returns (new_board, score_gained, changed).

    This is the deterministic half of a turn — the afterstate. No tile is
    spawned here. `changed` is False when the move is illegal, and an illegal
    move returns the board untouched with zero score: never a partial slide, and
    never a spawn (SPECS trap 3). Raising on an illegal move is `env.py`'s job,
    not the engine's.
    """
    if direction not in MOVES:
        raise ValueError(f"unknown direction {direction!r}, expected one of {MOVES}")

    oriented = _to_left_frame(board, direction)

    slid: Board = []
    score = 0
    for row in oriented:
        new_row, row_score = slide_row_left(row)
        slid.append(new_row)
        score += row_score

    moved = _from_left_frame(slid, direction)

    if moved == board:
        return [row[:] for row in board], 0, False
    return moved, score, True


def legal_moves(board: Board) -> list[str]:
    """The directions that change the board. A move is legal only if it does."""
    return [direction for direction in MOVES if move(board, direction)[2]]


def is_game_over(board: Board) -> bool:
    """No legal move in any of the four directions (SPECS section 1)."""
    return not legal_moves(board)


def spawn(board: Board, rng: random.Random) -> Board:
    """Place one new tile: uniform over empty cells, 2 at p=0.9 and 4 at p=0.1.

    Takes an explicit `random.Random` so every game is reproducible from its
    seed. The two draws happen in a fixed order — cell first, then value — and
    that order is part of what a seed reproduces; changing it changes every
    recorded transcript.
    """
    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    if not empty:
        raise ValueError("cannot spawn on a full board")

    row, column = rng.choice(empty)
    value = 4 if rng.random() < PROBABILITY_OF_FOUR else 2

    spawned = [existing[:] for existing in board]
    spawned[row][column] = value
    return spawned


def new_game(rng: random.Random) -> Board:
    """An empty board with two tiles spawned into it (SPECS section 1)."""
    board = [[0] * SIZE for _ in range(SIZE)]
    return spawn(spawn(board, rng), rng)
