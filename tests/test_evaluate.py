"""The shared eval harness (SPECS section 3, 4).

What must hold:

* Game i is exactly `Env(seed=seed_base + i)`, so every number replays.
* The statistics are computed from the games, not estimated.
* The gates know what each baseline looks like and exit 1 outside it. The random
  gate is a range, not a floor: a "random" agent scoring 3,000 is not random.
"""

import json

import pytest

from game2048.agents.random_agent import RandomAgent
from game2048.env import Env
from game2048.train import evaluate
from game2048.train.evaluate import Report


def report(scores, max_tiles=None, moves=100, seconds=1.0, agent="random", seed_base=0):
    max_tiles = max_tiles or [256] * len(scores)
    return Report(
        agent=agent,
        seed_base=seed_base,
        scores=scores,
        max_tiles=max_tiles,
        moves=moves,
        seconds=seconds,
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def test_mean_median_max():
    r = report([100, 900, 200, 400])
    assert r.mean == 400
    assert r.median == 300
    assert r.max == 900


def test_tile_rates_count_games_reaching_at_least_that_tile():
    r = report([0] * 4, max_tiles=[1024, 2048, 4096, 8192])
    assert r.rate(2048) == 0.75
    assert r.rate(4096) == 0.5


def test_histogram_counts_every_game_once_in_ascending_tile_order():
    r = report([0] * 5, max_tiles=[512, 128, 512, 2048, 128])
    assert list(r.histogram.items()) == [(128, 2), (512, 2), (2048, 1)]


def test_ms_per_move():
    assert report([0], moves=4000, seconds=2.0).ms_per_move == 0.5


# ---------------------------------------------------------------------------
# Running games
# ---------------------------------------------------------------------------


def test_game_i_is_the_env_seeded_with_seed_base_plus_i():
    r = evaluate.evaluate("random", games=3, seed_base=4200)
    for i in range(3):
        env = Env(seed=4200 + i)
        agent = RandomAgent(seed=f"{4200 + i}:agent")
        while env.legal_moves():
            env.step(agent.act(env))
        assert r.scores[i] == env.score
        assert r.max_tiles[i] == max(map(max, env.state))


def test_evaluation_replays_from_its_seed_base():
    first = evaluate.evaluate("random", games=5, seed_base=123)
    second = evaluate.evaluate("random", games=5, seed_base=123)
    assert (first.scores, first.max_tiles, first.moves) == (
        second.scores,
        second.max_tiles,
        second.moves,
    )


def test_different_seed_bases_give_different_games():
    a = evaluate.evaluate("random", games=5, seed_base=1)
    b = evaluate.evaluate("random", games=5, seed_base=2)
    assert a.scores != b.scores


def test_agent_seed_differs_from_env_seed():
    """Same int for both would make the agent's draws mirror the spawn stream."""
    assert evaluate.agent_seed(5) != 5


def test_moves_count_every_step_played():
    r = evaluate.evaluate("heuristic", games=2, seed_base=4200)
    total = 0
    for i in range(2):
        env = Env(seed=4200 + i)
        agent = evaluate.AGENTS["heuristic"](evaluate.agent_seed(4200 + i))
        while env.legal_moves():
            env.step(agent.act(env))
        total += env.moves
    assert r.moves == total
    assert r.seconds > 0


def test_unknown_agent_is_rejected_by_the_cli():
    with pytest.raises(SystemExit):
        evaluate.main(["--agent", "nope", "--games", "1", "--seed-base", "0"])


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mean, passed",
    [
        (850, True),
        (1000, True),
        (1150, True),
        (849, False),
        (1151, False),
        (3000, False),
    ],
)
def test_random_gate_is_a_range(mean, passed):
    assert evaluate.gate(report([mean]))[1] is passed


@pytest.mark.parametrize(
    "mean, wins, passed",
    [(3000, 5, True), (2999, 5, False), (3000, 4, False), (11000, 100, True)],
)
def test_heuristic_gate_needs_score_and_2048_rate(mean, wins, passed):
    tiles = [2048] * wins + [1024] * (100 - wins)
    r = report([mean] * 100, max_tiles=tiles, agent="heuristic")
    assert evaluate.gate(r)[1] is passed


def test_every_cli_agent_has_a_gate():
    assert set(evaluate.GATES) == set(evaluate.AGENTS)


def fake_evaluate(scores, max_tiles):
    """Stands in for the game loop; checks the CLI passed its arguments through."""

    def run(agent, games, seed_base):
        assert games == len(scores)
        return report(scores, max_tiles, agent=agent, seed_base=seed_base)

    return run


def test_cli_exits_1_when_the_gate_fails(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "evaluate", fake_evaluate([3000], [256]))
    code = evaluate.main(["--agent", "random", "--games", "1", "--seed-base", "0"])
    assert code == 1
    assert "FAIL" in capsys.readouterr().out


def test_cli_exits_0_when_the_gate_passes(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "evaluate", fake_evaluate([1000], [256]))
    code = evaluate.main(["--agent", "random", "--games", "1", "--seed-base", "0"])
    assert code == 0
    assert "PASS" in capsys.readouterr().out


def test_table_shows_every_reported_number(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "evaluate", fake_evaluate([1000, 1200], [2048, 4096]))
    evaluate.main(["--agent", "random", "--games", "2", "--seed-base", "777"])
    lines = capsys.readouterr().out.splitlines()

    def line(label):
        return next(text for text in lines if text.startswith(label))

    assert "1,100" in line("mean")
    assert "1,100" in line("median")
    assert "1,200" in line("max score")
    assert "100.0%" in line("2048 rate")
    assert "50.0%" in line("4096 rate")
    assert "777..778" in line("games")
    assert "ms/move" in line("ms/move")
    assert "PASS" in line("gate")


def test_json_output_is_machine_readable(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "evaluate", fake_evaluate([1000, 1200], [2048, 4096]))
    code = evaluate.main(
        ["--agent", "random", "--games", "2", "--seed-base", "777", "--json"]
    )
    data = json.loads(capsys.readouterr().out)
    assert data["mean"] == 1100
    assert data["median"] == 1100
    assert data["max"] == 1200
    assert data["rate_2048"] == 1.0
    assert data["rate_4096"] == 0.5
    assert data["histogram"] == {"2048": 1, "4096": 1}
    assert data["seed_base"] == 777
    assert data["gate"]["passed"] is True
    assert code == 0


def test_json_reports_a_failed_gate(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "evaluate", fake_evaluate([3000], [256]))
    code = evaluate.main(["--agent", "random", "--games", "1", "--json"])
    assert json.loads(capsys.readouterr().out)["gate"]["passed"] is False
    assert code == 1
