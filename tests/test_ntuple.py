"""Track A: the N-tuple network, its TD update, the agent and the trainer.

What must hold:

* V is invariant under the 8 board symmetries, because every symmetry of
  every tuple is summed. A wrong permutation breaks this at once.
* The bitboard path (trainer) and the grid path (agent) index identically.
* One update moves V by exactly `alpha * delta` on a board with no repeated
  feature (SPECS trap 6: the `1/features` factor).
* The agent is greedy on `r + V`, stays legal, and leaves the env untouched.
"""

import json

import numpy as np
import pytest
from test_env import fingerprint, with_board

from game2048 import bitboard
from game2048.agents.ntuple import (
    STAGE1,
    STAGE2,
    NTupleAgent,
    NTupleNetwork,
    grid_exponents,
)
from game2048.env import Env
from game2048.train import evaluate, td_train


def random_boards(rng, n):
    return rng.integers(0, 12, size=(n, 16))


def random_network(rng):
    net = NTupleNetwork()
    net.weights[:] = rng.standard_normal(net.weights.shape)
    return net


def test_stage1_is_four_5_tuples_times_8_symmetries():
    net = NTupleNetwork()
    assert len(STAGE1) == 4 and {len(t) for t in STAGE1} == {5}
    assert net.features == 32
    assert net.weights.shape == (4 * 16**5,) and net.weights.dtype == np.float32


def test_value_is_invariant_under_all_8_symmetries():
    rng = np.random.default_rng(0)
    net = random_network(rng)
    boards = random_boards(rng, 50)
    grids = boards.reshape(-1, 4, 4)
    variants = [np.rot90(g, k, axes=(1, 2)) for g in (grids, grids.transpose(0, 2, 1))
                for k in range(4)]  # fmt: skip
    expected = net.values(boards)
    for v in variants:
        np.testing.assert_allclose(net.values(v.reshape(-1, 16)), expected, rtol=1e-5)


def test_an_asymmetric_board_touches_32_distinct_entries():
    net = NTupleNetwork()
    board = np.arange(16).reshape(1, 16)
    assert len(set(net.indices(board)[0].tolist())) == 32


def test_bitboard_and_grid_paths_give_the_same_exponents():
    rng = np.random.default_rng(1)
    for exps in random_boards(rng, 100):
        board = int("".join(f"{e:x}" for e in exps), 16)
        grid = bitboard.decode(board)
        np.testing.assert_array_equal(td_train.exponents([board])[0], exps)
        np.testing.assert_array_equal(grid_exponents([grid])[0], exps)


def test_one_update_moves_v_by_alpha_times_delta():
    net = NTupleNetwork()
    board = np.arange(16).reshape(1, 16)
    net.update(board, np.array([100.0]), alpha=0.1)
    assert net.values(board)[0] == pytest.approx(10.0)


def test_repeated_boards_in_one_batch_accumulate():
    """Fancy-index `+=` keeps only one of the duplicates; `np.add.at` sums them."""
    net = NTupleNetwork()
    board = np.arange(16).reshape(1, 16)
    net.update(np.repeat(board, 2, axis=0), np.array([100.0, 100.0]), alpha=0.1)
    assert net.values(board)[0] == pytest.approx(20.0)


def test_save_and_load_round_trip(tmp_path):
    net = random_network(np.random.default_rng(2))
    net.save(tmp_path / "w.npz")
    loaded = NTupleNetwork.load(tmp_path / "w.npz")
    assert loaded.tuples == net.tuples
    np.testing.assert_array_equal(loaded.weights, net.weights)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


def test_agent_with_no_knowledge_takes_the_biggest_merge():
    env = with_board([[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [64, 64, 0, 0]])
    # left/right merge both pairs (132); up/down merge nothing.
    assert NTupleAgent(NTupleNetwork()).act(env) in ("left", "right")


def test_agent_follows_the_value_when_rewards_tie():
    env = with_board([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 4]])
    net = random_network(np.random.default_rng(3))
    agent = NTupleAgent(net)
    moves = env.legal_moves()
    values = [net.values(grid_exponents([env.afterstate(m)[0]]))[0] for m in moves]
    assert agent.act(env) == moves[int(np.argmax(values))]


def test_agent_plays_legally_and_leaves_the_env_untouched():
    agent = NTupleAgent(random_network(np.random.default_rng(4)))
    env = Env(seed=4200)
    for _ in range(300):
        if not env.legal_moves():
            env.reset()
        before = fingerprint(env)
        move = agent.act(env)
        assert fingerprint(env) == before
        assert move in env.legal_moves()
        env.step(move)


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


def test_training_replays_from_its_seed():
    runs = []
    for _ in range(2):
        net = NTupleNetwork()
        runs.append((td_train.train(net, games=20, seed=7), net.weights.copy()))
    assert runs[0][0] == runs[1][0]
    np.testing.assert_array_equal(runs[0][1], runs[1][1])


def test_training_learns():
    """Random play averages ~1,100; the smoke run passes 4,000 by game 200."""
    results = td_train.train(NTupleNetwork(), games=300, seed=3)
    assert len(results) == 300
    late = [score for score, _ in results[-100:]]
    assert sum(late) / len(late) > 3000


# Two legal moves (down, right); after either, any spawn leaves no move.
DEAD_END = [[16, 32, 16, 32], [128, 16, 64, 16], [16, 64, 8, 64], [8, 32, 128, 0]]


def test_terminal_afterstate_is_pulled_to_zero(monkeypatch):
    """Every move from DEAD_END ends the game after its spawn.

    So the trainer's only update is the terminal one: `0 - V(s')` on the
    afterstate it took. With every weight at 1, that V must drop below 32.
    """
    monkeypatch.setattr(bitboard, "new_game", lambda rng: bitboard.encode(DEAD_END))
    net = NTupleNetwork()
    net.weights[:] = 1.0
    [(score, _)] = td_train.train(net, games=1, seed=5)
    assert score == 0
    board = bitboard.encode(DEAD_END)
    afters = [bitboard.move(board, m)[0] for m in ("right", "down")]
    values = net.values(td_train.exponents(afters))
    assert min(values) < 32 and max(values) <= 32


def test_cli_writes_the_run_manifest_and_refuses_to_overwrite(tmp_path):
    argv = [
        "--run",
        "t",
        "--games",
        "3",
        "--log-every",
        "2",
        "--runs-dir",
        str(tmp_path),
    ]
    assert td_train.main(argv) == 0
    out = tmp_path / "t"
    assert {p.name for p in out.iterdir()} == {
        "config.json",
        "metrics.csv",
        "summary.md",
        "weights.npz",
    }
    assert (out / "metrics.csv").read_text().count("\n") == 3  # header + 2 rows
    with pytest.raises(FileExistsError):
        td_train.main(argv)


def test_a_crashed_run_resumes_to_the_same_weights_and_metrics(tmp_path, monkeypatch):
    """Crash at game 58: checkpoint at 40, metrics row at 45 already written.

    Logging every 15 leaves games in the metrics window at the checkpoint, so
    the window has to be restored too. `--resume` must drop the row past the
    checkpoint, append the rest, and end byte-identical to a run that never
    stopped (bar the seconds column).
    """
    common = ["--games", "60", "--batch", "8", "--log-every", "15"]
    common += ["--alpha-schedule", "linear", "--alpha-end", "0.01"]
    common += ["--checkpoint-every", "20", "--runs-dir", str(tmp_path)]
    assert td_train.main(["--run", "clean", *common]) == 0

    new_game, calls = bitboard.new_game, []

    def crash_at_58(rng):
        calls.append(1)
        if len(calls) == 58:
            raise RuntimeError("simulated crash")
        return new_game(rng)

    monkeypatch.setattr(bitboard, "new_game", crash_at_58)
    with pytest.raises(RuntimeError):
        td_train.main(["--run", "crash", *common])
    out = tmp_path / "crash"
    assert (out / "checkpoint_latest.npz").exists()
    assert "\n45," in (out / "metrics.csv").read_text()
    monkeypatch.setattr(bitboard, "new_game", new_game)

    # The command line may not override the run's own config.
    argv = ["--run", "crash", "--resume", "--games", "5", "--runs-dir", str(tmp_path)]
    assert td_train.main(argv) == 0

    def rows(run):
        text = (tmp_path / run / "metrics.csv").read_text().splitlines()
        return [line.rsplit(",", 1)[0] for line in text]

    assert rows("crash") == rows("clean")
    games = [r.split(",")[0] for r in rows("crash")[1:]]
    assert games == ["15", "30", "45", "60"]
    np.testing.assert_array_equal(
        NTupleNetwork.load(out / "weights.npz").weights,
        NTupleNetwork.load(tmp_path / "clean" / "weights.npz").weights,
    )
    assert not (out / "checkpoint_latest.npz").exists()


def test_linear_decay_reaches_the_update_and_the_metrics(tmp_path, monkeypatch):
    steps = []
    update = NTupleNetwork.update

    def spy(self, exponents, deltas, alpha):
        steps.append(alpha)
        update(self, exponents, deltas, alpha)

    monkeypatch.setattr(NTupleNetwork, "update", spy)
    argv = ["--run", "t", "--games", "40", "--batch", "8", "--log-every", "20"]
    argv += ["--alpha-schedule", "linear", "--alpha-start", "0.1"]
    argv += ["--alpha-end", "0.01", "--runs-dir", str(tmp_path)]
    assert td_train.main(argv) == 0
    assert steps[0] == 0.1 and steps == sorted(steps, reverse=True)
    assert 0.01 < steps[-1] < 0.02  # the last update happens before game 40 ends
    rows = (tmp_path / "t" / "metrics.csv").read_text().splitlines()
    assert rows[0] == "games,mean_score,rate_2048,max_score,alpha,seconds"
    assert [r.split(",")[4] for r in rows[1:]] == ["0.055", "0.01"]
    config = json.loads((tmp_path / "t" / "config.json").read_text())
    assert (config["alpha_schedule"], config["alpha_start"]) == ("linear", 0.1)
    assert config["alpha_end"] == 0.01 and "alpha_cadence" in config


def test_alpha_end_needs_the_linear_schedule(tmp_path):
    for extra in (["--alpha-end", "0.01"], ["--alpha-schedule", "linear"]):
        with pytest.raises(SystemExit):
            td_train.main(["--run", "t", "--runs-dir", str(tmp_path), *extra])


def test_resume_without_a_checkpoint_is_an_error(tmp_path):
    argv = ["--run", "t", "--games", "3", "--runs-dir", str(tmp_path)]
    assert td_train.main(argv) == 0
    with pytest.raises(SystemExit):
        td_train.main(["--run", "t", "--resume", "--runs-dir", str(tmp_path)])


def test_stage2_is_four_6_tuples():
    assert td_train.STAGES[2] == STAGE2
    assert len(STAGE2) == 4 and {len(t) for t in STAGE2} == {6}


def test_cli_refuses_the_held_out_seed_range(tmp_path):
    with pytest.raises(SystemExit):
        td_train.main(["--run", "t", "--seed", "900000", "--runs-dir", str(tmp_path)])


# ---------------------------------------------------------------------------
# Eval wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mean, wins, passed",
    [(15000, 50, True), (14999, 50, False), (15000, 49, False)],
)
def test_ntuple_gate(mean, wins, passed):
    tiles = [2048] * wins + [1024] * (100 - wins)
    r = evaluate.Report("ntuple", 0, [mean] * 100, tiles, 100, 1.0)
    assert evaluate.gate(r)[1] is passed


def test_eval_cli_plays_the_weights_it_is_given(tmp_path, capsys):
    NTupleNetwork().save(tmp_path / "w.npz")
    argv = ["--agent", "ntuple", "--games", "2", "--seed-base", "4200"]
    code = evaluate.main([*argv, "--weights", str(tmp_path / "w.npz")])
    assert code == 1  # an untrained network does not clear the gate
    assert "games       : 2" in capsys.readouterr().out
