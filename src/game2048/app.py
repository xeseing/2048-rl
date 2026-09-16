"""The terminal app. Everything that prints lives here.

`python -m game2048 play`. The installable `2048rl` console script is TASK-19 —
declaring it before `app.main` was importable would have shipped a command that
crashes on install (ADR-008).

Key handling is split in two on purpose:

* `decode()` is a pure function from a raw byte sequence to a move. It is where
  the actual trickiness lives — on Windows an arrow key arrives as *two* bytes,
  a 0xe0 (or 0x00) prefix followed by a scan code, so a bare b"H" is the letter
  H and b"\\xe0H" is the up arrow.
* `read_key_from_terminal()` is the platform I/O that feeds it, and is the only
  part that needs a real terminal.

That way CI, which has no terminal and is not Windows, still tests the part that
is easy to get wrong.
"""

import argparse
import os
import sys

from game2048 import render
from game2048.env import Env, IllegalMove

QUIT = "quit"

# Windows reports special keys as a prefix byte followed by a scan code.
WINDOWS_PREFIXES = (b"\xe0", b"\x00")
WINDOWS_ARROWS = {b"H": "up", b"P": "down", b"K": "left", b"M": "right"}

# POSIX terminals send the same four keys as ANSI escape sequences.
ANSI_ARROWS = {b"A": "up", b"B": "down", b"C": "right", b"D": "left"}

QUIT_KEYS = (b"q", b"Q", b"\x03", b"\x1b")  # q, Ctrl-C, bare Escape


def decode(sequence: bytes) -> str | None:
    """Map a raw key sequence to a move, QUIT, or None if it means nothing."""
    if sequence in QUIT_KEYS:
        return QUIT

    if len(sequence) == 2 and sequence[:1] in WINDOWS_PREFIXES:
        return WINDOWS_ARROWS.get(sequence[1:])

    if len(sequence) == 3 and sequence[:2] == b"\x1b[":
        return ANSI_ARROWS.get(sequence[2:])

    return None


def read_key_from_terminal() -> str | None:
    """Read one keypress. Needs a real terminal, so nothing here is unit-tested."""
    if os.name == "nt":
        import msvcrt

        sequence = msvcrt.getch()
        if sequence in WINDOWS_PREFIXES:
            sequence += msvcrt.getch()
        return decode(sequence)

    # POSIX. termios and tty are stdlib, so this costs no dependency and stops
    # `play` being a Windows-only command in a package people pip install.
    import termios
    import tty

    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        sequence = os.read(descriptor, 1)
        if sequence == b"\x1b":
            sequence += os.read(descriptor, 2)
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
    return decode(sequence)


def play(env: Env, read_key=None, write=print) -> int:
    """Play one game to game over or quit. Returns an exit code.

    `read_key` and `write` are injected so a test can drive a whole game to its
    end without a terminal.
    """
    if read_key is None:
        read_key = read_key_from_terminal

    message = None
    while True:
        write(render.frame(env.state, env.score, env.moves, message))
        message = None

        key = read_key()
        if key == QUIT:
            write(render.quit_message(env.score, env.moves))
            return 0
        if key is None:
            message = "Unknown key — use the arrow keys, or q to quit."
            continue

        try:
            _, _, done, _ = env.step(key)
        except IllegalMove:
            message = f"{key} does nothing here — the board would not change."
            continue

        if done:
            write(render.game_over(env.state, env.score, env.moves, env.won))
            return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="game2048", description="2048, and agents that learn to play it."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    play_command = subcommands.add_parser("play", help="play in the terminal")
    play_command.add_argument(
        "--seed", type=int, default=None, help="seed the game for a reproducible board"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "play":
        return play(Env(seed=args.seed))
    return 1
