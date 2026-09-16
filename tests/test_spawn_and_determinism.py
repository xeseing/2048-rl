"""Spawn distribution, seeded determinism, and the score invariant (SPECS section 3).

Every check in this file is written to take the implementation under test as an
argument, so each one can be pointed at a deliberately wrong spawn or move and
shown to reject it. The `test_rejects_*` tests below are those demonstrations,
kept permanently: a statistical check nobody has ever seen fail is a check whose
threshold might be asleep.
"""

import json
import random

import pytest

from game2048 import naive

SIZE = naive.SIZE
CELLS = SIZE * SIZE

# Upper-tail chi-square critical values at alpha = 0.01. Comparing the statistic
# against these is exactly "p > 0.01", without needing an incomplete gamma
# function in a test file. df = (number of candidate cells) - 1.
CHI2_CRITICAL_ALPHA_001 = {4: 13.277, 15: 30.578}

EMPTY_BOARD = [[0] * SIZE for _ in range(SIZE)]

# Five empty cells: (2,2) (2,3) (3,0) (3,1) (3,2).
PARTIAL_BOARD = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 0, 0],
    [0, 0, 0, 2],
]

# The real checks use the 100,000 spawns SPECS section 3 asks for. The
# demonstrations that a wrong implementation is rejected use fewer, because
# rejecting P(4)=0.5 or a constant cell does not need 100,000 samples and the
# suite has to stay fast.
SPAWNS = 100_000
SPAWNS_FOR_REJECTION = 20_000


# ---------------------------------------------------------------------------
# Deliberately wrong implementations. These exist only to be rejected.
# ---------------------------------------------------------------------------


def spawn_biased_value(board, rng):
    """Wrong: P(4) = 0.5 instead of 0.1. Cell choice is correct."""
    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    row, column = rng.choice(empty)
    spawned = [existing[:] for existing in board]
    spawned[row][column] = 4 if rng.random() < 0.5 else 2
    return spawned


def spawn_always_first_empty_cell(board, rng):
    """Wrong: always the first empty cell. Value distribution is correct."""
    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    row, column = empty[0]
    spawned = [existing[:] for existing in board]
    spawned[row][column] = 4 if rng.random() < naive.PROBABILITY_OF_FOUR else 2
    return spawned


def spawn_ignoring_the_seed(board, rng):
    """Wrong: draws from the global RNG, so a seed reproduces nothing."""
    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    row, column = random.choice(empty)
    spawned = [existing[:] for existing in board]
    spawned[row][column] = 4 if random.random() < naive.PROBABILITY_OF_FOUR else 2
    return spawned


def move_scoring_the_pre_merge_value(board, direction):
    """Wrong: a merge scores the value of one input tile, not the result.

    The classic off-by-a-factor-of-two in 2048 scoring. Boards are correct, so
    only the score invariant can catch it.
    """
    moved, score, changed = naive.move(board, direction)
    return moved, score // 2, changed


# ---------------------------------------------------------------------------
# Measurement helpers.
# ---------------------------------------------------------------------------


def spawned_cell(before, after):
    """The (row, column) that `after` filled in and `before` had empty."""
    for r in range(SIZE):
        for c in range(SIZE):
            if before[r][c] != after[r][c]:
                return r, c
    raise AssertionError("spawn changed nothing")


def four_rate(spawn_fn, board, trials, rng):
    """Fraction of spawns that produced a 4."""
    fours = 0
    for _ in range(trials):
        spawned = spawn_fn(board, rng)
        row, column = spawned_cell(board, spawned)
        fours += spawned[row][column] == 4
    return fours / trials


def cell_counts(spawn_fn, board, trials, rng):
    """How many times each empty cell was chosen."""
    empty = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    counts = dict.fromkeys(empty, 0)
    for _ in range(trials):
        counts[spawned_cell(board, spawn_fn(board, rng))] += 1
    return list(counts.values())


def chi_square_uniform(counts):
    """Pearson's chi-square against a uniform expectation over len(counts) cells."""
    expected = sum(counts) / len(counts)
    return sum((count - expected) ** 2 / expected for count in counts)


def merge_weight(value):
    """w(v) = v * (log2(v) - 1): the score of building v out of 2s by merging.

    For a power of two, log2(v) is v.bit_length() - 1, so w(2) = 0, w(4) = 4,
    w(8) = 16, w(16) = 48. A merge of two v's into 2v raises the board's total
    weight by exactly 2v, which is what that merge adds to the score.
    """
    return value * (value.bit_length() - 2)


def play_seeded_game(seed, spawn_fn=naive.spawn, move_fn=naive.move):
    """Play one game with a seeded random policy.

    Returns (final_board, score, spawned_values, transcript). A single RNG drives
    both the spawns and the move choice, so the whole game is reproducible from
    `seed` alone.
    """
    rng = random.Random(seed)
    board = [row[:] for row in EMPTY_BOARD]
    spawned_values = []

    def spawn_and_record(current):
        nxt = spawn_fn(current, rng)
        row, column = spawned_cell(current, nxt)
        spawned_values.append(nxt[row][column])
        return nxt

    board = spawn_and_record(spawn_and_record(board))

    score = 0
    transcript = []
    while not naive.is_game_over(board):
        direction = rng.choice(naive.legal_moves(board))
        afterstate, gained, changed = move_fn(board, direction)
        assert changed, "legal_moves offered a move that changes nothing"
        score += gained
        transcript.append([direction, gained, afterstate])
        board = spawn_and_record(afterstate)
        transcript.append([None, 0, board])

    return board, score, spawned_values, transcript


def transcript_bytes(seed, spawn_fn=naive.spawn):
    """The whole game serialised, so two runs can be compared byte for byte."""
    board, score, spawned_values, transcript = play_seeded_game(seed, spawn_fn)
    return json.dumps(
        {
            "final_board": board,
            "score": score,
            "spawned": spawned_values,
            "transcript": transcript,
        },
        sort_keys=True,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Spawn value distribution: 2 at p=0.9, 4 at p=0.1.
# ---------------------------------------------------------------------------


def test_spawn_produces_a_four_about_one_time_in_ten():
    rate = four_rate(naive.spawn, EMPTY_BOARD, SPAWNS, random.Random(0))
    assert 0.09 <= rate <= 0.11, f"P(4) = {rate}"


def test_the_four_rate_check_rejects_a_fair_coin_spawn():
    """P(4) = 0.5 must fail the band the real test passes."""
    rate = four_rate(
        spawn_biased_value, EMPTY_BOARD, SPAWNS_FOR_REJECTION, random.Random(0)
    )
    assert not (0.09 <= rate <= 0.11), (
        f"biased spawn slipped through with P(4) = {rate}"
    )


# ---------------------------------------------------------------------------
# Spawn cell distribution: uniform over the empty cells.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "board, degrees_of_freedom",
    [(EMPTY_BOARD, 15), (PARTIAL_BOARD, 4)],
    ids=["empty-board", "five-empty-cells"],
)
def test_spawn_picks_empty_cells_uniformly(board, degrees_of_freedom):
    counts = cell_counts(naive.spawn, board, SPAWNS, random.Random(0))
    assert len(counts) == degrees_of_freedom + 1
    statistic = chi_square_uniform(counts)
    assert statistic < CHI2_CRITICAL_ALPHA_001[degrees_of_freedom], (
        f"chi-square {statistic:.2f} exceeds the p=0.01 critical value; counts={counts}"
    )


def test_the_chi_square_check_rejects_a_spawn_that_always_picks_the_first_cell():
    """A constant cell choice must blow past the same critical value."""
    counts = cell_counts(
        spawn_always_first_empty_cell,
        EMPTY_BOARD,
        SPAWNS_FOR_REJECTION,
        random.Random(0),
    )
    statistic = chi_square_uniform(counts)
    assert statistic > CHI2_CRITICAL_ALPHA_001[15], (
        f"biased cell choice slipped through with chi-square {statistic:.2f}"
    )


def test_spawn_never_lands_on_an_occupied_cell():
    rng = random.Random(0)
    for _ in range(1000):
        spawned = naive.spawn(PARTIAL_BOARD, rng)
        row, column = spawned_cell(PARTIAL_BOARD, spawned)
        assert PARTIAL_BOARD[row][column] == 0


# ---------------------------------------------------------------------------
# Determinism: the same seed replays byte for byte.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 20_240_915])
def test_the_same_seed_produces_a_byte_identical_transcript_twice(seed):
    assert transcript_bytes(seed) == transcript_bytes(seed)


def test_different_seeds_produce_different_transcripts():
    """Otherwise the determinism test would pass on a constant."""
    assert transcript_bytes(0) != transcript_bytes(1)


def test_the_determinism_check_rejects_a_spawn_that_ignores_the_seed():
    first = transcript_bytes(0, spawn_fn=spawn_ignoring_the_seed)
    second = transcript_bytes(0, spawn_fn=spawn_ignoring_the_seed)
    assert first != second, "a spawn drawing from the global RNG replayed identically"


def test_a_seeded_spawn_sequence_replays_exactly():
    def sequence():
        rng = random.Random(1234)
        board = [row[:] for row in EMPTY_BOARD]
        drawn = []
        for _ in range(CELLS):
            board = naive.spawn(board, rng)
            drawn.append([row[:] for row in board])
        return drawn

    assert sequence() == sequence()


# ---------------------------------------------------------------------------
# Score invariant.
#
# SPECS section 3 originally stated this as "score == sum(tiles) - sum(spawned
# values)", which is identically zero: a merge turns a + a into 2a and so leaves
# the board's tile sum untouched, making sum(tiles) always equal sum(spawned).
# The invariant that actually holds weights each tile by w(v) = v*(log2(v)-1).
# See ADR-010; SPECS section 3 has been corrected to match.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 20_240_915])
def test_score_equals_the_boards_merge_weight_minus_the_spawned_weight(seed):
    board, score, spawned_values, _ = play_seeded_game(seed)
    on_board = sum(merge_weight(v) for row in board for v in row if v)
    from_spawns = sum(merge_weight(v) for v in spawned_values)
    assert score == on_board - from_spawns


def test_the_score_invariant_rejects_a_move_that_scores_the_pre_merge_value():
    board, score, spawned_values, _ = play_seeded_game(
        0, move_fn=move_scoring_the_pre_merge_value
    )
    on_board = sum(merge_weight(v) for row in board for v in row if v)
    from_spawns = sum(merge_weight(v) for v in spawned_values)
    assert score != on_board - from_spawns, "halved scores satisfied the invariant"


def test_the_tile_sum_is_conserved_by_moves_which_is_why_the_naive_form_is_zero():
    """Pins the reason SPECS' original wording could not have held."""
    board, _, spawned_values, _ = play_seeded_game(0)
    assert sum(v for row in board for v in row) == sum(spawned_values)
