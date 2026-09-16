"""Golden tests for the naive engine — the permanent oracle.

Every number in this file is hand-computed from the rules in SPECS section 1, not
copied from the implementation's output. That is the whole point: if these tests
are ever derived from the code they are meant to check, the oracle stops being an
oracle and every later differential test becomes theatre.
"""

import random

import pytest
from golden_cases import (
    DEAD,
    FOUR_EQUAL_TILES,
    GOLDEN,
    GOLDEN_MOVES,
    ROW_CASES,
    TRAP_EDGE_ORDER,
    TRAP_MERGE_ONCE,
    TRAP_NO_CASCADE,
    TWO_DISTINCT_PAIRS,
    WEDGED,
    WEDGED_LEGAL_MOVES,
)

from game2048 import naive

# --------------------------------------------------------------------------
# SPECS section 7, trap 1: merges resolve from the edge being moved toward.
# --------------------------------------------------------------------------


def test_trap1_three_in_a_row_merges_the_pair_nearest_the_moved_toward_edge():
    """[2,2,2,0] left is [4,2,0,0], never [2,4,0,0]."""
    row, expected, score = TRAP_EDGE_ORDER
    assert naive.slide_row_left(row) == (expected, score)


def test_trap1_holds_moving_right_too():
    """Moving right, the pair nearest the right edge is the one that merges."""
    board = [[0, 2, 2, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    moved, _, _ = naive.move(board, "right")
    assert moved[0] == [0, 0, 2, 4]


# --------------------------------------------------------------------------
# SPECS section 7, trap 2: a tile produced by a merge cannot merge again.
# --------------------------------------------------------------------------


def test_trap2_a_merged_tile_cannot_merge_again_in_the_same_move():
    """[4,4,4,4] left is [8,8,0,0], never [16,0,0,0]."""
    row, expected, score = TRAP_MERGE_ONCE
    assert naive.slide_row_left(row) == (expected, score)


def test_trap2_cascade_is_not_allowed():
    """[2,2,4,0] left is [4,4,0,0]: the new 4 does not eat the existing 4."""
    row, expected, score = TRAP_NO_CASCADE
    assert naive.slide_row_left(row) == (expected, score)


# --------------------------------------------------------------------------
# The two remaining row cases named in SPECS section 1.
# --------------------------------------------------------------------------


def test_four_equal_tiles_make_two_independent_pairs():
    """[2,2,2,2] left is [4,4,0,0]."""
    row, expected, score = FOUR_EQUAL_TILES
    assert naive.slide_row_left(row) == (expected, score)


def test_two_distinct_pairs_merge_independently():
    """[4,4,2,2] left is [8,4,0,0]."""
    row, expected, score = TWO_DISTINCT_PAIRS
    assert naive.slide_row_left(row) == (expected, score)


@pytest.mark.parametrize("row, expected, score", ROW_CASES)
def test_row_slides(row, expected, score):
    assert naive.slide_row_left(row) == (expected, score)


# --------------------------------------------------------------------------
# Golden boards: all four directions on the same start position.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("direction, expected, score", GOLDEN_MOVES)
def test_golden_board_all_four_directions(direction, expected, score):
    moved, gained, changed = naive.move(GOLDEN, direction)
    assert moved == expected
    assert gained == score
    assert changed is True


def test_move_does_not_mutate_the_board_it_was_given():
    before = [row[:] for row in GOLDEN]
    naive.move(GOLDEN, "left")
    assert GOLDEN == before


# --------------------------------------------------------------------------
# Legality: a move is legal only if it changes the board.
# --------------------------------------------------------------------------


def test_a_move_that_changes_nothing_reports_changed_false():
    moved, gained, changed = naive.move(DEAD, "left")
    assert changed is False
    assert gained == 0
    assert moved == DEAD


def test_sliding_without_merging_still_counts_as_a_change():
    board = [[0, 0, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    _, gained, changed = naive.move(board, "left")
    assert changed is True
    assert gained == 0


def test_legal_moves_lists_only_directions_that_change_the_board():
    assert sorted(naive.legal_moves(WEDGED)) == WEDGED_LEGAL_MOVES


# --------------------------------------------------------------------------
# Game over.
# --------------------------------------------------------------------------


def test_a_full_board_with_no_equal_neighbours_is_game_over():
    assert naive.is_game_over(DEAD) is True


def test_a_full_board_with_an_equal_neighbour_is_not_game_over():
    alive = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 4]]
    assert naive.is_game_over(alive) is False


def test_a_board_with_an_empty_cell_is_not_game_over():
    assert naive.is_game_over(WEDGED) is False


# --------------------------------------------------------------------------
# Spawn. The distribution itself is TASK-03; this only pins the mechanics.
# --------------------------------------------------------------------------


def test_spawn_fills_exactly_one_empty_cell_with_a_2_or_a_4():
    spawned = naive.spawn(WEDGED, random.Random(0))
    assert spawned[3][3] in (2, 4)
    assert [row[:3] for row in spawned] == [row[:3] for row in WEDGED]


def test_spawn_does_not_mutate_the_board_it_was_given():
    board = [[0] * 4 for _ in range(4)]
    before = [row[:] for row in board]
    naive.spawn(board, random.Random(0))
    assert board == before


def test_spawn_on_a_full_board_is_an_error():
    with pytest.raises(ValueError):
        naive.spawn(DEAD, random.Random(0))


def test_new_game_starts_with_exactly_two_tiles():
    board = naive.new_game(random.Random(7))
    values = [v for row in board for v in row if v != 0]
    assert len(values) == 2
    assert all(v in (2, 4) for v in values)
