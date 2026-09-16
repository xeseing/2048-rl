"""Terminal rendering. Every function returns a string; nothing here prints.

That split is not stylistic. It means the rendering can be asserted on directly
in tests without capturing stdout, and it means watch mode (TASK-17) draws the
agent's game with this same code instead of a second renderer that slowly drifts
away from this one. All printing lives in `app.py`.

Plain ASCII on purpose. TASK-21 adds colour on top; this stays the thing that
still works on a dumb terminal.
"""

from game2048 import naive

# Wide enough for "2048" plus a space either side; 32768 is the engine's ceiling
# and still fits.
CELL_WIDTH = 7

EMPTY_CELL = "."

CONTROLS = "[arrow keys] move    [q] quit"


def _rule() -> str:
    return "+" + ("-" * CELL_WIDTH + "+") * naive.SIZE


def _row(row: list[int]) -> str:
    cells = "".join(
        f"{(str(value) if value else EMPTY_CELL):^{CELL_WIDTH}}|" for value in row
    )
    return "|" + cells


def board(grid: list[list[int]]) -> str:
    """The grid alone, no score and no controls."""
    lines = [_rule()]
    for row in grid:
        lines.append(_row(row))
        lines.append(_rule())
    return "\n".join(lines)


def frame(
    grid: list[list[int]],
    score: int,
    moves: int = 0,
    message: str | None = None,
) -> str:
    """One playable screen: the board, the score line, and the controls."""
    parts = [board(grid), f"Score: {score}    Moves: {moves}"]
    if message:
        parts.append(message)
    parts.append(CONTROLS)
    return "\n".join(parts)


def game_over(grid: list[list[int]], score: int, moves: int, won: bool) -> str:
    """The final screen. Shows the board it ended on, not a blank one."""
    best = max(value for row in grid for value in row)
    parts = [
        board(grid),
        "",
        "GAME OVER",
        f"Score: {score}",
        f"Moves: {moves}",
        f"Best tile: {best}",
    ]
    if won:
        parts.append("You reached 2048.")
    return "\n".join(parts)


def quit_message(score: int, moves: int = 0) -> str:
    parts = ["", "Quit.", f"Score: {score}", f"Moves: {moves}"]
    return "\n".join(parts)
