"""Baseline agents (SPECS section 4.1, 4.2).

Two properties matter beyond "plays a game":

* Neither agent ever emits a move outside `env.legal_moves()`. An illegal move
  raises in `Env.step`, so a baseline that emits one is not a baseline.
* The heuristic agent is the first real user of `Env.afterstate()` purity
  (TASK-04). It looks at every legal move and takes one; the env must be
  byte-identical after `act` returns, RNG state included.
"""

from test_env import DEAD, WEDGED, fingerprint, with_board

from game2048.agents import heuristic
from game2048.agents.base import Agent
from game2048.agents.heuristic import HeuristicAgent
from game2048.agents.random_agent import RandomAgent
from game2048.env import Env

# Chi-square critical value, df=3, alpha=0.01 (see FACTS: no scipy).
CHI2_DF3_ALPHA01 = 11.345

# Every row and column non-increasing away from the top-left corner.
MONOTONE = [
    [64, 32, 16, 8],
    [32, 16, 8, 4],
    [16, 8, 4, 2],
    [8, 4, 2, 0],
]

# Rows zig-zag; nothing about it is monotone.
ZIGZAG = [
    [2, 64, 2, 64],
    [64, 2, 64, 2],
    [2, 64, 2, 64],
    [64, 2, 64, 2],
]


def check_every_move_is_legal(agent, steps=1000, seed=0):
    env = Env(seed=seed)
    for _ in range(steps):
        legal = env.legal_moves()
        if not legal:
            env.reset()
            continue
        move = agent.act(env)
        assert move in legal, (move, legal, env.state)
        env.step(move)


def play_game(agent, seed):
    env = Env(seed=seed)
    while env.legal_moves():
        env.step(agent.act(env))
    return env.score


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


def test_both_agents_satisfy_the_agent_protocol():
    assert isinstance(RandomAgent(seed=0), Agent)
    assert isinstance(HeuristicAgent(), Agent)


def test_agents_have_distinct_names():
    assert RandomAgent(seed=0).name() == "random"
    assert HeuristicAgent().name() == "heuristic"


# ---------------------------------------------------------------------------
# Random
# ---------------------------------------------------------------------------


def test_random_only_emits_legal_moves():
    check_every_move_is_legal(RandomAgent(seed=1))


def test_random_on_a_wedged_board_picks_only_the_two_legal_moves():
    env = with_board(WEDGED)
    agent = RandomAgent(seed=2)
    assert {agent.act(env) for _ in range(200)} == {"down", "right"}


def test_random_is_uniform_over_legal_moves():
    env = Env(seed=0)
    env._board = [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert sorted(env.legal_moves()) == ["down", "left", "right", "up"]
    agent = RandomAgent(seed=3)
    draws = 8000
    counts = {}
    for _ in range(draws):
        move = agent.act(env)
        counts[move] = counts.get(move, 0) + 1
    expected = draws / 4
    statistic = sum((c - expected) ** 2 / expected for c in counts.values())
    assert len(counts) == 4
    assert statistic < CHI2_DF3_ALPHA01, counts


def test_random_replays_from_its_seed():
    assert play_game(RandomAgent(seed=9), 9) == play_game(RandomAgent(seed=9), 9)


def test_random_does_not_touch_the_env():
    env = Env(seed=4)
    before = fingerprint(env)
    RandomAgent(seed=4).act(env)
    assert fingerprint(env) == before


# ---------------------------------------------------------------------------
# Heuristic: afterstate purity (TASK-04's guarantee, first real user)
# ---------------------------------------------------------------------------


def test_heuristic_act_leaves_the_env_byte_identical():
    env = Env(seed=5)
    agent = HeuristicAgent()
    for _ in range(300):
        if not env.legal_moves():
            env.reset()
        before = fingerprint(env)
        move = agent.act(env)
        assert fingerprint(env) == before, "heuristic.act mutated the env"
        env.step(move)


def test_heuristic_features_do_not_mutate_their_input():
    grid = [row[:] for row in ZIGZAG]
    heuristic.evaluate(grid)
    assert grid == ZIGZAG


# ---------------------------------------------------------------------------
# Heuristic: legality and choice
# ---------------------------------------------------------------------------


def test_heuristic_only_emits_legal_moves():
    check_every_move_is_legal(HeuristicAgent(), seed=6)


def test_heuristic_on_a_wedged_board_picks_a_legal_move():
    assert HeuristicAgent().act(with_board(WEDGED)) in ("down", "right")


def test_heuristic_picks_the_afterstate_its_features_rank_highest():
    env = Env(seed=7)
    agent = HeuristicAgent()
    for _ in range(100):
        if not env.legal_moves():
            env.reset()
        values = {
            move: heuristic.evaluate(env.afterstate(move)[0])
            for move in env.legal_moves()
        }
        move = agent.act(env)
        assert values[move] == max(values.values())
        env.step(move)


def test_heuristic_is_deterministic():
    env = Env(seed=8)
    assert HeuristicAgent().act(env) == HeuristicAgent().act(env)


def test_heuristic_beats_random_by_a_wide_margin():
    seeds = range(100, 110)
    random_mean = sum(play_game(RandomAgent(seed=s), s) for s in seeds) / len(seeds)
    heuristic_mean = sum(play_game(HeuristicAgent(), s) for s in seeds) / len(seeds)
    assert heuristic_mean > 3 * random_mean, (heuristic_mean, random_mean)


# ---------------------------------------------------------------------------
# Heuristic: features, each against a board whose answer is obvious
# ---------------------------------------------------------------------------


def test_empty_counts_zero_cells():
    assert heuristic.empty(MONOTONE) == 1
    assert heuristic.empty(DEAD) == 0
    assert heuristic.empty([[0] * 4 for _ in range(4)]) == 16


def test_monotonicity_penalty_is_zero_on_a_monotone_board_only():
    assert heuristic.monotonicity(MONOTONE) == 0
    assert heuristic.monotonicity(ZIGZAG) > 0


def test_monotonicity_accepts_either_direction():
    mirrored = [row[::-1] for row in MONOTONE[::-1]]
    assert heuristic.monotonicity(mirrored) == 0


def test_monotonicity_checks_columns_as_well_as_rows():
    rows_sorted_columns_zigzag = [
        [2, 4, 8, 16],
        [16, 32, 64, 128],
        [2, 4, 8, 16],
        [16, 32, 64, 128],
    ]
    columns_sorted_rows_zigzag = [list(c) for c in zip(*rows_sorted_columns_zigzag)]
    assert heuristic.monotonicity(rows_sorted_columns_zigzag) > 0
    assert heuristic.monotonicity(columns_sorted_rows_zigzag) > 0


def test_smoothness_penalty_is_zero_when_neighbours_match():
    assert heuristic.smoothness([[4] * 4 for _ in range(4)]) == 0
    assert heuristic.smoothness(ZIGZAG) > heuristic.smoothness(MONOTONE) > 0


def test_smoothness_ignores_empty_cells():
    assert heuristic.smoothness([[8, 0, 0, 8], [0] * 4, [0] * 4, [0] * 4]) == 0


def test_max_in_corner():
    assert heuristic.max_in_corner(MONOTONE) == 1
    assert heuristic.max_in_corner([row[::-1] for row in MONOTONE]) == 1
    centred = [[0, 0, 0, 0], [0, 64, 0, 0], [0, 0, 2, 0], [0, 0, 0, 0]]
    assert heuristic.max_in_corner(centred) == 0


def test_evaluate_prefers_the_ordered_board():
    assert heuristic.evaluate(MONOTONE) > heuristic.evaluate(ZIGZAG)


def test_evaluate_rewards_space():
    crowded = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [0, 0, 0, 0]]
    roomy = [[2, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert heuristic.evaluate(roomy) > heuristic.evaluate(crowded)
