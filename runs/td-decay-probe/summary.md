# td-decay-probe

- games: 100,000, seed 1, alpha 0.1 -> 0.01 (linear), batch 64, stage 1
- last 1,000 training games: mean 63,728, 2048 rate 94.0%
- wall time: 2,312s
- held-out eval: `python -m game2048.train.evaluate --agent ntuple --games 1000 --seed-base 900000 --weights runs/td-decay-probe/weights.npz`
  -> mean 62,589, median 69,644, max 148,300, 2048 rate 92.5%, 4096 rate 71.0%, 8192 rate 4.5%, gate PASS
- vs td-01 (fixed alpha 0.1, same seed): held-out mean 64,492, 2048 96.4%, 4096 77.2%, 8192 3.9%.
  Decay trailed on the training curve at every 10k mark; the gap narrowed from 5.0% at 50k to 1.4% at 90k and never closed.
