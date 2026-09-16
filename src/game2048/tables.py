"""Precomputed row tables — the naive engine, memoized (SPECS section 2.2).

A row is 4 nibbles of log2(tile) packed into 16 bits, cell 0 in the **highest**
nibble, so a row reads left to right in hex: `[2, 4, 8, 16]` is `0x1234`. Nibble
0 is an empty cell, 1 is a 2, 15 is 32768.

`ROW_LEFT[row]` and `ROW_SCORE[row]` are built by calling
`naive.slide_row_left` on every one of the 65536 rows. That is not an
implementation detail, it is the guarantee: the tables inherit the oracle's
correctness by construction, so TASK-08's differential test is comparing the
bitboard engine's *plumbing* — transposes, reversals, packing — against the
naive engine, and not comparing two independent guesses at the merge rule.

Never hand-write this build to "match" the naive engine. If the oracle has a
subtle bug, these tables must have exactly the same bug, or the differential
test quietly stops being a test.
"""

from game2048 import naive

ROW_CELLS = naive.SIZE
ROW_COUNT = 1 << (4 * ROW_CELLS)  # 65536

# A nibble holds log2(tile), so 15 is 32768 and there is no room for 65536.
MAX_EXPONENT = 15
MAX_TILE = 1 << MAX_EXPONENT

# Sliding a row can produce a tile the encoding cannot hold: 32768 + 32768.
# Those rows are marked rather than wrapped (SPECS trap 4); `row_left` and
# `row_score` raise on them.
#
# The sentinels are chosen so that code which indexes the tables RAW — which the
# bitboard engine will, to reach the throughput gate — and forgets to check goes
# visibly wrong at once instead of corrupting quietly:
#
#   OVERFLOW_ROW is 0xFFFF, four nibbles of 15, i.e. a row of four 32768s. No
#   slide can ever produce that: for it to come out, it would have to go in, and
#   four adjacent 32768s merge — and overflow. So it is unambiguous, and a board
#   that picks it up is instantly, obviously wrong.
#
#   OVERFLOW_SCORE is large and negative. A small sentinel like -1 would shift a
#   real score by one per lookup, which is precisely the silent corruption this
#   exists to prevent; this one sends the score somewhere no game could reach and
#   fails any "score is non-negative" check on the spot.
#
# `test_no_legitimate_entry_collides_with_either_sentinel` proves both are
# unreachable by real play, over all 65536 rows.
OVERFLOW_ROW = 0xFFFF
OVERFLOW_SCORE = -1_000_000_000


class NibbleOverflow(ValueError):
    """A tile above 32768, which no nibble can hold.

    Raised rather than wrapped. Wrapping 65536 would store exponent 16 as
    nibble 0 — an empty cell — so the engine would silently delete the largest
    tile on the board and keep playing (SPECS trap 4).
    """


def _exponent(tile: int) -> int:
    if tile == 0:
        return 0
    if tile & (tile - 1):
        raise ValueError(f"tile {tile} is not a power of two")
    exponent = tile.bit_length() - 1
    if exponent > MAX_EXPONENT:
        raise NibbleOverflow(f"tile {tile} exceeds the {MAX_TILE} nibble ceiling")
    return exponent


def encode_row(tiles: list[int]) -> int:
    """Pack 4 tile values into 16 bits. Cell 0 lands in the highest nibble."""
    packed = 0
    for tile in tiles:
        packed = (packed << 4) | _exponent(tile)
    return packed


def decode_row(packed: int) -> list[int]:
    """Unpack 16 bits back into 4 tile values."""
    return [
        (0 if exponent == 0 else 1 << exponent)
        for exponent in (
            (packed >> shift) & 0xF for shift in range(4 * (ROW_CELLS - 1), -1, -4)
        )
    ]


def build_tables() -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Build both tables by asking the oracle about all 65536 rows.

    Looked up as `naive.slide_row_left` at call time rather than imported by
    name, so a test can replace the oracle and prove this delegates to it
    instead of carrying its own copy of the merge rule.
    """
    row_left = []
    row_score = []
    for packed in range(ROW_COUNT):
        moved, score = naive.slide_row_left(decode_row(packed))
        try:
            row_left.append(encode_row(moved))
        except NibbleOverflow:
            row_left.append(OVERFLOW_ROW)
            row_score.append(OVERFLOW_SCORE)
            continue
        row_score.append(score)
    return tuple(row_left), tuple(row_score)


def _mirror_row(packed: int) -> int:
    """Reverse the four nibbles of a row: [a b c d] -> [d c b a]."""
    return (
        ((packed & 0x000F) << 12)
        | ((packed & 0x00F0) << 4)
        | ((packed & 0x0F00) >> 4)
        | ((packed & 0xF000) >> 12)
    )


def build_right_tables(
    row_left: tuple[int, ...], row_score: tuple[int, ...]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Derive the right-slide tables by mirroring the left ones.

    Sliding a row right is sliding its mirror left and mirroring back. Building
    the table means the bitboard engine never reverses a board at move time:
    `right` becomes a plain lookup and `down` becomes transpose, lookup,
    transpose. Costs about a megabyte and a tenth of a second at import.

    Overflow is carried across explicitly rather than relying on the fact that
    `OVERFLOW_ROW` happens to be a palindrome.
    """
    right = []
    score = []
    for packed in range(ROW_COUNT):
        mirrored = _mirror_row(packed)
        moved = row_left[mirrored]
        if moved == OVERFLOW_ROW:
            right.append(OVERFLOW_ROW)
            score.append(OVERFLOW_SCORE)
        else:
            right.append(_mirror_row(moved))
            score.append(row_score[mirrored])
    return tuple(right), tuple(score)


ROW_LEFT, ROW_SCORE = build_tables()
ROW_RIGHT, ROW_SCORE_RIGHT = build_right_tables(ROW_LEFT, ROW_SCORE)


def is_overflow(packed: int) -> bool:
    """Does sliding this row left produce a tile the encoding cannot hold?"""
    return ROW_LEFT[packed] == OVERFLOW_ROW


def row_left(packed: int) -> int:
    """The row after sliding left. Raises if the result cannot be encoded."""
    result = ROW_LEFT[packed]
    if result == OVERFLOW_ROW:
        raise NibbleOverflow(
            f"row {packed:#06x} -> {decode_row(packed)} merges past {MAX_TILE}"
        )
    return result


def row_score(packed: int) -> int:
    """The score gained by sliding left. Raises if the result cannot be encoded."""
    result = ROW_SCORE[packed]
    if result == OVERFLOW_SCORE:
        raise NibbleOverflow(
            f"row {packed:#06x} -> {decode_row(packed)} merges past {MAX_TILE}"
        )
    return result
