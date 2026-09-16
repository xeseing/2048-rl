"""Terminal rendering and the `play` loop.

Assertions here are on substrings, not exact whitespace. A renderer whose column
padding shifts by one space is not a bug worth blocking a merge over; a renderer
that loses the score is.

The split that makes this testable: `render` returns strings and never prints,
`app` does all the printing, and the key decoding is a pure function separated
from the platform I/O that feeds it. So the fiddly part — Windows sending arrow
keys as two bytes behind a 0xe0 prefix — is tested on Linux CI without a
terminal anywhere in sight.
"""

import pytest

from game2048 import app, render
from game2048.env import Env

GRID = [
    [2, 4, 8, 16],
    [0, 32, 64, 128],
    [256, 512, 1024, 2048],
    [0, 0, 0, 4],
]


def keys(*sequence):
    """A scripted key source. Falls back to quit so no test can hang."""
    remaining = iter(sequence)
    return lambda: next(remaining, app.QUIT)


class Writer:
    """Captures what `play` would have printed."""

    def __init__(self):
        self.frames = []

    def __call__(self, text):
        self.frames.append(str(text))

    @property
    def text(self):
        return "\n".join(self.frames)


# ---------------------------------------------------------------------------
# Key decoding. Pure, so it is testable off-Windows.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sequence, expected",
    [
        (b"\xe0H", "up"),
        (b"\xe0P", "down"),
        (b"\xe0K", "left"),
        (b"\xe0M", "right"),
        # Windows also reports special keys behind a 0x00 prefix.
        (b"\x00H", "up"),
        (b"\x00P", "down"),
        (b"\x00K", "left"),
        (b"\x00M", "right"),
        # POSIX terminals send the same four as ANSI escape sequences.
        (b"\x1b[A", "up"),
        (b"\x1b[B", "down"),
        (b"\x1b[D", "left"),
        (b"\x1b[C", "right"),
    ],
)
def test_arrow_keys_decode_to_moves(sequence, expected):
    assert app.decode(sequence) == expected


@pytest.mark.parametrize("sequence", [b"q", b"Q", b"\x03", b"\x1b"])
def test_quit_keys_decode_to_quit(sequence):
    assert app.decode(sequence) == app.QUIT


@pytest.mark.parametrize("sequence", [b"z", b"H", b"P", b"", b"\xe0Z", b"\x1b[Z"])
def test_unrecognised_keys_decode_to_none(sequence):
    assert app.decode(sequence) is None


def test_a_bare_scancode_without_its_prefix_is_not_a_move():
    """0xe0 is what distinguishes the up arrow from the letter H."""
    assert app.decode(b"H") is None
    assert app.decode(b"\xe0H") == "up"


# ---------------------------------------------------------------------------
# Rendering. Substrings, not whitespace.
# ---------------------------------------------------------------------------


def test_the_board_shows_every_tile_value():
    out = render.board(GRID)
    for value in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048):
        assert str(value) in out


def test_the_board_does_not_print_zeros_as_zero():
    assert "0 " not in render.board([[0] * 4 for _ in range(4)])


def test_the_frame_shows_the_score_and_the_controls():
    out = render.frame(GRID, score=1234, moves=56)
    assert "Score:" in out
    assert "1234" in out
    assert "56" in out
    assert "q" in out


def test_the_frame_can_carry_a_message():
    out = render.frame(GRID, score=0, moves=0, message="left does nothing here")
    assert "left does nothing here" in out


def test_the_game_over_screen_shows_the_final_score_and_best_tile():
    out = render.game_over(GRID, score=9876, moves=421, won=True)
    assert "GAME OVER" in out
    assert "Score:" in out
    assert "9876" in out
    assert "421" in out
    assert "2048" in out


def test_the_game_over_screen_still_shows_the_board():
    out = render.game_over(GRID, score=1, moves=1, won=False)
    assert "512" in out


# ---------------------------------------------------------------------------
# The constraint: Env.render() returns, and does not print.
# ---------------------------------------------------------------------------


def test_env_render_returns_a_string(capsys):
    env = Env(seed=0)
    out = env.render()
    assert isinstance(out, str)
    assert "Score:" in out
    assert capsys.readouterr().out == "", "render() printed instead of returning"


def test_env_render_reflects_the_current_score():
    env = Env(seed=0)
    env.score = 4242
    assert "4242" in env.render()


# ---------------------------------------------------------------------------
# The play loop.
# ---------------------------------------------------------------------------


def test_q_quits_immediately_and_reports_the_score():
    env = Env(seed=0)
    out = Writer()
    assert app.play(env, read_key=keys(app.QUIT), write=out) == 0
    assert env.moves == 0
    assert "Score:" in out.text


def test_a_legal_move_advances_the_game():
    env = Env(seed=0)
    move = min(env.legal_moves())
    assert app.play(env, read_key=keys(move, app.QUIT), write=Writer()) == 0
    assert env.moves == 1


def test_an_illegal_move_is_reported_and_does_not_advance_the_game():
    env = Env(seed=0)
    env._board = [
        [2, 4, 8, 16],
        [4, 8, 16, 2],
        [8, 16, 2, 4],
        [16, 2, 4, 0],
    ]
    out = Writer()
    app.play(env, read_key=keys("left", app.QUIT), write=out)
    assert env.moves == 0
    assert "left" in out.text.lower()


def test_an_unknown_key_is_reported_and_does_not_advance_the_game():
    env = Env(seed=0)
    out = Writer()
    app.play(env, read_key=keys(None, app.QUIT), write=out)
    assert env.moves == 0
    assert "arrow" in out.text.lower()


def test_playing_to_game_over_shows_the_game_over_screen():
    env = Env(seed=0)
    out = Writer()

    order = ["up", "down", "left", "right"]
    counter = {"n": 0}

    def cycle():
        counter["n"] += 1
        if counter["n"] > 20_000:
            return app.QUIT
        return order[counter["n"] % 4]

    assert app.play(env, read_key=cycle, write=out) == 0
    assert env.legal_moves() == [], "the game did not actually end"
    assert "GAME OVER" in out.text
    assert str(env.score) in out.text


# ---------------------------------------------------------------------------
# The CLI surface. `2048rl` itself is TASK-19; this is `python -m game2048`.
# ---------------------------------------------------------------------------


def test_the_parser_accepts_play_with_a_seed():
    args = app.build_parser().parse_args(["play", "--seed", "42"])
    assert args.command == "play"
    assert args.seed == 42


def test_the_parser_accepts_play_without_a_seed():
    assert app.build_parser().parse_args(["play"]).seed is None


def test_an_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as exit_info:
        app.build_parser().parse_args(["frobnicate"])
    assert exit_info.value.code != 0


def test_main_runs_play_and_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr(app, "read_key_from_terminal", lambda: app.QUIT)
    assert app.main(["play", "--seed", "1"]) == 0
    assert "Score:" in capsys.readouterr().out


def test_main_seeds_the_game_reproducibly(monkeypatch, capsys):
    monkeypatch.setattr(app, "read_key_from_terminal", lambda: app.QUIT)
    app.main(["play", "--seed", "99"])
    first = capsys.readouterr().out
    app.main(["play", "--seed", "99"])
    assert capsys.readouterr().out == first
