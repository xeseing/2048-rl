"""The differential harness itself.

A harness that always says "OK" is worse than no harness, because it is trusted.
So most of this file is about making the harness fail: a subtly broken bitboard
must be caught, and `main()` must return 1 when it is.

The last test documents the limitation rather than hiding it — a bug both
engines share is invisible here, by construction.
"""

import random

import pytest

from game2048 import bitboard, naive
from game2048.bench import differential


def rotate_rows_instead_of_reversing(board):
    """A subtle off-by-one in the row reversal.

    Reversing [a b c d] gives [d c b a]; this gives [d a b c]. Boards stay
    well-formed and `left` and `up` are untouched, so only `right` and `down`
    quietly disagree — exactly the kind of bug the differential test exists for.
    """
    result = 0
    for shift in bitboard.ROW_SHIFTS:
        row = (board >> shift) & bitboard.ROW_MASK
        rotated = ((row & 0xF) << 12) | (row >> 4)
        result |= rotated << shift
    return result


# ---------------------------------------------------------------------------
# The harness agrees with itself on the real engines.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 1234, 20_240_916])
def test_a_single_game_agrees(seed):
    assert differential.compare_game(seed) is None


def test_a_short_run_agrees():
    assert differential.run(games=50, seed=1234) is None


def test_main_returns_zero_when_the_engines_agree(capsys):
    assert differential.main(["--games", "20", "--seed", "1234"]) == 0
    assert "0 divergences" in capsys.readouterr().out


def test_the_same_seed_gives_the_same_game_twice():
    """Otherwise a reported seed would not reproduce the failure."""
    assert differential.compare_game(7) is None
    assert differential.compare_game(7) is None


# ---------------------------------------------------------------------------
# A broken bitboard must be caught, and must make the exit code 1.
# ---------------------------------------------------------------------------


def test_a_subtly_broken_reverse_is_caught(monkeypatch):
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    divergence = differential.run(games=20, seed=1234)
    assert divergence is not None


def test_main_returns_one_when_the_engines_disagree(monkeypatch, capsys):
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    assert differential.main(["--games", "20", "--seed", "1234"]) == 1
    assert "DIVERGENCE" in capsys.readouterr().err


def test_a_wrong_score_is_caught(monkeypatch):
    real_move = bitboard.move

    def move_scoring_one_too_many(board, direction):
        moved, score, changed = real_move(board, direction)
        return moved, score + 1 if changed else score, changed

    monkeypatch.setattr(bitboard, "move", move_scoring_one_too_many)
    assert differential.run(games=5, seed=1234) is not None


def test_a_wrong_spawn_is_caught(monkeypatch):
    """Same cell, wrong value: boards diverge without the RNG drifting."""
    real_spawn = bitboard.spawn

    def spawn_one_exponent_too_high(board, rng):
        spawned = real_spawn(board, rng)
        new_nibble = spawned ^ board  # the cell that was just filled, in place
        return board | (new_nibble << 1)  # exponent 1 -> 2, i.e. a 2 becomes a 4

    monkeypatch.setattr(bitboard, "spawn", spawn_one_exponent_too_high)
    assert differential.run(games=5, seed=1234) is not None


def test_a_swallowed_divergence_would_be_visible_as_exit_zero(monkeypatch):
    """The always-green failure mode, stated as a test so it cannot creep back."""
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    assert differential.main(["--games", "20", "--seed", "1234"]) != 0


# ---------------------------------------------------------------------------
# The report has to be enough to reproduce the failure.
# ---------------------------------------------------------------------------


def test_the_report_carries_everything_needed_to_reproduce(monkeypatch):
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    divergence = differential.run(games=20, seed=1234)
    assert divergence is not None

    report = divergence.report()
    assert "DIVERGENCE" in report
    assert f"seed         : {divergence.seed}" in report
    assert f"move number  : {divergence.move_index}" in report
    assert divergence.direction in report
    assert "naive says" in report
    assert "bitboard says" in report
    assert "score naive" in report
    assert "score fast" in report
    assert f"--games 1 --seed {divergence.seed}" in report, (
        "the report must contain a one-line repro"
    )


def test_the_repro_command_in_the_report_actually_reproduces(monkeypatch):
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    divergence = differential.run(games=20, seed=1234)
    assert divergence is not None
    again = differential.compare_game(divergence.seed)
    assert again is not None
    assert again.seed == divergence.seed
    assert again.move_index == divergence.move_index
    assert again.what == divergence.what


def test_both_boards_appear_in_the_report(monkeypatch):
    monkeypatch.setattr(bitboard, "_reverse_rows", rotate_rows_instead_of_reversing)
    divergence = differential.run(games=20, seed=1234)
    report = divergence.report()
    assert "disagreement, naive:" in report
    assert "disagreement, bitboard:" in report


# ---------------------------------------------------------------------------
# The limitation, stated out loud.
# ---------------------------------------------------------------------------


def test_a_bug_shared_by_both_engines_is_invisible_here(monkeypatch):
    """Differential testing catches divergences, not shared bugs.

    `tables.py` is built by calling `naive.slide_row_left`, so the bitboard
    engine inherits the oracle's merge rule on purpose (ADR-013). A wrong merge
    rule is therefore wrong identically on both sides and passes here. The
    golden tests, whose values are hand-computed from SPECS and never captured
    from either implementation, are what catch that. This test exists so the
    gap is documented rather than assumed.
    """
    real_move_naive = naive.move
    real_move_fast = bitboard.move

    def naive_no_score(grid, direction):
        moved, score, changed = real_move_naive(grid, direction)
        return moved, score // 2, changed

    def fast_no_score(board, direction):
        moved, score, changed = real_move_fast(board, direction)
        return moved, score // 2, changed

    monkeypatch.setattr(naive, "move", naive_no_score)
    monkeypatch.setattr(bitboard, "move", fast_no_score)

    assert differential.run(games=5, seed=1234) is None, (
        "a shared bug should pass the differential test — if this ever fails, "
        "the harness has started doing something it does not claim to do"
    )


# ---------------------------------------------------------------------------
# CLI surface.
# ---------------------------------------------------------------------------


def test_the_parser_defaults_to_the_ci_fast_lane():
    args = differential.build_parser().parse_args([])
    assert args.games == 5000
    assert args.seed == 1234


def test_the_parser_accepts_games_and_seed():
    args = differential.build_parser().parse_args(["--games", "100000", "--seed", "7"])
    assert args.games == 100_000
    assert args.seed == 7


def test_seeds_advance_one_per_game(monkeypatch):
    seen = []
    monkeypatch.setattr(differential, "compare_game", lambda seed: seen.append(seed))
    differential.run(games=5, seed=100)
    assert seen == [100, 101, 102, 103, 104]


def test_spawn_streams_stay_in_lockstep():
    """The property the whole harness rests on (verified again at TASK-07)."""
    naive_rng = random.Random(42)
    fast_rng = random.Random(42)
    grid = naive.new_game(naive_rng)
    board = bitboard.new_game(fast_rng)
    assert bitboard.decode(board) == grid
    assert naive_rng.getstate() == fast_rng.getstate()
