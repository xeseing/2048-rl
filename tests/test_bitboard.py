"""The bitboard engine (SPECS section 2.2).

Every golden value here comes from `tests/golden_cases.py`, the same module the
naive engine's tests read. Nothing is re-typed: the bitboard converts at its own
boundary and the numbers do not change. Two copies of a golden table drift, and
when they do, TASK-08 stops comparing two engines and starts comparing two sets
of expectations.

The other thing this file exists for is ADR-013's trap. `tables.ROW_LEFT` is
indexed raw here, for speed, and a raw index that forgets its overflow check is
exactly the failure mode the sentinels were chosen to make loud. So every
direction is walked up to the ceiling and over it.
"""

import random

import pytest
from golden_cases import (
    ALIVE,
    DEAD,
    GOLDEN,
    GOLDEN_MOVES,
    ONE_NIBBLE_FROM_OVERFLOW,
    ONE_NIBBLE_FROM_OVERFLOW_AFTER_LEFT,
    ONE_NIBBLE_FROM_OVERFLOW_SCORE,
    OVERFLOW_BOARDS,
    ROW_CASES,
    WEDGED,
    WEDGED_LEGAL_MOVES,
)

from game2048 import bitboard, naive, tables

DIRECTIONS = ("up", "down", "left", "right")


def row_as_board(row):
    """A single row placed in row 0, the rest empty."""
    return [list(row), [0] * 4, [0] * 4, [0] * 4]


def random_grid(rng, max_exponent=11):
    """A random board well below the nibble ceiling."""
    return [
        [
            0 if (e := rng.randrange(0, max_exponent + 1)) == 0 else 1 << e
            for _ in range(4)
        ]
        for _ in range(4)
    ]


# ---------------------------------------------------------------------------
# Packing: 16 nibbles of log2(tile), row-major, cell (0,0) highest.
# ---------------------------------------------------------------------------


def test_the_board_packs_row_major_with_cell_zero_zero_highest():
    grid = [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert bitboard.encode(grid) == 0x1234_0000_0000_0000


def test_decode_is_the_inverse_of_encode():
    assert bitboard.decode(0x1234_0000_0000_0000) == [
        [2, 4, 8, 16],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]


def test_encode_decode_round_trips_on_random_boards():
    rng = random.Random(0)
    for _ in range(2000):
        grid = random_grid(rng)
        assert bitboard.decode(bitboard.encode(grid)) == grid


def test_an_empty_board_is_zero():
    assert bitboard.encode([[0] * 4 for _ in range(4)]) == 0


def test_a_board_never_exceeds_64_bits():
    full = [[32768] * 4 for _ in range(4)]
    assert bitboard.encode(full) == 0xFFFF_FFFF_FFFF_FFFF
    assert bitboard.encode(full).bit_length() <= 64


# ---------------------------------------------------------------------------
# transpose
# ---------------------------------------------------------------------------


def test_transpose_matches_flipping_the_grid():
    rng = random.Random(1)
    for _ in range(2000):
        grid = random_grid(rng)
        flipped = [list(column) for column in zip(*grid)]
        assert bitboard.decode(bitboard.transpose(bitboard.encode(grid))) == flipped


def test_transpose_is_its_own_inverse():
    rng = random.Random(2)
    for _ in range(2000):
        board = bitboard.encode(random_grid(rng))
        assert bitboard.transpose(bitboard.transpose(board)) == board


# ---------------------------------------------------------------------------
# The golden cases, unchanged, applied to the bitboard.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row, expected, score", ROW_CASES)
def test_row_cases_hold_moving_left(row, expected, score):
    board = bitboard.encode(row_as_board(row))
    moved, gained, _ = bitboard.move(board, "left")
    assert bitboard.decode(moved) == row_as_board(expected)
    assert gained == score


@pytest.mark.parametrize("direction, expected, score", GOLDEN_MOVES)
def test_golden_board_all_four_directions(direction, expected, score):
    moved, gained, changed = bitboard.move(bitboard.encode(GOLDEN), direction)
    assert bitboard.decode(moved) == expected
    assert gained == score
    assert changed is True


def test_a_move_that_changes_nothing_reports_changed_false():
    board = bitboard.encode(DEAD)
    moved, gained, changed = bitboard.move(board, "left")
    assert changed is False
    assert gained == 0
    assert moved == board


def test_sliding_without_merging_still_counts_as_a_change():
    board = bitboard.encode([[0, 0, 0, 2], [0] * 4, [0] * 4, [0] * 4])
    _, gained, changed = bitboard.move(board, "left")
    assert changed is True
    assert gained == 0


def test_legal_moves_lists_only_directions_that_change_the_board():
    assert sorted(bitboard.legal_moves(bitboard.encode(WEDGED))) == WEDGED_LEGAL_MOVES


def test_a_full_board_with_no_equal_neighbours_is_game_over():
    assert bitboard.is_game_over(bitboard.encode(DEAD)) is True


def test_a_full_board_with_an_equal_neighbour_is_not_game_over():
    assert bitboard.is_game_over(bitboard.encode(ALIVE)) is False


def test_a_board_with_an_empty_cell_is_not_game_over():
    assert bitboard.is_game_over(bitboard.encode(WEDGED)) is False


def test_an_unknown_direction_is_a_value_error():
    with pytest.raises(ValueError):
        bitboard.move(bitboard.encode(GOLDEN), "sideways")


# ---------------------------------------------------------------------------
# Agreement with the oracle. The 100k-game differential test is TASK-08; this
# is the bounded version that keeps plumbing bugs out of the branch.
# ---------------------------------------------------------------------------


def test_moves_agree_with_the_naive_engine_on_random_boards():
    rng = random.Random(1234)
    for _ in range(3000):
        grid = random_grid(rng)
        board = bitboard.encode(grid)
        for direction in DIRECTIONS:
            fast_board, fast_score, fast_changed = bitboard.move(board, direction)
            slow_grid, slow_score, slow_changed = naive.move(grid, direction)
            assert bitboard.decode(fast_board) == slow_grid, (direction, grid)
            assert fast_score == slow_score, (direction, grid)
            assert fast_changed == slow_changed, (direction, grid)


def test_legal_moves_agree_with_the_naive_engine_on_random_boards():
    rng = random.Random(5678)
    for _ in range(3000):
        grid = random_grid(rng)
        assert sorted(bitboard.legal_moves(bitboard.encode(grid))) == sorted(
            naive.legal_moves(grid)
        )


def test_spawn_consumes_the_rng_exactly_as_the_naive_engine_does():
    """TASK-08 replays both engines from one seed; a different draw order breaks it."""
    fast_rng = random.Random(99)
    slow_rng = random.Random(99)
    grid = [[0] * 4 for _ in range(4)]
    board = bitboard.encode(grid)
    for _ in range(16):
        board = bitboard.spawn(board, fast_rng)
        grid = naive.spawn(grid, slow_rng)
        assert bitboard.decode(board) == grid
    assert fast_rng.getstate() == slow_rng.getstate()


def test_new_game_matches_the_naive_engine_from_the_same_seed():
    assert bitboard.decode(bitboard.new_game(random.Random(7))) == naive.new_game(
        random.Random(7)
    )


def test_empty_cells_matches_a_cell_by_cell_scan():
    """Row-major, nibble 8 (tile 256) has only its top bit set, so it tests the `>> 3`."""
    rng = random.Random(3)
    for _ in range(5000):
        grid = [[rng.choice((0, 0, 2, 256, 32768)) for _ in range(4)] for _ in range(4)]
        expected = [4 * r + c for r in range(4) for c in range(4) if grid[r][c] == 0]
        assert bitboard.empty_cells(bitboard.encode(grid)) == expected
    assert bitboard.empty_cells(0) == list(range(16))
    assert bitboard.empty_cells(bitboard.encode(DEAD)) == []


def test_spawn_on_a_full_board_is_an_error():
    with pytest.raises(ValueError):
        bitboard.spawn(bitboard.encode(DEAD), random.Random(0))


# ---------------------------------------------------------------------------
# ADR-013: the raw-index trap. Every direction must check.
# ---------------------------------------------------------------------------


def test_the_state_one_nibble_from_overflow_still_works():
    board = bitboard.encode(ONE_NIBBLE_FROM_OVERFLOW)
    moved, gained, changed = bitboard.move(board, "left")
    assert bitboard.decode(moved) == ONE_NIBBLE_FROM_OVERFLOW_AFTER_LEFT
    assert gained == ONE_NIBBLE_FROM_OVERFLOW_SCORE
    assert changed is True


def test_the_merge_out_of_that_state_raises_rather_than_returning_a_number():
    """The whole point: a wrong board is never returned, an exception is raised."""
    board, _, _ = bitboard.move(bitboard.encode(ONE_NIBBLE_FROM_OVERFLOW), "left")
    with pytest.raises(tables.NibbleOverflow):
        bitboard.move(board, "left")


@pytest.mark.parametrize("direction", DIRECTIONS)
def test_every_direction_checks_for_overflow(direction):
    """A check on the left path only would leave three directions corrupting."""
    board = bitboard.encode(OVERFLOW_BOARDS[direction])
    with pytest.raises(tables.NibbleOverflow):
        bitboard.move(board, direction)


@pytest.mark.parametrize("direction", DIRECTIONS)
def test_legal_moves_does_not_swallow_an_overflow(direction):
    """legal_moves calls move on every direction; it must not hide the raise."""
    board = bitboard.encode(OVERFLOW_BOARDS[direction])
    with pytest.raises(tables.NibbleOverflow):
        bitboard.legal_moves(board)


def test_no_overflow_sentinel_can_reach_a_returned_board():
    """If the check were missing, 0xFFFF would appear as a row of four 32768s."""
    board = bitboard.encode(ONE_NIBBLE_FROM_OVERFLOW_AFTER_LEFT)
    try:
        moved, _, _ = bitboard.move(board, "left")
    except tables.NibbleOverflow:
        return
    pytest.fail(f"returned {moved:#018x} instead of raising")
