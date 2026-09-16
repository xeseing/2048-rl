# td-01

- games: 100,000, seed 1, alpha 0.1, batch 64
- last 1,000 training games: mean 64,783, 2048 rate 96.2%
- wall time: 4,251s
- held-out eval: `python -m game2048.train.evaluate --agent ntuple --games 1000 --seed-base 900000 --weights runs/td-01/weights.npz`
  -> mean 64,492, median 70,620, max 133,928, 2048 rate 96.4%, 4096 rate 77.2%, gate PASS
