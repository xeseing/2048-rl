# EXPERIMENTS.md — One row per training run

**APPEND ONLY.** Every run gets a row, including killed and failed runs. A killed run
with no row is a run that gets pointlessly repeated.

| run_id | date | agent | seed | games | key hyperparams | mean score | max tile rate | outcome |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| smoke-b64 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 64 | 12,900 (last 200, training) | 2048: 7.5% | smoke; pipeline proven, 12s |
| smoke-b256 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 256 | 1,916 (last 200, training) | 2048: 0% | failed to learn (F-001) |
| smoke-b16 | 2026-09-17 | ntuple S1 | 1 | 1,000 | alpha 0.1, batch 16 | 11,785 (last 200, training) | 2048: 6.5% | learns, no faster than 64 |
| td-01 | 2026-09-17 | ntuple S1 | 1 | 100,000 | alpha 0.1 const, batch 64, tuples per ADR-022 | **64,492** held-out (median 70,620); training last 1k 64,783 | 2048: 96.4%, 4096: 77.2%, 8192: 3.9% | TASK-12 gate PASS; 4,251s train, 327s eval |
