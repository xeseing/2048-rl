# EXPERIMENTS.md — One row per training run

**APPEND ONLY.** Every run gets a row, including killed and failed runs. A killed run
with no row is a run that gets pointlessly repeated.

| run_id | date | agent | seed | games | key hyperparams | mean score | max tile rate | outcome |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| smoke-b64 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 64 | 12,900 (last 200, training) | 2048: 7.5% | smoke; pipeline proven, 12s |
| smoke-b256 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 256 | 1,916 (last 200, training) | 2048: 0% | failed to learn (F-001) |
| smoke-b16 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 16 | 11,785 (last 200, training) | 2048: 6.5% | learns, no faster than 64 |
| td-01 | 2026-09-17 | ntuple S1 | 1 | 100,000 | alpha 0.1 const, batch 64, tuples per ADR-022 | **64,492** held-out (median 70,620); training last 1k 64,783 | 2048: 96.4%, 4096: 77.2%, 8192: 3.9% | TASK-12 gate PASS; 4,251s train, 327s eval |
| smoke-s2-resume | 2026-09-17 | ntuple S2 | 1 | 1,000 | alpha 0.1, batch 64, ckpt every 200; hard-killed after row 500 (ckpt 401), `--resume` | 10,537 (last 100, training) | 2048: 0% | resume proven: metrics identical bar seconds, weights bit-identical to smoke-s2-clean; run twice |
| smoke-s2-clean | 2026-09-17 | ntuple S2 | 1 | 1,000 | alpha 0.1, batch 64, ckpt every 200 | 10,537 (last 100, training) | 2048: 0% | uninterrupted twin of smoke-s2-resume; 7.4s |
| smoke-s1-decay-10k | 2026-09-17 | ntuple S1 | 1 | 10,000 | alpha linear 0.1 -> 0.01 over the 10k games, batch 64 | 21,624 (last 1k, training) vs td-01 at 10k: 26,750 | 2048: 35.3% vs td-01 54.5% | decay worse at 10k (-19% mean); stop condition hit, td-02 on hold. Schedule is 100x compressed vs td-02's; 124.6s |
