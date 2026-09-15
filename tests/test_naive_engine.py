"""Golden tests for the naive engine — the permanent oracle.

Every number in this file is hand-computed from the rules in SPECS section 1, not
copied from the implementation's output. That is the whole point: if these tests
are ever derived from the code they are meant to check, the oracle stops being an
oracle and every later differential test becomes theatre.
"""

import random

import pytest

from game2048 import naive

# A board chosen so that all four directions do something different, and so that
# every row and column contains at least one merge.
GOLDEN = [
    [2, 2, 4, 0],
    [0, 4, 4, 4],
    [2, 0, 2, 2],
    [8, 8, 0, 0],
]


# --------------------------------------------------------------------------
# SPECS section 7, trap 1: merges resolve from the edge being moved toward.
# --------------------------------------------------------------------------


def test_trap1_three_in_a_row_merges_the_pair_nearest_the_moved_toward_edge():
    """[2,2,2,0] left is [4,2,0,0], never [2,4,0,0]."""
    assert naive.slide_row_left([2, 2, 2, 0]) == ([4, 2, 0, 0], 4)


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
    assert naive.slide_row_left([4, 4, 4, 4]) == ([8, 8, 0, 0], 16)


def test_trap2_cascade_is_not_allowed():
    """[2,2,4,0] left is [4,4,0,0]: the new 4 does not eat the existing 4."""
    assert naive.slide_row_left([2, 2, 4, 0]) == ([4, 4, 0, 0], 4)


# --------------------------------------------------------------------------
# The two remaining row cases named in SPECS section 1.
# --------------------------------------------------------------------------


def test_four_equal_tiles_make_two_independent_pairs():
    """[2,2,2,2] left is [4,4,0,0]."""
    assert naive.slide_row_left([2, 2, 2, 2]) == ([4, 4, 0, 0], 8)


def test_two_distinct_pairs_merge_independently():
    """[4,4,2,2] left is [8,4,0,0]."""
    assert naive.slide_row_left([4, 4, 2, 2]) == ([8, 4, 0, 0], 12)


@pytest.mark.parametrize(
    "row, expected, score",
    [
        ([0, 0, 0, 0], [0, 0, 0, 0], 0),
        ([2, 0, 0, 0], [2, 0, 0, 0], 0),
        ([0, 0, 0, 2], [2, 0, 0, 0], 0),
        ([2, 4, 8, 16], [2, 4, 8, 16], 0),
        ([0, 2, 0, 2], [4, 0, 0, 0], 4),
        ([2, 0, 0, 2], [4, 0, 0, 0], 4),
        ([4, 2, 2, 0], [4, 4, 0, 0], 4),
        ([2, 2, 0, 4], [4, 4, 0, 0], 4),
    ],
)
def test_row_slides(row, expected, score):
    assert naive.slide_row_left(row) == (expected, score)


# --------------------------------------------------------------------------
# Golden boards: all four directions on the same start position.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "direction, expected, score",
    [
        (
            "left",
            [[4, 4, 0, 0], [8, 4, 0, 0], [4, 2, 0, 0], [16, 0, 0, 0]],
            32,
        ),
        (
            "right",
            [[0, 0, 4, 4], [0, 0, 4, 8], [0, 0, 2, 4], [0, 0, 0, 16]],
            32,
        ),
        (
            "up",
            [[4, 2, 8, 4], [8, 4, 2, 2], [0, 8, 0, 0], [0, 0, 0, 0]],
            12,
        ),
        (
            "down",
            [[0, 0, 0, 0], [0, 2, 0, 0], [4, 4, 8, 4], [8, 8, 2, 2]],
            12,
        ),
    ],
)
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
    packed = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 8]]
    moved, gained, changed = naive.move(packed, "left")
    assert changed is False
    assert gained == 0
    assert moved == packed


def test_sliding_without_merging_still_counts_as_a_change():
    board = [[0, 0, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    _, gained, changed = naive.move(board, "left")
    assert changed is True
    assert gained == 0


def test_legal_moves_lists_only_directions_that_change_the_board():
    board = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 0]]
    assert sorted(naive.legal_moves(board)) == ["down", "right"]


# --------------------------------------------------------------------------
# Game over.
# --------------------------------------------------------------------------


def test_a_full_board_with_no_equal_neighbours_is_game_over():
    dead = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 8]]
    assert naive.is_game_over(dead) is True


def test_a_full_board_with_an_equal_neighbour_is_not_game_over():
    alive = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 4]]
    assert naive.is_game_over(alive) is False


def test_a_board_with_an_empty_cell_is_not_game_over():
    board = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 0]]
    assert naive.is_game_over(board) is False


# --------------------------------------------------------------------------
# Spawn. The distribution itself is TASK-03; this only pins the mechanics.
# --------------------------------------------------------------------------


def test_spawn_fills_exactly_one_empty_cell_with_a_2_or_a_4():
    board = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 0]]
    spawned = naive.spawn(board, random.Random(0))
    assert spawned[3][3] in (2, 4)
    assert [row[:3] for row in spawned] == [row[:3] for row in board]


def test_spawn_does_not_mutate_the_board_it_was_given():
    board = [[0] * 4 for _ in range(4)]
    before = [row[:] for row in board]
    naive.spawn(board, random.Random(0))
    assert board == before


def test_spawn_on_a_full_board_is_an_error():
    full = [[2, 4, 8, 16], [4, 8, 16, 2], [8, 16, 2, 4], [16, 2, 4, 8]]
    with pytest.raises(ValueError):
        naive.spawn(full, random.Random(0))


def test_new_game_starts_with_exactly_two_tiles():
    board = naive.new_game(random.Random(7))
    values = [v for row in board for v in row if v != 0]
    assert len(values) == 2
    assert all(v in (2, 4) for v in values)
