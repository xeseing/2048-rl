# 2048-rl

> An agent that teaches itself to play 2048 from self-play — no human games, no
> hardcoded strategy, just the score as reward.

[![CI](https://github.com/xeseing/2048-rl/actions/workflows/ci.yml/badge.svg)](https://github.com/xeseing/2048-rl/actions/workflows/ci.yml)

<!-- TASK-22: asciinema/GIF of `2048rl watch` goes here. Do this before the results
     table — the demo is what makes someone read the rest. -->

## Install

```bash
pip install git+https://github.com/xeseing/2048-rl
2048rl fetch-weights
2048rl watch --agent ntuple
```

## Results

<!-- TASK-22: filled from RESULTS.md. Numbers must match exactly. -->

| Agent | Mean score | Median | 2048 | 4096 | 8192 | ms/move |
| :-- | --: | --: | --: | --: | --: | --: |
| Random | | | | | | |
| Heuristic (1-ply) | | | | | | |
| Expectimax (d=3) | | | | | | |
| **N-tuple TD (Stage 2)** | | | | | | |
| Double DQN | | | | | | |

## Why the sparse linear network beats the convnet

<!-- TASK-22: one paragraph, drawn from RESULTS.md. Sample efficiency, afterstate
     valuation, and how each representation captures tile adjacency. -->

## How it works

Two learning tracks, both built and benchmarked against each other:

- **N-tuple value network + TD(0) on afterstates** — a sparse linear network over
  board patterns, updated over all 8 board symmetries. This is what actually wins at
  2048.
- **Double DQN** — the deep-RL track, built properly and reported honestly.

Random and expectimax agents exist only as the floor and ceiling to measure against.

## Development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
```

See `CLAUDE.md` for the working protocol, `SPECS.md` for the technical contract, and
`GIT_WORKFLOW.md` for branching and releases.

## License

MIT
