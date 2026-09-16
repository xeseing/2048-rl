"""The environment API frozen in SPECS section 2.3.

Two properties here matter more than the rest, because breaking either one
poisons every agent built on top without anything visibly failing:

* An illegal move must raise and change *nothing* (SPECS trap 3). Not "leave the
  board looking the same" — leave the env byte-identical, RNG state included.
  A spawn on an illegal move silently destroys any agent's learning.
* `afterstate()` must be pure. Every agent above random calls it speculatively,
  thousands of times a game, on moves it will not take. If it leaks a spawn or a
  score increment, the agent trains on a world that does not exist.

Both are asserted by fingerprinting the whole env — board, score, win flag, move
count and the RNG's internal state — and comparing bytes.
"""

import inspect
import json
import random

import pytest

from game2048 import env as env_module
from game2048 import naive
from game2048.env import Env, IllegalMove

# Left and up change nothing; down and right do. One empty cell, at (3, 3).
WEDGED = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 2, 4],
    [16, 2, 4, 0],
]

# No legal move in any direction.
DEAD = [
    [2, 4, 8, 16],
    [4, 8, 16, 2],
    [8, 16, 2, 4],
    [16, 2, 4, 8],
]


def fingerprint(env):
    """Every piece of state the env owns, as bytes.

    The RNG state is the important inclusion: it is what makes "did not spawn"
    provable rather than merely plausible. A spawn consumes draws, so any
    accidental one moves this fingerprint even if the board happens to look the
    same afterwards.
    """
    return json.dumps(
        {
            "board": env.state,
            "score": env.score,
            "won": env.won,
            "moves": env.moves,
            "rng": repr(env._rng.getstate()),
        },
        sort_keys=True,
    ).encode("utf-8")


def with_board(board, seed=0):
    """An env forced onto a known board, so legality can be set up on purpose."""
    env = Env(seed=seed)
    env._board = [row[:] for row in board]
    return env


def play(env, policy_seed, limit=10_000):
    """Drive an env to game over with a seeded policy. Returns the transcript."""
    policy = random.Random(policy_seed)
    transcript = []
    for _ in range(limit):
        moves = env.legal_moves()
        if not moves:
            break
        move = policy.choice(sorted(moves))
        state, reward, done, info = env.step(move)
        transcript.append([move, reward, state, done, info])
        if done:
            break
    return json.dumps(transcript, sort_keys=True).encode("utf-8")


# ---------------------------------------------------------------------------
# The frozen signatures from SPECS section 2.3.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, parameters",
    [
        ("__init__", ["self", "seed"]),
        ("reset", ["self", "seed"]),
        ("legal_moves", ["self"]),
        ("afterstate", ["self", "move"]),
        ("step", ["self", "move"]),
        ("render", ["self"]),
    ],
)
def test_the_frozen_api_has_the_signature_specs_says_it_has(name, parameters):
    signature = inspect.signature(getattr(Env, name))
    assert list(signature.parameters) == parameters


def test_illegal_move_is_an_exception_the_caller_can_catch():
    assert issubclass(IllegalMove, Exception)


def test_move_type_is_exported_for_agents():
    assert hasattr(env_module, "Move")


# ---------------------------------------------------------------------------
# SPECS trap 3: an illegal move raises, and changes nothing at all.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("move", ["left", "up"])
def test_an_illegal_move_raises_illegal_move(move):
    env = with_board(WEDGED)
    with pytest.raises(IllegalMove):
        env.step(move)


@pytest.mark.parametrize("move", ["left", "up"])
def test_an_illegal_move_leaves_the_env_byte_identical(move):
    env = with_board(WEDGED)
    before = fingerprint(env)
    with pytest.raises(IllegalMove):
        env.step(move)
    assert fingerprint(env) == before


def test_an_illegal_move_does_not_spawn():
    """The tile count is the blunt version of the fingerprint check."""
    env = with_board(WEDGED)
    occupied = sum(1 for row in env.state for v in row if v)
    with pytest.raises(IllegalMove):
        env.step("left")
    assert sum(1 for row in env.state for v in row if v) == occupied


def test_an_illegal_move_does_not_score():
    env = with_board(WEDGED)
    env.score = 1234
    with pytest.raises(IllegalMove):
        env.step("up")
    assert env.score == 1234


def test_every_move_on_a_dead_board_raises_and_changes_nothing():
    env = with_board(DEAD)
    before = fingerprint(env)
    for move in ("up", "down", "left", "right"):
        with pytest.raises(IllegalMove):
            env.step(move)
    assert fingerprint(env) == before
    assert env.legal_moves() == []


def test_the_raised_error_names_the_move():
    env = with_board(WEDGED)
    with pytest.raises(IllegalMove, match="left"):
        env.step("left")


# ---------------------------------------------------------------------------
# afterstate() is pure.
# ---------------------------------------------------------------------------


def test_afterstate_on_every_legal_move_leaves_the_env_byte_identical():
    env = Env(seed=7)
    for _ in range(40):
        before = fingerprint(env)
        for move in env.legal_moves():
            env.afterstate(move)
        assert fingerprint(env) == before, "afterstate mutated the env"
        env.step(min(env.legal_moves()))
        if not env.legal_moves():
            break


def test_afterstate_on_an_illegal_move_neither_raises_nor_mutates():
    env = with_board(WEDGED)
    before = fingerprint(env)
    _state, reward, changed = env.afterstate("left")
    assert changed is False
    assert reward == 0
    assert fingerprint(env) == before


def test_afterstate_does_not_hand_back_the_envs_own_board():
    """A caller scribbling on the returned board must not reach into the env."""
    env = with_board(WEDGED)
    before = fingerprint(env)
    state, _, _ = env.afterstate("down")
    state[0][0] = 99999
    assert fingerprint(env) == before


def test_afterstate_agrees_with_the_naive_engine():
    env = Env(seed=3)
    for move in ("up", "down", "left", "right"):
        assert env.afterstate(move) == naive.move(env.state, move)


def test_afterstate_reward_is_the_reward_step_then_gives():
    env = Env(seed=11)
    for _ in range(60):
        moves = env.legal_moves()
        if not moves:
            break
        move = min(moves)
        _, predicted, changed = env.afterstate(move)
        assert changed is True
        _, actual, _, _ = env.step(move)
        assert actual == predicted


# ---------------------------------------------------------------------------
# reset() and the other frozen methods.
# ---------------------------------------------------------------------------


def test_reset_starts_from_two_tiles():
    env = Env(seed=0)
    state = env.reset()
    assert sum(1 for row in state for v in row if v) == 2
    assert env.score == 0
    assert env.moves == 0
    assert env.won is False


def test_reset_does_not_hand_back_the_envs_own_board():
    env = Env(seed=0)
    state = env.reset()
    state[0][0] = 99999
    assert env.state[0][0] != 99999


def test_state_is_a_copy_every_time():
    env = Env(seed=0)
    assert env.state is not env.state


def test_legal_moves_agrees_with_the_naive_engine():
    env = Env(seed=5)
    for _ in range(50):
        assert sorted(env.legal_moves()) == sorted(naive.legal_moves(env.state))
        if not env.legal_moves():
            break
        env.step(min(env.legal_moves()))


def test_step_spawns_exactly_one_tile():
    """Counted against the afterstate, not the starting board: a merge removes a
    tile too, so comparing with the board before the move proves nothing."""
    env = Env(seed=9)
    for _ in range(50):
        moves = env.legal_moves()
        if not moves:
            break
        move = min(moves)
        afterstate, _, _ = env.afterstate(move)
        on_afterstate = sum(1 for row in afterstate for v in row if v)
        env.step(move)
        assert sum(1 for row in env.state for v in row if v) == on_afterstate + 1


def test_done_is_true_only_when_no_legal_move_remains():
    env = Env(seed=13)
    for _ in range(10_000):
        moves = env.legal_moves()
        if not moves:
            break
        _, _, done, _ = env.step(min(moves))
        assert done == (env.legal_moves() == [])
        if done:
            break


def test_the_win_event_is_recorded_and_play_continues():
    env = with_board([[1024, 1024, 0, 0], [0, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0]])
    assert env.won is False
    _, reward, done, info = env.step("left")
    assert reward == 2048
    assert env.won is True
    assert info["won"] is True
    assert done is False, "reaching 2048 must not end the game"


def test_render_returns_a_string_showing_the_tiles():
    env = with_board(WEDGED)
    out = env.render()
    assert isinstance(out, str)
    for value in (2, 4, 8, 16):
        assert str(value) in out


def test_an_unknown_direction_is_a_value_error_not_an_illegal_move():
    env = Env(seed=0)
    with pytest.raises(ValueError):
        env.step("sideways")
    with pytest.raises(ValueError):
        env.afterstate("sideways")


# ---------------------------------------------------------------------------
# Determinism.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 20_240_915])
def test_two_envs_with_the_same_seed_start_byte_identical(seed):
    assert fingerprint(Env(seed=seed)) == fingerprint(Env(seed=seed))


@pytest.mark.parametrize("seed", [0, 1, 20_240_915])
def test_two_envs_with_the_same_seed_replay_a_whole_game_byte_identical(seed):
    assert play(Env(seed=seed), policy_seed=99) == play(Env(seed=seed), policy_seed=99)


def test_different_seeds_give_different_games():
    assert play(Env(seed=0), policy_seed=99) != play(Env(seed=1), policy_seed=99)


def test_reset_with_a_seed_reproduces_that_seeds_opening():
    env = Env(seed=0)
    opening = Env(seed=4242).state
    env.reset(seed=4242)
    assert env.state == opening


def test_the_env_spawns_exactly_what_the_naive_engine_would_from_the_same_seed():
    """No hidden draws: env's RNG stream is naive's, in the same order."""
    seed = 2024
    env = Env(seed=seed)

    rng = random.Random(seed)
    board = naive.new_game(rng)
    assert env.state == board

    policy = random.Random(5)
    for _ in range(80):
        moves = env.legal_moves()
        if not moves:
            break
        move = policy.choice(sorted(moves))
        env.step(move)
        afterstate, _, changed = naive.move(board, move)
        assert changed
        board = naive.spawn(afterstate, rng)
        assert env.state == board
