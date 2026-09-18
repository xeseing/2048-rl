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
| smoke-s2-decay-resume | 2026-09-17 | ntuple S2 | 1 | 1,000 | alpha linear 0.1 -> 0.01, batch 64, ckpt every 200; hard-killed after row 500 (ckpt 400), `--resume` | 10,504 (last 100, training) | 2048: 3% | resume under decay proven: metrics incl. alpha identical bar seconds, weights bit-identical to unkilled twin |
| td-decay-probe | 2026-09-17 | ntuple S1 | 1 | 100,000 | alpha linear 0.1 -> 0.01 over 100k, batch 64 | **62,589** held-out (median 69,644); training last 1k 63,728 | 2048: 92.5%, 4096: 71.0%, 8192: 4.5% | decay below the 6% 8192 bar → td-02 constant (ADR-025); trailed td-01 at every 10k mark; 2,312s train, 249s eval |
| td-02 | 2026-09-18 | ntuple S2 | 1 | 1,000,000 | alpha 0.1 const, batch 64, 4x6-tuples per ADR-024, ckpt every 10k | **126,454** held-out (median 146,396, max 313,632); training last 1k 128,360, gap 1.5% | 2048: 95.5%, 4096: 89.7%, 8192: 69.7%, 16384: 2.1% | TASK-13 gate PASS (SPECS §5: ≥ 40,000 / ≥ 90% / 4096 ≥ 50%), 3.2x over on mean. 21.50h elapsed, **15.34h compute** after two sleeps (6.17h, FACTS); 610s eval. Ran to completion unattended; ADR-026's “below 30% 8192 → try decay” trigger did not fire at 69.7%. |

**Open question (td-02, 2026-09-17), not being investigated now:** per-1,000-game pace ran
at 95–122s from 50k to 73k on AC, and at 26–65s after waking at 20:37 on battery (from
84k to 87k). The machine runs faster on battery than on AC. It may share a cause with
the eval's 0.085 vs 0.110 ms/move gap. Data: `runs/td-02/pace.csv`; sleep windows are
in FACTS.
