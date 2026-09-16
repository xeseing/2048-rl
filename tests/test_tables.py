"""The 65536-entry row tables (SPECS section 2.2).

The headline test walks **all 65536 rows**, not a sample, and checks each entry
against `naive.slide_row_left`. That exhaustiveness is what makes TASK-08's
differential test meaningful: once the tables are provably the naive engine
memoized, any divergence the bitboard engine shows later is in the bitboard
plumbing — transposes, reversals, packing — and not in the merge rule.

There is also a test that the build *calls* the oracle rather than agreeing with
it. A hand-written table build that happened to match would defeat the entire
point: if the naive engine has a subtle bug, the tables must inherit it, or the
differential test compares two independent implementations of a guess.
"""

import pytest

from game2048 import naive, tables

ALL_ROWS = range(1 << 16)


def naive_row_result(packed):
    """What the oracle says this row becomes, in tile values."""
    return naive.slide_row_left(tables.decode_row(packed))


# ---------------------------------------------------------------------------
# Nibble encoding: 4 nibbles of log2(tile), cell 0 in the highest nibble.
# ---------------------------------------------------------------------------


def test_a_row_packs_cell_zero_into_the_highest_nibble():
    assert tables.encode_row([2, 4, 8, 16]) == 0x1234


def test_decoding_is_the_inverse_of_encoding():
    assert tables.decode_row(0x1234) == [2, 4, 8, 16]


def test_an_empty_row_is_zero():
    assert tables.encode_row([0, 0, 0, 0]) == 0
    assert tables.decode_row(0) == [0, 0, 0, 0]


def test_the_ceiling_tile_fits_in_a_nibble():
    assert tables.encode_row([32768, 0, 0, 0]) == 0xF000
    assert tables.decode_row(0xF000) == [32768, 0, 0, 0]


def test_encode_decode_round_trips_for_every_row():
    for packed in ALL_ROWS:
        assert tables.encode_row(tables.decode_row(packed)) == packed


# ---------------------------------------------------------------------------
# SPECS trap 4: nibble overflow asserts, it does not wrap.
# ---------------------------------------------------------------------------


def test_a_tile_above_the_ceiling_raises_rather_than_wrapping():
    """65536 needs nibble 16. Wrapping would silently store it as an empty cell."""
    with pytest.raises(tables.NibbleOverflow):
        tables.encode_row([65536, 0, 0, 0])


def test_a_non_power_of_two_tile_is_rejected():
    with pytest.raises(ValueError):
        tables.encode_row([3, 0, 0, 0])


def test_merging_the_two_biggest_tiles_is_an_overflow_row():
    """32768 + 32768 = 65536, which no nibble can hold."""
    packed = tables.encode_row([32768, 32768, 0, 0])
    assert tables.is_overflow(packed)
    with pytest.raises(tables.NibbleOverflow):
        tables.row_left(packed)
    with pytest.raises(tables.NibbleOverflow):
        tables.row_score(packed)


def test_the_last_legal_merge_is_one_nibble_below_the_ceiling():
    """16384 + 16384 = 32768 is fine; one doubling later is not.

    This is the boundary the bitboard engine will walk up to at TASK-07: the
    state one nibble away from overflow must still work, and the merge out of
    it must not.
    """
    safe = tables.encode_row([16384, 16384, 0, 0])
    assert not tables.is_overflow(safe)
    assert tables.decode_row(tables.row_left(safe)) == [32768, 0, 0, 0]
    assert tables.row_score(safe) == 32768

    over = tables.row_left(safe)  # the row we just produced, slid again...
    assert tables.decode_row(over) == [32768, 0, 0, 0]
    assert not tables.is_overflow(over), "a lone 32768 is legal; only merging it is not"

    doomed = tables.encode_row([32768, 32768, 0, 0])
    assert tables.is_overflow(doomed)
    with pytest.raises(tables.NibbleOverflow):
        tables.row_left(doomed)


def test_overflow_rows_are_exactly_those_the_oracle_pushes_past_the_ceiling():
    from_tables = {p for p in ALL_ROWS if tables.is_overflow(p)}
    from_oracle = {p for p in ALL_ROWS if max(naive_row_result(p)[0]) > 32768}
    assert from_tables == from_oracle
    assert from_tables, "no overflow rows found — the ceiling test is vacuous"


def test_the_sentinels_are_the_documented_values():
    """Pinned, because the bitboard engine will compare against them by value."""
    assert tables.OVERFLOW_ROW == 0xFFFF
    assert tables.OVERFLOW_SCORE < 0

    doomed = tables.encode_row([32768, 32768, 0, 0])
    assert tables.ROW_LEFT[doomed] == tables.OVERFLOW_ROW
    assert tables.ROW_SCORE[doomed] == tables.OVERFLOW_SCORE


def test_no_legitimate_entry_collides_with_either_sentinel():
    """The sentinels must be unreachable by real play, or they are ambiguous.

    OVERFLOW_ROW is 0xFFFF, four 32768s. A slide cannot produce that: to come
    out it would have to go in, and four adjacent 32768s merge — and overflow.
    """
    for packed in ALL_ROWS:
        if tables.is_overflow(packed):
            continue
        assert tables.ROW_LEFT[packed] != tables.OVERFLOW_ROW
        assert tables.ROW_SCORE[packed] != tables.OVERFLOW_SCORE
        assert tables.ROW_SCORE[packed] >= 0


def test_a_raw_index_that_forgets_to_check_goes_visibly_wrong():
    """The point of the sentinel choice: wrong, loudly, on the first lookup."""
    doomed = tables.encode_row([32768, 32768, 0, 0])
    assert tables.decode_row(tables.ROW_LEFT[doomed]) == [32768] * 4
    assert tables.ROW_SCORE[doomed] < -1, (
        "a small negative sentinel would shift a real score by one and hide"
    )


# ---------------------------------------------------------------------------
# The headline test: all 65536 entries, against the oracle.
# ---------------------------------------------------------------------------


def test_every_row_left_entry_matches_the_naive_engine():
    for packed in ALL_ROWS:
        moved, _ = naive_row_result(packed)
        if max(moved) > 32768:
            continue  # overflow rows are covered by their own test
        assert tables.ROW_LEFT[packed] == tables.encode_row(moved), (
            f"row {packed:#06x} -> {tables.decode_row(packed)}"
        )


def test_every_row_score_entry_matches_the_naive_engine():
    for packed in ALL_ROWS:
        moved, score = naive_row_result(packed)
        if max(moved) > 32768:
            continue
        assert tables.ROW_SCORE[packed] == score, (
            f"row {packed:#06x} -> {tables.decode_row(packed)}"
        )


def test_both_tables_cover_every_row():
    assert len(tables.ROW_LEFT) == 1 << 16
    assert len(tables.ROW_SCORE) == 1 << 16


def test_the_tables_are_immutable():
    with pytest.raises(TypeError):
        tables.ROW_LEFT[0] = 1


# ---------------------------------------------------------------------------
# The tables must BE the oracle, memoized — not a second implementation.
# ---------------------------------------------------------------------------


def test_the_build_calls_the_naive_engine_rather_than_reimplementing_it(monkeypatch):
    """Replace the oracle with a lie; the rebuilt tables must repeat the lie.

    If this passes with the real engine but fails here, the build has its own
    copy of the merge rule, and TASK-08 would be comparing two independent
    guesses instead of an engine against its oracle.
    """
    monkeypatch.setattr(naive, "slide_row_left", lambda row: ([2, 0, 0, 0], 7))
    row_left, row_score = tables.build_tables()
    assert set(row_left) == {tables.encode_row([2, 0, 0, 0])}
    assert set(row_score) == {7}


def test_rebuilding_reproduces_the_module_level_tables():
    row_left, row_score = tables.build_tables()
    assert row_left == tables.ROW_LEFT
    assert row_score == tables.ROW_SCORE


# ---------------------------------------------------------------------------
# Spot checks, written from SPECS section 1 rather than read off the tables.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "row, expected, score",
    [
        ([2, 2, 2, 0], [4, 2, 0, 0], 4),
        ([4, 4, 4, 4], [8, 8, 0, 0], 16),
        ([2, 2, 2, 2], [4, 4, 0, 0], 8),
        ([4, 4, 2, 2], [8, 4, 0, 0], 12),
        ([0, 0, 0, 2], [2, 0, 0, 0], 0),
        ([2, 4, 8, 16], [2, 4, 8, 16], 0),
    ],
)
def test_known_rows(row, expected, score):
    packed = tables.encode_row(row)
    assert tables.row_left(packed) == tables.encode_row(expected)
    assert tables.row_score(packed) == score


# ---------------------------------------------------------------------------
# The mirrored right-slide tables (TASK-09). Same exhaustive standard as the
# left ones: every row, checked against the oracle, not a sample.
# ---------------------------------------------------------------------------


def test_every_row_right_entry_matches_the_naive_engine():
    for packed in ALL_ROWS:
        tiles = tables.decode_row(packed)
        moved, score = naive.slide_row_left(tiles[::-1])
        moved = moved[::-1]
        if max(moved) > 32768:
            continue
        assert tables.ROW_RIGHT[packed] == tables.encode_row(moved), (
            f"row {packed:#06x} -> {tiles}"
        )
        assert tables.ROW_SCORE_RIGHT[packed] == score, f"row {packed:#06x} -> {tiles}"


def test_right_tables_cover_every_row():
    assert len(tables.ROW_RIGHT) == 1 << 16
    assert len(tables.ROW_SCORE_RIGHT) == 1 << 16


def test_right_overflow_rows_are_the_mirror_of_the_left_ones():
    left_overflow = {p for p in ALL_ROWS if tables.ROW_LEFT[p] == tables.OVERFLOW_ROW}
    right_overflow = {p for p in ALL_ROWS if tables.ROW_RIGHT[p] == tables.OVERFLOW_ROW}
    assert right_overflow == {tables._mirror_row(p) for p in left_overflow}
    assert right_overflow


def test_no_legitimate_right_entry_collides_with_either_sentinel():
    for packed in ALL_ROWS:
        if tables.ROW_RIGHT[packed] == tables.OVERFLOW_ROW:
            continue
        assert tables.ROW_SCORE_RIGHT[packed] >= 0


def test_mirroring_a_row_twice_is_the_identity():
    for packed in ALL_ROWS:
        assert tables._mirror_row(tables._mirror_row(packed)) == packed
